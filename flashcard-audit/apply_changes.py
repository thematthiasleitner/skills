#!/usr/bin/env python3
"""
Apply flashcard audit verdicts to vault files.

Reads:
  - extracted-cards.json (from extract_cards.py)
  - classifications.jsonl (from classification step — one JSON per line)
  - rewrites.jsonl (from rewrite step — one JSON per line, keepers only)

Actions:
  - RETIRE: remove the separator line (? / ??) and <!--SR:...--> comment
  - KEEP with rewrite: replace question + answer text, preserve SR comment
  - KEEP without rewrite: leave as-is

Usage:
    python3 apply_changes.py [vault_path] [--dry-run] [--apply]

Default is --dry-run. Must pass --apply to mutate files.
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import date

SR_PATTERN = re.compile(r'<!--SR:.*?-->')


def load_jsonl(path):
    """Load a .jsonl file (one JSON object per line)."""
    items = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            items[obj['id']] = obj
    return items


def load_extracted(path):
    """Load extracted cards JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def retire_multiline_card(lines, card):
    """
    Retire a multiline card (? or ??).
    Remove the separator line and the SR comment line.
    Returns modified lines list.
    """
    sep_type = card['separator']  # '?' or '??'

    # Find the separator line between line_start and line_end
    for i in range(card['line_start'] - 1, min(card['line_end'], len(lines))):
        if lines[i].strip() == sep_type:
            lines[i] = ''  # Remove separator line (leave blank)
            break

    # Remove SR comment
    if card.get('sr_line'):
        sr_idx = card['sr_line'] - 1
        if sr_idx < len(lines) and SR_PATTERN.search(lines[sr_idx]):
            lines[sr_idx] = ''

    return lines


def retire_singleline_card(lines, card):
    """
    Retire a single-line card (:: or :::).
    Replace separator with em-dash and remove SR comment.
    """
    line_idx = card['line_start'] - 1
    sep = ':::' if card['separator'] == ':::' else '::'

    if line_idx < len(lines) and sep in lines[line_idx]:
        lines[line_idx] = lines[line_idx].replace(sep, ' — ', 1)

    if card.get('sr_line'):
        sr_idx = card['sr_line'] - 1
        if sr_idx < len(lines) and SR_PATTERN.search(lines[sr_idx]):
            lines[sr_idx] = ''

    return lines


def rewrite_multiline_card(lines, card, rewrite):
    """
    Rewrite a multiline card's question and answer.
    Preserve the SR comment.
    """
    # Find separator line
    sep_idx = None
    sep_type = card['separator']
    for i in range(card['line_start'] - 1, min(card['line_end'], len(lines))):
        if lines[i].strip() == sep_type:
            sep_idx = i
            break

    if sep_idx is None:
        return lines  # Can't find separator, skip

    # Find question range: from line_start to sep_idx
    q_start = card['line_start'] - 1
    q_end = sep_idx

    # Find answer range: from sep_idx+1 to SR comment or card end
    a_start = sep_idx + 1
    if card.get('sr_line'):
        a_end = card['sr_line'] - 1
    else:
        a_end = card['line_end']

    # Check if separator should change (e.g., ? → ::)
    new_sep = rewrite.get('separator', sep_type)

    if new_sep in ('::', ':::'):
        # Convert multiline → single-line
        # Replace entire block with single line
        new_line = f"{rewrite['question']} {new_sep} {rewrite['answer']}"
        # Preserve SR comment
        sr_comment = ''
        if card.get('sr_line'):
            sr_idx = card['sr_line'] - 1
            if sr_idx < len(lines):
                sr_comment = lines[sr_idx]

        # Replace the entire card range
        for i in range(q_start, min(a_end, len(lines))):
            lines[i] = ''
        lines[q_start] = new_line
        # SR comment stays on its original line (already in lines)
    else:
        # Stay multiline — replace question and answer text
        # Clear old question lines
        for i in range(q_start, q_end):
            lines[i] = ''
        lines[q_start] = rewrite['question']

        # Clear old answer lines
        for i in range(a_start, min(a_end, len(lines))):
            lines[i] = ''
        lines[a_start] = rewrite['answer']

    return lines


def rewrite_singleline_card(lines, card, rewrite):
    """Rewrite a single-line card."""
    line_idx = card['line_start'] - 1
    new_sep = rewrite.get('separator', card['separator'])
    answer = rewrite.get('answer', '')

    if new_sep == '?':
        # Convert single-line → multiline
        lines[line_idx] = f"{rewrite['question']}\n?\n{answer}"
    else:
        lines[line_idx] = f"{rewrite['question']} {new_sep} {answer}"

    return lines


def apply_to_file(filepath, file_cards, classifications, rewrites, dry_run=True):
    """Apply all changes to a single file. Returns (retires, keeps, rewrites_applied)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    retires = 0
    keeps = 0
    rewrites_applied = 0

    # Process cards in REVERSE line order to preserve line numbers
    sorted_cards = sorted(file_cards, key=lambda c: c['line_start'], reverse=True)

    for card in sorted_cards:
        cid = card['id']

        if cid not in classifications:
            continue  # Not classified yet, skip

        verdict = classifications[cid]['verdict']

        if verdict == 'retire':
            if card['separator'] in ('?', '??'):
                retire_multiline_card(lines, card)
            else:
                retire_singleline_card(lines, card)
            retires += 1

        elif verdict == 'keep':
            keeps += 1
            if cid in rewrites:
                rewrite = rewrites[cid]
                if card['separator'] in ('?', '??'):
                    rewrite_multiline_card(lines, card, rewrite)
                else:
                    rewrite_singleline_card(lines, card, rewrite)
                rewrites_applied += 1

    if not dry_run and (retires > 0 or rewrites_applied > 0):
        # Clean up multiple consecutive blank lines
        new_content = re.sub(r'\n{4,}', '\n\n\n', '\n'.join(lines))
        # Write atomically
        tmp = filepath.with_suffix('.md.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(new_content)
        tmp.rename(filepath)

    return retires, keeps, rewrites_applied


def main():
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/Users/matthias/ObsVault')
    dry_run = '--apply' not in sys.argv
    audit_dir = vault_path / '.flashcard-audit'

    # Load data
    extracted = load_extracted(audit_dir / 'extracted-cards.json')
    cards = extracted['cards']

    classifications_path = audit_dir / 'classifications.jsonl'
    rewrites_path = audit_dir / 'rewrites.jsonl'

    if not classifications_path.exists():
        print("ERROR: No classifications.jsonl found. Run the classification step first.")
        sys.exit(1)

    classifications = load_jsonl(classifications_path)
    rewrites = load_jsonl(rewrites_path) if rewrites_path.exists() else {}

    # Group cards by file
    by_file = defaultdict(list)
    for card in cards:
        by_file[card['file']].append(card)

    # Apply changes
    total_retires = 0
    total_keeps = 0
    total_rewrites = 0
    files_modified = 0

    mode = "DRY RUN" if dry_run else "APPLYING"
    print(f"=== {mode} ===")
    print(f"Cards classified: {len(classifications)}")
    print(f"Rewrites available: {len(rewrites)}")
    print()

    for rel_path, file_cards in sorted(by_file.items()):
        filepath = vault_path / rel_path
        if not filepath.exists():
            continue

        # Only process files with classified cards
        classified_in_file = [c for c in file_cards if c['id'] in classifications]
        if not classified_in_file:
            continue

        r, k, rw = apply_to_file(filepath, file_cards, classifications, rewrites, dry_run)

        if r > 0 or rw > 0:
            files_modified += 1
            print(f"  {rel_path}: retire={r}, keep={k}, rewrite={rw}")

        total_retires += r
        total_keeps += k
        total_rewrites += rw

    print(f"\n=== Summary ===")
    print(f"Files modified: {files_modified}")
    print(f"Cards retired: {total_retires}")
    print(f"Cards kept: {total_keeps}")
    print(f"Cards rewritten: {total_rewrites}")
    print(f"Estimated active cards remaining: {len(cards) - total_retires}")

    if dry_run:
        print(f"\nThis was a DRY RUN. Pass --apply to make changes.")

    # Update canonical index
    if not dry_run:
        index_path = audit_dir / 'canonical-index.json'
        if index_path.exists():
            with open(index_path) as f:
                index = json.load(f)
        else:
            index = {"version": 1, "target_pool_size": 700, "insights": []}

        # Add kept cards to index
        for cid, cls in classifications.items():
            if cls['verdict'] == 'keep':
                # Find the card
                card = next((c for c in cards if c['id'] == cid), None)
                if card and not any(e['id'] == cid for e in index['insights']):
                    index['insights'].append({
                        'id': cid,
                        'summary': card['question'][:100],
                        'source_file': card['file'],
                        'tag': cls.get('tag', 'fc/insight'),
                    })

        index['retired_count'] = total_retires
        index['last_audit'] = str(date.today())

        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print(f"Updated canonical index: {len(index['insights'])} insights")


if __name__ == '__main__':
    main()
