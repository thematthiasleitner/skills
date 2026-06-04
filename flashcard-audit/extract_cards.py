#!/usr/bin/env python3
"""
Extract all Obsidian Spaced Repetition flashcards from a vault into structured JSON.

Usage:
    python3 extract_cards.py [vault_path] [--output path.json]

Separators detected:
    ::   single-line (front :: back)
    :::  single-line reversed (back ::: front)
    ?    multiline (question \\n ? \\n answer)
    ??   multiline reversed (answer \\n ?? \\n question)

Output: JSON with cards array + stats. Each card has:
    id, file, line_start, line_end, separator, question, answer,
    sr_comment, has_images, has_wikilinks, word_count, auto_flags
"""

import json
import re
import hashlib
import sys
from pathlib import Path
from datetime import date

SR_PATTERN = re.compile(r'<!--SR:.*?-->')
WIKILINK_PATTERN = re.compile(r'\[\[.*?\]\]')
IMAGE_EMBED = re.compile(r'!\[\[.*?\]\]')
INLINE_CODE = re.compile(r'`[^`]+`')
DIVIDERS = {'***', '---', '----', '___'}
SKIP_DIRS = {'.obsidian', '.git', '.trash', '.flashcard-audit', 'node_modules'}


def strip_sr_comment(text):
    """Remove SR scheduling comments from text."""
    return SR_PATTERN.sub('', text).strip()


def auto_flag(card):
    """Flag cards that can be mechanically pre-classified."""
    flags = []
    q = card['question']
    a = card['answer']

    # Image-only answer
    a_stripped = IMAGE_EMBED.sub('', a).strip()
    a_stripped = re.sub(r'>\s*\[!image-desc\].*', '', a_stripped, flags=re.DOTALL).strip()
    if not a_stripped and IMAGE_EMBED.search(a):
        flags.append('image-only-answer')

    # Empty or near-empty answer
    if len(a.split()) < 3:
        flags.append('thin-answer')

    # Draft / incomplete markers
    lower_a = a.lower()
    lower_q = q.lower()
    for marker in ['to be reviewed', 'todo', 'tbd', 'fixme', '???']:
        if marker in lower_a or marker in lower_q:
            flags.append('incomplete')
            break

    # Very short question (likely not a real card)
    if len(q.split()) < 3:
        flags.append('thin-question')

    return flags


def find_multiline_cards(lines, start_line):
    """
    Find all multiline cards (? and ??) and return them with their line ranges.
    Returns: list of (card_dict, range(line_start, line_end+1))
    """
    cards = []
    in_code_block = False
    i = start_line

    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith('```'):
            in_code_block = not in_code_block
            i += 1
            continue
        if in_code_block:
            i += 1
            continue

        # Detect standalone ? or ?? separator
        if stripped in ('?', '??'):
            separator = stripped
            sep_idx = i

            # Collect question: walk backwards
            question_lines = []
            q_start = sep_idx
            for j in range(sep_idx - 1, start_line - 1, -1):
                qline = lines[j].strip()
                if not qline or qline in DIVIDERS:
                    break
                if SR_PATTERN.search(qline):
                    break
                if qline in ('?', '??'):
                    break
                question_lines.insert(0, lines[j])
                q_start = j

            # Collect answer: walk forward
            answer_lines = []
            sr_comment = None
            sr_line = None
            card_end = sep_idx + 1

            for j in range(sep_idx + 1, len(lines)):
                aline = lines[j].strip()

                if SR_PATTERN.search(aline):
                    sr_comment = SR_PATTERN.search(aline).group()
                    sr_line = j
                    card_end = j + 1
                    break

                if not aline or aline in DIVIDERS or aline in ('?', '??'):
                    card_end = j
                    break

                answer_lines.append(lines[j])
                card_end = j + 1

            if question_lines:
                question = '\n'.join(question_lines).strip()
                answer = '\n'.join(answer_lines).strip()

                card = {
                    'line_start': q_start + 1,  # 1-indexed
                    'line_end': card_end,        # 1-indexed exclusive
                    'separator': separator,
                    'question': strip_sr_comment(question),
                    'answer': strip_sr_comment(answer),
                    'sr_comment': sr_comment,
                    'sr_line': (sr_line + 1) if sr_line is not None else None,
                }
                line_range = set(range(q_start, card_end))
                cards.append((card, line_range))

        i += 1

    return cards


def find_singleline_cards(lines, start_line, occupied_lines):
    """
    Find all single-line cards (:: and :::), skipping lines that belong
    to multiline cards (occupied_lines).
    """
    cards = []
    in_code_block = False

    for i in range(start_line, len(lines)):
        if i in occupied_lines:
            continue

        stripped = lines[i].strip()

        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Skip SR comments, blank lines, dividers, headings
        if not stripped or stripped in DIVIDERS:
            continue
        if SR_PATTERN.match(stripped):
            continue

        # Remove inline code before checking for separators
        check_line = INLINE_CODE.sub('', lines[i])
        # Remove wikilinks before checking (they can contain ::)
        check_line = WIKILINK_PATTERN.sub('', check_line)

        # Check ::: first (takes precedence)
        if ':::' in check_line:
            parts = lines[i].split(':::', 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                sr_comment, sr_line = _find_sr_nearby(lines, i)
                card_end = (sr_line) if sr_line is not None else (i + 1)
                # ::: is reversed: left=back, right=front
                cards.append({
                    'line_start': i + 1,
                    'line_end': card_end,
                    'separator': ':::',
                    'question': strip_sr_comment(parts[1].strip()),
                    'answer': strip_sr_comment(parts[0].strip()),
                    'sr_comment': sr_comment,
                    'sr_line': sr_line,
                })
                continue

        # Check :: (but not :::)
        if '::' in check_line and ':::' not in check_line:
            parts = lines[i].split('::', 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                sr_comment, sr_line = _find_sr_nearby(lines, i)
                card_end = (sr_line) if sr_line is not None else (i + 1)
                cards.append({
                    'line_start': i + 1,
                    'line_end': card_end,
                    'separator': '::',
                    'question': strip_sr_comment(parts[0].strip()),
                    'answer': strip_sr_comment(parts[1].strip()),
                    'sr_comment': sr_comment,
                    'sr_line': sr_line,
                })

    return cards


def _find_sr_nearby(lines, card_line_idx):
    """Look for SR comment within 2 lines after a single-line card."""
    for j in range(card_line_idx + 1, min(card_line_idx + 3, len(lines))):
        if SR_PATTERN.search(lines[j]):
            return SR_PATTERN.search(lines[j]).group(), j + 1  # 1-indexed
        if lines[j].strip() and not SR_PATTERN.search(lines[j]):
            break
    return None, None


def extract_cards_from_file(filepath, vault_root):
    """Extract all flashcards from a single markdown file."""
    rel_path = str(filepath.relative_to(vault_root))

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError):
        return []

    lines = content.split('\n')

    # Skip YAML frontmatter
    start_line = 0
    if lines and lines[0].strip() == '---':
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                start_line = i + 1
                break

    # Pass 1: multiline cards (? and ??)
    multiline_results = find_multiline_cards(lines, start_line)
    occupied = set()
    for _, line_range in multiline_results:
        occupied.update(line_range)

    # Pass 2: single-line cards (:: and :::), skipping multiline ranges
    singleline_cards = find_singleline_cards(lines, start_line, occupied)

    # Merge and enrich
    all_cards = [card for card, _ in multiline_results] + singleline_cards

    for card in all_cards:
        card['file'] = rel_path
        full_text = card['question'] + '\n' + card['answer']
        card['has_images'] = bool(IMAGE_EMBED.search(full_text))
        card['has_wikilinks'] = bool(WIKILINK_PATTERN.search(full_text))
        card['word_count'] = len(full_text.split())
        card['auto_flags'] = auto_flag(card)

        # Generate stable ID
        raw = f"{rel_path}:{card['line_start']}:{card['question'][:80]}"
        card['id'] = hashlib.sha256(raw.encode()).hexdigest()[:12]

    # Sort by line number
    all_cards.sort(key=lambda c: c['line_start'])
    return all_cards


def find_text_duplicates(cards):
    """Flag cards with identical or near-identical question text."""
    seen = {}  # normalized_question -> first card id
    for card in cards:
        # Normalize: lowercase, strip wikilinks, strip formatting
        norm = card['question'].lower()
        norm = WIKILINK_PATTERN.sub(lambda m: m.group()[2:-2], norm)
        norm = re.sub(r'[*_#>]', '', norm)
        norm = re.sub(r'\s+', ' ', norm).strip()

        if norm in seen:
            if 'text-duplicate' not in card['auto_flags']:
                card['auto_flags'].append('text-duplicate')
                card['duplicate_of'] = seen[norm]
        else:
            seen[norm] = card['id']


def main():
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/Users/matthias/ObsVault')
    output_flag = '--output'
    if output_flag in sys.argv:
        idx = sys.argv.index(output_flag)
        output_path = sys.argv[idx + 1]
    else:
        output_path = str(vault_path / '.flashcard-audit' / 'extracted-cards.json')

    all_cards = []
    files_scanned = 0
    files_with_cards = 0

    for md_file in sorted(vault_path.rglob('*.md')):
        # Skip hidden/system directories
        rel_parts = md_file.relative_to(vault_path).parts
        if any(part.startswith('.') or part in SKIP_DIRS for part in rel_parts):
            continue

        files_scanned += 1
        cards = extract_cards_from_file(md_file, vault_path)
        if cards:
            files_with_cards += 1
            all_cards.extend(cards)

    # Cross-file duplicate detection
    find_text_duplicates(all_cards)

    # Stats
    by_separator = {}
    with_sr = 0
    with_images = 0
    flagged = 0
    flag_counts = {}
    for card in all_cards:
        by_separator[card['separator']] = by_separator.get(card['separator'], 0) + 1
        if card['sr_comment']:
            with_sr += 1
        if card['has_images']:
            with_images += 1
        if card['auto_flags']:
            flagged += 1
            for f in card['auto_flags']:
                flag_counts[f] = flag_counts.get(f, 0) + 1

    output = {
        'cards': all_cards,
        'stats': {
            'total_cards': len(all_cards),
            'total_files_scanned': files_scanned,
            'files_with_cards': files_with_cards,
            'by_separator': by_separator,
            'with_sr_data': with_sr,
            'with_images': with_images,
            'auto_flagged': flagged,
            'flag_counts': flag_counts,
            'extraction_date': str(date.today()),
        }
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Scanned {files_scanned} files")
    print(f"Found {len(all_cards)} cards in {files_with_cards} files")
    print(f"By separator: {json.dumps(by_separator)}")
    print(f"With SR data: {with_sr}")
    print(f"With images: {with_images}")
    print(f"Auto-flagged: {flagged} ({json.dumps(flag_counts)})")
    print(f"Output: {output_path}")


if __name__ == '__main__':
    main()
