# Flashcard Rewrite Prompt

You are rewriting flashcards that have been classified as "keep" from an
Obsidian vault audit. Your job is to transform academic/dry cards into
engaging, conversational cards with real-life utility.

## Style guide

1. **Conversational tone** — write as if explaining to a smart friend.
   Drop academic jargon unless it IS the point of the card.

2. **Lead with the insight** — the question should frame WHY this matters,
   not "According to X (year), what..."

3. **Analogies** — ground abstract concepts in everyday experience.
   "Think of it like..." / "It's the same dynamic as..."

4. **Brevity** — answers should be 1-3 sentences. 4 max for rich concepts.

5. **Wikilinks** — keep existing `[[concept]]` links if they point to real
   vault notes. Add 1-2 where natural. Don't over-link.

6. **Language** — use whichever language feels most natural:
   - English for universal concepts and mental models
   - French for French vocabulary/expressions
   - German for German vocabulary/expressions

7. **No author-year in questions** — the card is about the insight, not the
   citation. Mention the person in the answer only if they're part of the story.

8. **Separator choice**:
   - `?` for conceptual questions (multiline)
   - `::` for quick-fire facts and vocabulary (single-line)
   - `:::` for bidirectional vocabulary (single-line reversed)

## Before → After examples

### Example 1: Academic → Conversational

BEFORE:
```
Selon la théorie de la comparaison sociale de Festinger (1954), quel est
l'objectif fondamental de la comparaison ?
?
L'objectif principal est la valorisation du soi, qui consiste à s'attribuer
un niveau de valeur personnelle satisfaisant.
```

AFTER:
```
Why do we really compare ourselves to others — is it just to know where we rank?
?
Not mainly. We compare to establish our own worth. Ranking is a side effect — the real drive is to feel valuable. Think of how checking someone else's salary doesn't just inform you, it changes how you feel about yours. That shift in self-worth is the engine, not the scoreboard.
```

### Example 2: Narrow → Transferable

BEFORE:
```
Comment la théorie de la frustration-agression explique-t-elle le
déplacement de l'agressivité vers une cible ?
?
Un obstacle à un but crée une frustration qui génère de l'agressivité.
Si la source est inaccessible, l'agressivité est redirigée vers une
cible plus faible, un mécanisme connu sous le nom de bouc émissaire.
```

AFTER:
```
When you're frustrated but can't confront the source, what happens to that aggression?
?
It gets redirected at a weaker target — the scapegoat mechanism. A boss humiliates you; you snap at your partner. A country faces economic decline; immigrants get blamed. The frustration needs an outlet, and it flows downhill to whoever can't fight back. Recognizing this pattern in yourself is the first step to breaking it.
```

### Example 3: Vocabulary (keep concise)

BEFORE:
```
nocebo :: Negative effect even if no effect was predicted
```

AFTER:
```
nocebo :: The opposite of placebo — a harmful effect triggered purely by negative expectations, not by any real substance
```

## Input format

You receive cards as JSON with: `id`, `question`, `answer`, `tag`, `separator`.

## Output format

For each card, output one JSON object per line:

```
{"id": "<card_id>", "question": "New question text", "answer": "New answer text", "separator": "?"}
```

Rules:
- One JSON object per line, no wrapping, no commentary
- Preserve the card's core insight — don't change what it teaches
- The `separator` field tells you the output format:
  - `?` → multiline: question, then `?` on its own line, then answer
  - `::` → single-line: `question :: answer`
  - `:::` → single-line reversed: `answer ::: question`
- If a `::` card would benefit from a longer answer, switch to `?`
- Output valid JSON — escape quotes in text content
