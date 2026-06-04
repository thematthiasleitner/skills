#!/usr/bin/env python3
"""
Prepare classification batches from extracted cards.

Reads extracted-cards.json, filters out auto-flagged cards,
and writes batch files for the classification step.

Usage:
    python3 prepare_batches.py [vault_path] [--batch-size 50] [--retire-flagged]

Options:
    --batch-size N     Cards per batch (default: 50)
    --retire-flagged   Auto-retire all flagged cards (writes to classifications.jsonl)
    --retire-vocab     Auto-retire all ::: vocabulary cards
    --retire-file PAT  Auto-retire all cards from files matching pattern
"""

import json
import sys
import fnmatch
from pathlib import Path


def main():
    vault_path = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else Path('/Users/matthias/ObsVault')
    audit_dir = vault_path / '.flashcard-audit'

    batch_size = 50
    retire_flagged = False
    retire_vocab = False
    retire_patterns = []

    # Parse args
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--batch-size' and i + 1 < len(args):
            batch_size = int(args[i + 1])
            i += 2
        elif args[i] == '--retire-flagged':
            retire_flagged = True
            i += 1
        elif args[i] == '--retire-vocab':
            retire_vocab = True
            i += 1
        elif args[i] == '--retire-file' and i + 1 < len(args):
            retire_patterns.append(args[i + 1])
            i += 2
        else:
            i += 1

    # Load extracted cards
    extracted_path = audit_dir / 'extracted-cards.json'
    with open(extracted_path) as f:
        data = json.load(f)

    cards = data['cards']
    print(f"Total cards: {len(cards)}")

    # Load existing classifications (to skip already-classified)
    classifications_path = audit_dir / 'classifications.jsonl'
    existing = set()
    if classifications_path.exists():
        with open(classifications_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    existing.add(json.loads(line)['id'])
    print(f"Already classified: {len(existing)}")

    # Auto-retire flagged cards
    auto_retired = []

    if retire_flagged:
        for card in cards:
            if card['id'] in existing:
                continue
            if card['auto_flags']:
                # Map flags to retire reasons
                if 'image-only-answer' in card['auto_flags']:
                    reason = 'image-dependent'
                elif 'incomplete' in card['auto_flags']:
                    reason = 'thin'
                elif 'text-duplicate' in card['auto_flags']:
                    reason = 'duplicate'
                elif 'thin-answer' in card['auto_flags']:
                    reason = 'thin'
                elif 'thin-question' in card['auto_flags']:
                    reason = 'thin'
                else:
                    reason = 'thin'

                auto_retired.append({
                    'id': card['id'],
                    'verdict': 'retire',
                    'reason': reason,
                })
                existing.add(card['id'])

    if retire_vocab:
        for card in cards:
            if card['id'] in existing:
                continue
            if card['separator'] == ':::':
                auto_retired.append({
                    'id': card['id'],
                    'verdict': 'retire',
                    'reason': 'vocabulary-bulk-retire',
                })
                existing.add(card['id'])

    for pattern in retire_patterns:
        for card in cards:
            if card['id'] in existing:
                continue
            if fnmatch.fnmatch(card['file'], pattern):
                auto_retired.append({
                    'id': card['id'],
                    'verdict': 'retire',
                    'reason': f'file-pattern:{pattern}',
                })
                existing.add(card['id'])

    # Write auto-retires to classifications
    if auto_retired:
        with open(classifications_path, 'a', encoding='utf-8') as f:
            for cls in auto_retired:
                f.write(json.dumps(cls, ensure_ascii=False) + '\n')
        print(f"Auto-retired: {len(auto_retired)}")

    # Filter remaining cards for batching
    remaining = [c for c in cards if c['id'] not in existing]
    print(f"Remaining for AI classification: {len(remaining)}")

    # Prepare batches
    batches_dir = audit_dir / 'batches'
    batches_dir.mkdir(exist_ok=True)

    # Slim down card data for batches (reduce tokens)
    def slim_card(card):
        return {
            'id': card['id'],
            'file': card['file'],
            'question': card['question'][:500],  # Cap very long questions
            'answer': card['answer'][:500],       # Cap very long answers
            'separator': card['separator'],
            'word_count': card['word_count'],
            'has_images': card['has_images'],
        }

    batch_num = 0
    for start in range(0, len(remaining), batch_size):
        batch = remaining[start:start + batch_size]
        batch_file = batches_dir / f'batch_{batch_num:03d}.json'

        slim_batch = [slim_card(c) for c in batch]
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(slim_batch, f, ensure_ascii=False, indent=2)

        batch_num += 1

    print(f"Created {batch_num} batch files in {batches_dir}/")
    print(f"Each batch has ~{batch_size} cards")
    print(f"\nNext step: classify each batch using Sonnet.")
    print(f"Read classify_prompt.md for instructions.")
    print(f"Write results to {classifications_path} (append mode, one JSON per line)")


if __name__ == '__main__':
    main()
