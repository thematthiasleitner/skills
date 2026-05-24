# thematthiasleitner/skills

Claude Code skills — available on any machine with one command.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/thematthiasleitner/skills/main/install.sh | bash
```

Or clone manually:

```bash
git clone https://github.com/thematthiasleitner/skills.git ~/.claude/skills
```

To update later:

```bash
git -C ~/.claude/skills pull
```

## Skills

| Skill | Description |
|---|---|
| `obsidian-plugin-deploy` | Build + rsync Obsidian plugin to production vault |
| `vault-weaver-health-check` | Diagnose Vault Weaver index vs disk mismatches |
| `vault-weaver-concept-trace` | Single-concept state inspector |
| `vault-wikilink-toolkit` | Vault-wide wikilink scanner / rewriter (dry-run-by-default) |
| `advance-deploy` | Deploy ADVANCE project |
| `advance-server-cycle-trigger` | Trigger manual ADVANCE export cycle |
| `audit-hardcoded-drafts` | Audit hardcoded Outlook drafts |
| `apply-reviewer-audit` | Apply reviewer audit XLSX to translation block store |
| `translate-doc` | Translate DOCX/PPTX FR→DE via ADVANCE pipeline |
| `refine-drafts` | Improve imperfect LLM reply drafts |
| `qualtrics` | Qualtrics REST API v3 expert |
| `qualtrics-csv-pull` | Pull Qualtrics CSV exports |
| `qualtrics-export` | Export Qualtrics responses |
| `qualtrics-e2e-pressure-test` | End-to-end pressure test |
| `qualtrics-restructure-step` | Restructure Qualtrics survey steps |
| `glossary` | Glossary lookup |
| `apple-mail-reply` | Compose Apple Mail replies |
| `caveman` | Ultra-compressed responses |
| `caveman-commit` | Compressed commit messages |
| `caveman-compress` | Compress context/documents |
| `caveman-review` | Ultra-compressed code review |
| `caveman-stats` | Compression statistics |
| `caveman-help` | Caveman quick-reference |
| `cavecrew` | Multi-agent caveman crew |
| `diagnose` | Diagnose code issues |
| `grill-with-docs` | Interrogate docs |
| `grill-me` | Self-directed grilling |
| `handoff` | Compact conversation for agent handoff |
| `improve-codebase-architecture` | Architecture review and improvement |
| `prototype` | Rapid prototyping |
| `tdd` | Test-driven development |
| `to-issues` | Convert tasks to GitHub issues |
| `to-prd` | Generate PRD from requirements |
| `triage` | Issue triage state machine |
| `write-a-skill` | Create new agent skills |
| `zoom-out` | Step back and see the big picture |
| `setup-matt-pocock-skills` | Setup Matt Pocock skills config |

## Compatibility

Works with **Claude Code** (CLI, VSCode extension, desktop app).
Not available on claude.ai web — skills require local file access.
