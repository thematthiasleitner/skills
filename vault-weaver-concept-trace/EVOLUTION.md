# Evolution log — vault-weaver-concept-trace

## 2026-05-24 — Skill created

Initial creation. The "why is yellow.md still in approved/" tool — assembled
many times by hand during debugging sessions:
- read frontmatter of the file
- search index.json for the slug
- grep vault for inbound `[[X]]`
- tail activity log

Now codified. Built-in diagnosis rules:
- ✅ healthy (all 3 agree)
- ⚠ frontmatter ↔ disk-location mismatch (the misplacement bug)
- ⚠ index ↔ frontmatter mismatch (stale index)
- ⚠ orphan index entry (no file)
- ⚠ orphan file (no index entry)
- ❌ unknown (nothing found)

**Default inbound-wikilink cap is 20.** If the user repeatedly passes
`--all`, that's a signal to bump the default.
