# Flashcard Classification Prompt

You are classifying flashcards from an Obsidian vault. Your job is to decide
which cards are worth keeping in a spaced repetition system and which should
be retired.

## Context

The user wants flashcards that serve real life, not academic exams. Target:
500-800 active cards across the whole vault (down from ~5,800). That means
~85-90% of cards get retired.

## Keep criteria (card must pass at least ONE)

1. **Transferable mental model** — an idea you can apply across domains.
   "The future depends only on the present, not the path" (Markov property)
   works in decision-making, not just math.

2. **Conversation fuel** — a fact or story surprising enough to tell someone.
   "4% of people are congenitally amusic" is a dinner-party fact.
   "V1 uses oriented line detectors" is not.

3. **Vocabulary you'd use** — a word filling a gap in active FR/DE/EN
   expression. "Hinterlistig" (perfidious) fills a gap if you speak German
   actively. "Syn: lovely = splendid" does not — you already know those.

4. **Principle that changes behavior** — something about relationships,
   leadership, or judgment you'd want top-of-mind.

## Retire reasons

- `narrow-academic` — too specific to a course, no real-life utility
- `duplicate` — same insight already covered by another card (reference its ID)
- `image-dependent` — answer only makes sense with an image that's not described
- `thin` — too little content to be useful (bare definition, no explanation)
- `already-known` — common knowledge the user doesn't need SR to remember
- `humor-only` — joke or meme, not knowledge-bearing

## Calibration examples

### KEEP examples (from calibrated audit of Social Identity Theory file)

**KEEP as fc/insight** — "Why do people revolt when things aren't even that bad?"
→ Relative deprivation: comparative disadvantage, not absolute. Transferable to
salary negotiations, politics, sibling rivalry.

**KEEP as fc/story** — "What's the minimum it takes to make people discriminate?"
→ Klee vs Kandinsky experiment. Captivating, counterintuitive, retellable.

**KEEP as fc/insight** — "Do people maximize their group's gains or the gap?"
→ Maximum Difference strategy. People sacrifice absolute gain for relative
superiority. Applies to arms races, price wars, political obstruction.

### RETIRE examples

**RETIRE narrow-academic** — "What are the specific conditions of a minimal context
in Tajfel's paradigm?" → Methodological detail, no real-life utility.

**RETIRE duplicate** — "Is competition necessary for ingroup favoritism?"
→ Same insight as the Klee/Kandinsky card, just stated differently.

**RETIRE thin** — "anaclitic :: Greek for leaning upon" → Etymology without
meaning or usage context.

## Output format

For each card, output exactly one JSON line:

```
{"id": "<card_id>", "verdict": "keep", "reason": "transferable-model", "tag": "fc/insight"}
{"id": "<card_id>", "verdict": "keep", "reason": "conversation-fuel", "tag": "fc/story"}
{"id": "<card_id>", "verdict": "keep", "reason": "active-vocabulary", "tag": "fc/vocab"}
{"id": "<card_id>", "verdict": "keep", "reason": "behavior-principle", "tag": "fc/insight"}
{"id": "<card_id>", "verdict": "retire", "reason": "narrow-academic"}
{"id": "<card_id>", "verdict": "retire", "reason": "duplicate", "duplicate_of": "<other_id>"}
{"id": "<card_id>", "verdict": "retire", "reason": "thin"}
```

Rules:
- One JSON object per line, no wrapping, no commentary
- `verdict` is either `keep` or `retire`
- `tag` is only for keep verdicts: `fc/insight`, `fc/story`, or `fc/vocab`
- Be aggressive. When in doubt, retire. 500-800 cards total is the target.
- For duplicates within the same batch, keep the BEST version and retire others.
- If a card's answer is just an image embed with no text description, retire as `image-dependent`.

## Batch input format

You will receive cards as a JSON array. Each card has:
- `id`: unique identifier
- `file`: source file path
- `question`: front of card
- `answer`: back of card
- `separator`: the flashcard separator type
- `word_count`: total words in Q+A
- `has_images`: whether the card contains image embeds

Classify ALL cards in the batch. Do not skip any.
