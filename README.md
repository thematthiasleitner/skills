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

<!-- skills:start -->

| Skill | Description |
|---|---|
| `advance-agent-session` | Preflight to run ONCE at the start of any ADVANCE server/live session, before advance-lock / adva... |
| `advance-calendar-status` | Read-only staleness verdict for the ADVANCE advance-project@unige.ch Outlook calendar — runs sync... |
| `advance-cycle-status` | Read-only health check of the ADVANCE production server's deploy + 15-min cycle — current deploye... |
| `advance-deploy` | BREAK-GLASS manual deploy to the ADVANCE production server. |
| `advance-durable-workbook-fix` | Decide + scaffold a DURABLE fix to the format/content of cells in the ADVANCE live workbook (Qual... |
| `advance-elevenlabs-narration` | Generate single-speaker ADVANCE German narration audio (e.g. |
| `advance-elevenlabs-podcast` | Generate two-host ADVANCE German podcasts (the "Gemeinsam im Gespräch" CG podcasts) with ElevenLa... |
| `advance-elevenlabs-voices` | Canonical reference for ADVANCE ElevenLabs German TTS — the vetted voice registry (Christian/Lena... |
| `advance-graph-health` | Read-only health verdict for the ADVANCE Microsoft Graph mail auth — is the token alive, since wh... |
| `advance-layer-c` | Manually run the ADVANCE nightly Layer C drift detector on the production server, on demand — typ... |
| `advance-lock` | Claim / renew / release / check the ADVANCE multi-agent mutex before LIVE or server operations. |
| `advance-new-task` | Start an ADVANCE coding task in an isolated, CURRENT git clone off origin/main (the multi-agent w... |
| `advance-promote` | Deploy merged ADVANCE code to production by pushing a promote tag (tag-deploy; docs/adr/0004 Phas... |
| `advance-server-cycle-trigger` | Trigger a one-shot manual export cycle on the ADVANCE production server (in-between the 15-min au... |
| `advance-ship` | Ship an ADVANCE task — push the current task/<id> branch and open a Merge Request set to AUTO-MER... |
| `advance-tts-master` | Master raw ADVANCE TTS clips (ElevenLabs or Gemini) into a clean, loudness-matched deliverable WI... |
| `alps-funder-report` | Drafts and updates funder-facing impact and finance report sections for ALPS events (Summer Schoo... |
| `alps-post-render` | >- |
| `alps-social-reel` | Turn an APPROVED ALPS HTML slide/carousel deliverable into a polished, on-brand 9:16 Instagram re... |
| `alps-task-plan` | Reads an ALPS Slack List task record and produces a step-by-step action plan with owners, blocker... |
| `alps-web-add-speaker` | Add or refresh a speaker / facilitator / team member on an ALPS Foundation website — process thei... |
| `alps-web-ship` | Build, verify, and ship a code change to any ALPS Foundation website (Astro + Cloudflare repos un... |
| `alps-web-sync-schedule` | Update an ALPS event programme / day-by-day timetable on the website from a planning spreadsheet. |
| `apple-mail-reply` | Compose a reply or a new outgoing message in Apple Mail (via AppleScript), with attachments, in a... |
| `apply-reviewer-audit` | Apply a reviewer-edited audit XLSX to the ADVANCE translation block store safely. |
| `archive-stale` | Walk any folder tree and archive stale artefacts (versioned predecessors, _BEFORE/_PREV snapshots... |
| `audit-hardcoded-drafts` | Audit all hardcoded Outlook drafts for the ADVANCE project — verify each draft matches the partic... |
| `cavecrew` | > |
| `caveman` | > |
| `caveman-commit` | > |
| `caveman-compress` | > |
| `caveman-help` | > |
| `caveman-review` | > |
| `caveman-stats` | > |
| `crash-safe-batch-pipeline` | Design a long-running batch job so it survives mid-run crashes (503s, OOM, network drops, killed... |
| `diagnose` | Disciplined diagnosis loop for hard bugs and performance regressions. |
| `embedded-captions` | Add captions to a talking-head video. |
| `faceless-explainer` | faceless-explainer video workflow - arbitrary text (article / notes / topic / brief) -> narrator_... |
| `flashcard-audit` | Audit flashcards in Obsidian vault notes — classify as keep/improve/retire, deduplicate across fi... |
| `french-typography-nbsp` | Detect and neutralize the U+00A0 (NBSP) trap when comparing French strings — subjects, titles, la... |
| `general-video` | > |
| `git-push` | Push the current branch to its remote, handling SSH passphrase authentication automatically. |
| `glossary` | Look up a term in the ADVANCE FR/DE/EN glossary (glossary_ADVANCE_v1.json, 218 entries). |
| `graph-drafts-tree` | Print a Microsoft Graph mail Drafts folder tree with per-folder item counts, optional message sub... |
| `graph-mail-search` | Mailbox-wide Microsoft Graph $search — find every message matching a term (participant email, sur... |
| `graph-sentitems-scan` | Scan a Microsoft Graph SentItems mailbox folder reliably. |
| `graphic-overlays` | Package an existing talking-head / interview / podcast video by layering timed, designed GRAPHIC... |
| `graphify` | Use for any question about a codebase, its architecture, file relationships, or project content —... |
| `grill-me` | Interview the user relentlessly about a plan or design until reaching shared understanding, resol... |
| `grill-with-docs` | Grilling session that challenges your plan against the existing domain model, sharpens terminolog... |
| `handoff` | Compact the current conversation into a handoff document for another agent to pick up. |
| `hyperframes` | Create video compositions, animations, title cards, overlays, captions, voiceovers, audio-reactiv... |
| `hyperframes-animation` | All animation knowledge for HyperFrames — atomic motion rules, multi-phase scene blueprints, scen... |
| `hyperframes-cli` | HyperFrames CLI dev loop — `npx hyperframes` for scaffolding (init), validation (lint, inspect),... |
| `hyperframes-core` | HyperFrames HTML composition contract. |
| `hyperframes-creative` | Non-animation creative direction for HyperFrames videos. |
| `hyperframes-media` | Asset preprocessing for HyperFrames compositions — multi-provider TTS (HeyGen / ElevenLabs / Koko... |
| `hyperframes-registry` | Install and wire registry blocks and components into HyperFrames compositions. |
| `improve-codebase-architecture` | Find deepening opportunities in a codebase, informed by the domain language in CONTEXT.md and the... |
| `label-numeric-audit` | Audit ADVANCE code for NUMERIC assumptions on the label-based Qualtrics CSV (ADR 0003). |
| `motion-graphics` | > |
| `obsidian-heading-enforcer` | Detect and fix bold text misused as section titles in Obsidian Markdown files, converting them to... |
| `obsidian-plugin-builder` | Legacy orchestration wrapper for full-lifecycle Obsidian plugin requests that explicitly need bot... |
| `obsidian-plugin-deploy` | Build a custom Obsidian plugin in the ObsVault_Dev workspace and rsync the compiled artifacts to... |
| `obsidian-plugin-from-scratch` | Operationalize and implement Obsidian plugins from idea to working codebase, without handling pub... |
| `obsidian-plugin-release-github` | Release, publish, and update Obsidian plugins using GitHub releases and official submission workf... |
| `obsidian-vault-agent` | Execute safe Obsidian vault content manipulation with awareness of Obsidian core features and ins... |
| `pr-to-video` | pr-to-video workflow - a GitHub pull request (URL like github.com/<owner>/<repo>/pull/<N>, or <ow... |
| `product-launch-video` | > |
| `prototype` | Build a throwaway prototype to flesh out a design before committing to it. |
| `qualtrics` | Expert knowledge of the Qualtrics REST API v3 for the ADVANCE project. |
| `qualtrics-column-trace` | Trace one ADVANCE column end-to-end across all four layers — survey question (alive? orphaned? wh... |
| `qualtrics-csv-pull` | Pull the live ADVANCE Qualtrics CSV via the 3-step async export endpoint (start → poll → download... |
| `qualtrics-e2e-pressure-test` | Submit a test persona to the live ADVANCE Qualtrics survey, pull the resulting CSV, feed it throu... |
| `qualtrics-export` | Expert knowledge of the ADVANCE project Qualtrics export pipeline — CSV column format, f_ty_room... |
| `qualtrics-export-coverage-audit` | Report every Qualtrics DataExportTag that will NOT appear in CSV exports — block-less questions (... |
| `qualtrics-inject-row` | Inject a REAL facilitator availability (f_tor_3) binding into the live ADVANCE survey as a Status... |
| `qualtrics-response-audit` | READ-ONLY audit of live ADVANCE Qualtrics responses by status — list them with RecordedDate, prof... |
| `qualtrics-restructure-step` | Scaffold an idempotent, --dry-run-default Python script that mutates the ADVANCE Qualtrics survey... |
| `qualtrics-survey-pull` | Pull the live ADVANCE Qualtrics survey DEFINITION (questions, blocks, flow) as JSON and answer "i... |
| `reference-flashcards` | Sync curated thesis reference PDFs into the Obsidian vault and create thesis-defense flashcards f... |
| `refine-drafts` | Improve imperfect LLM reply drafts for the ADVANCE project by tracing red/yellow Outlook annotati... |
| `remotion-to-hyperframes` | Translate an existing Remotion (React-based) video composition into a HyperFrames HTML composition. |
| `request-ssh-access` | Standardize how an agent gains use of a passphrase-protected SSH key WITHOUT ever handling the pa... |
| `session-harvest` | Turn a finished work session into durable assets — extract the lessons, mint small composable ski... |
| `setup-matt-pocock-skills` | Sets up an `## Agent skills` block in AGENTS.md/CLAUDE.md and `docs/agents/` so the engineering s... |
| `skills-sync` | Sync your personal Claude skills through the thematthiasleitner/skills GitHub repo so the same sk... |
| `slack-list-item-comment` | Find and post a comment on a Slack List item — routing the comment to the list's discussion chann... |
| `slideshow` | > |
| `tag-audit` | Review pending concepts in ObsVault 0.Tags/pending/ and batch approve or reject them with reasoni... |
| `tag-batch-enrich` | Enrich multiple ObsVault concept/tag files in one pass — pick the N stalest approved concepts (or... |
| `tag-create` | Create a new concept/tag file in the ObsVault 0.Tags/ system — scan the vault for notes mentionin... |
| `tag-discover` | Scan an ObsVault note or folder and propose new concepts worth adding to the 0.Tags/ system, scor... |
| `tag-enrich` | Re-synthesize an existing concept/tag file in ObsVault 0.Tags/ — re-scan the vault for notes ment... |
| `tdd` | Test-driven development with red-green-refactor loop. |
| `to-issues` | Break a plan, spec, or PRD into independently-grabbable issues on the project issue tracker using... |
| `to-prd` | Turn the current conversation context into a PRD and publish it to the project issue tracker. |
| `token-last` | Use whenever you are about to give the user a shell command they must complete with a SECRET they... |
| `translate-doc` | Translate a DOCX or PPTX from FR to DE using the existing ADVANCE translation pipeline (Gemini Fl... |
| `triage` | Triage issues through a state machine driven by triage roles. |
| `vault-weaver-concept-trace` | Inspect a single Vault Weaver concept slug end-to-end — its on-disk file (path, subfolder, frontm... |
| `vault-weaver-health-check` | Diagnose the Vault Weaver plugin's lifecycle state — compare the on-disk concept files (approved/... |
| `vault-wikilink-toolkit` | Scan, preview, and rewrite/strip Obsidian `[[wikilinks]]` across a vault using configurable patte... |
| `website-to-video` | Capture a general website/URL and turn it into a HyperFrames video (site tour, showcase, or socia... |
| `workbook-format-census` | Census date/time/number format shapes across every sheet of an ADVANCE recruitment workbook, flag... |
| `write-a-skill` | Create new agent skills with proper structure, progressive disclosure, and bundled resources. |
| `zoom-out` | Tell the agent to zoom out and give broader context or a higher-level perspective. |

<!-- skills:end -->

## Compatibility

Works with **Claude Code** (CLI, VSCode extension, desktop app).
Not available on claude.ai web — skills require local file access.
