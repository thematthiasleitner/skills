---
name: qualtrics
description: Expert knowledge of the Qualtrics REST API v3 for the ADVANCE project. Invoke when the user wants to interact with Qualtrics surveys programmatically — creating/updating questions, blocks, flow, or exporting responses.
tools: Bash, Read, Glob, Grep
---

# Qualtrics API Skill

You are an expert at using the Qualtrics REST API (v3). When this skill is invoked, help the user interact with Qualtrics surveys programmatically.

## Project context

The active project uses these credentials (loaded via shell):
```bash
source qualtrics/qualtrics_env.sh
# sets: $QUALTRICS_API_TOKEN, $QUALTRICS_DATACENTER
# $QUALTRICS_DATACENTER is the full base URL, e.g. https://fra1.qualtrics.com/API/v3
```

Main survey ID: `SV_aWrEE8bXIdc6Pqe` (ADVANCE recruitment survey).

## API conventions

**Base URL:** `$QUALTRICS_DATACENTER` (e.g. `https://fra1.qualtrics.com/API/v3`)

**Auth header for every request:**
```
X-API-TOKEN: $QUALTRICS_API_TOKEN
Content-Type: application/json
```

**Response envelope:** All responses wrap data in `{"result": {...}, "meta": {"httpStatus": "200 - OK"}}`.

**Two API families:**
- `/surveys/{id}` — read-only metadata + response export
- `/survey-definitions/{id}` — full read/write access to survey structure (questions, blocks, flow). **Use this for all edits.**

---

## Endpoint reference

### Survey definitions (read/write structure)

| Operation | Method | Path |
|-----------|--------|------|
| Get full survey definition | GET | `/survey-definitions/{surveyId}` |
| Update survey options | PUT | `/survey-definitions/{surveyId}/options` |
| Get survey flow | GET | `/survey-definitions/{surveyId}/flow` |
| Update survey flow | PUT | `/survey-definitions/{surveyId}/flow` |

### Blocks

| Operation | Method | Path |
|-----------|--------|------|
| List blocks | GET | `/survey-definitions/{surveyId}` (inside `result.Blocks`) |
| Create block | POST | `/survey-definitions/{surveyId}/blocks` |
| Get block | GET | `/survey-definitions/{surveyId}/blocks/{blockId}` |
| Update block | PUT | `/survey-definitions/{surveyId}/blocks/{blockId}` |
| Delete block | DELETE | `/survey-definitions/{surveyId}/blocks/{blockId}` |

**Create block body:**
```json
{
  "Type": "Standard",
  "Description": "My Block Name",
  "BlockElements": [],
  "Options": {
    "BlockLocking": "false",
    "RandomizeQuestions": "false",
    "BlockVisibility": "Expanded"
  }
}
```

### Questions

| Operation | Method | Path |
|-----------|--------|------|
| Create question | POST | `/survey-definitions/{surveyId}/questions?blockId={blockId}` |
| Get question | GET | `/survey-definitions/{surveyId}/questions/{questionId}` |
| Update question | PUT | `/survey-definitions/{surveyId}/questions/{questionId}` |
| Delete question | DELETE | `/survey-definitions/{surveyId}/questions/{questionId}` |

**Common QuestionType / Selector combinations:**

| Type | Selector | SubSelector | Description |
|------|----------|-------------|-------------|
| `MC` | `SAVR` | — | Single-answer radio |
| `MC` | `MAVR` | — | Multi-answer checkboxes |
| `MC` | `DL` | — | Dropdown list |
| `TE` | `SL` | — | Single-line text |
| `TE` | `ML` | — | Multi-line text |
| `Matrix` | `Likert` | `SingleAnswer` | Matrix / Likert |
| `DB` | `TB` | — | Descriptive text / HTML block |
| `FileUpload` | `FileUpload` | — | File upload |

**Create question body template:**
```json
{
  "QuestionText": "<p>Your question text here</p>",
  "QuestionType": "MC",
  "Selector": "SAVR",
  "DataExportTag": "my_tag",
  "QuestionDescription": "Internal label",
  "Choices": {
    "1": {"Display": "Option A"},
    "2": {"Display": "Option B"}
  },
  "ChoiceOrder": [1, 2],
  "Validation": {
    "Settings": {
      "ForceResponse": "ON",
      "ForceResponseType": "ON",
      "Type": "None"
    }
  }
}
```

**Descriptive text / link block (DB):**
```json
{
  "QuestionText": "<p><a href=\"https://example.com\">Click here</a></p>",
  "QuestionType": "DB",
  "Selector": "TB",
  "DataExportTag": "my_desc"
}
```

**Add French translation to a question:**
```json
{
  "Language": {
    "FR": {
      "QuestionText": "Votre texte en français",
      "Choices": {
        "1": {"Display": "Option A en français"},
        "2": {"Display": "Option B en français"}
      }
    }
  }
}
```

**Validation patterns:**
```json
// Force response ON
{"Settings": {"ForceResponse": "ON",  "ForceResponseType": "ON",  "Type": "None"}}

// Force response OFF
{"Settings": {"ForceResponse": "OFF", "ForceResponseType": "OFF", "Type": "None"}}
```

---

### Response export (3-step async)

**Step 1 — Start export:**
```
POST /surveys/{surveyId}/export-responses
Body: {
  "format": "csv",          // csv | json | tsv | xml | spss
  "useLabels": false,       // true = text labels, false = numeric recodes
  "compress": true          // true = zip (default)
}
→ result.progressId = "ES_..."
```

**Step 2 — Poll progress (every 2–5s):**
```
GET /surveys/{surveyId}/export-responses/{progressId}
→ result.status: "inProgress" | "complete" | "failed"
→ When complete: result.fileId = "ExportFile_..."
```

**Step 3 — Download file:**
```
GET /surveys/{surveyId}/export-responses/{fileId}/file
→ Binary ZIP/file stream
```

---

## Shell snippets (copy-paste ready)

**Load credentials:**
```bash
source qualtrics/qualtrics_env.sh
SID="SV_aWrEE8bXIdc6Pqe"
BASE="$QUALTRICS_DATACENTER"
TOK="$QUALTRICS_API_TOKEN"
HDR=(-H "X-API-TOKEN: $TOK" -H "Content-Type: application/json")
```

**List all blocks with names:**
```bash
curl -s "${HDR[@]}" "$BASE/survey-definitions/$SID" | python3 -c "
import sys,json; d=json.load(sys.stdin)
for bid,b in d['result']['Blocks'].items():
    print(bid, b.get('Description',''), len(b.get('BlockElements',[])), 'elements')
"
```

**Get full question:**
```bash
curl -s "${HDR[@]}" "$BASE/survey-definitions/$SID/questions/QID42" | python3 -m json.tool
```

**Create a text question in a block:**
```bash
curl -s -X POST "${HDR[@]}" \
  "$BASE/survey-definitions/$SID/questions?blockId=BL_xxxxx" \
  -d '{"QuestionText":"<p>Your text</p>","QuestionType":"DB","Selector":"TB","DataExportTag":"my_tag"}'
```

**Update question text:**
```bash
curl -s -X PUT "${HDR[@]}" \
  "$BASE/survey-definitions/$SID/questions/QID42" \
  -d '{"QuestionText":"<p>Updated text</p>"}'
```

**Export responses to CSV:**
```bash
PID=$(curl -s -X POST "${HDR[@]}" \
  "$BASE/surveys/$SID/export-responses" \
  -d '{"format":"csv","useLabels":false}' | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['progressId'])")

while true; do
  STATUS=$(curl -s "${HDR[@]}" "$BASE/surveys/$SID/export-responses/$PID" | python3 -c "import sys,json;r=json.load(sys.stdin)['result'];print(r['status'],r.get('fileId',''))")
  echo "$STATUS"
  [[ "$STATUS" == complete* ]] && break
  sleep 3
done

FID=$(echo "$STATUS" | awk '{print $2}')
curl -s "${HDR[@]}" "$BASE/surveys/$SID/export-responses/$FID/file" -o responses.zip
```

---

## Useful Python patterns

**Get and update a question (preserving existing fields):**
```python
import requests

def get_question(base, survey_id, qid, token):
    r = requests.get(f"{base}/survey-definitions/{survey_id}/questions/{qid}",
                     headers={"X-API-TOKEN": token})
    return r.json()["result"]

def update_question(base, survey_id, qid, payload, token):
    r = requests.put(f"{base}/survey-definitions/{survey_id}/questions/{qid}",
                     headers={"X-API-TOKEN": token, "Content-Type": "application/json"},
                     json=payload)
    r.raise_for_status()
```

**Find block by name:**
```python
def find_block_by_name(base, sid, name, token):
    r = requests.get(f"{base}/survey-definitions/{sid}",
                     headers={"X-API-TOKEN": token})
    blocks = r.json()["result"]["Blocks"]
    for bid, b in blocks.items():
        if b.get("Description") == name:
            return bid, b
    return None, None
```

---

## ID prefixes cheat-sheet

| Resource | Prefix | Example |
|----------|--------|---------|
| Survey | `SV_` | `SV_aWrEE8bXIdc6Pqe` |
| Block | `BL_` | `BL_87jwAfV9LnayNEO` |
| Question | `QID` | `QID19` |
| Export progress | `ES_` | `ES_abc123` |
| Export file | `ExportFile_` | `ExportFile_xyz` |

---

## Common errors

| HTTP | Code | Fix |
|------|------|-----|
| 400 | `VALIDATION_ERROR` | Check request body field names and types |
| 401 | `AUTH_USER_NOT_FOUND` | Token missing or invalid |
| 403 | `AUTH_INSUFFICIENT_PERMISSIONS` | Token lacks write access |
| 404 | `RESOURCE_NOT_FOUND` | Wrong survey/block/question ID |
| 409 | `DUPLICATE_RESOURCE` | DataExportTag already in use |

---

## Instructions

1. **Always** load credentials via `source qualtrics/qualtrics_env.sh` before making API calls.
2. Use `/survey-definitions/` for all structural edits (questions, blocks, flow, options).
3. Use `/surveys/` only for export and read-only metadata.
4. Verify the operation succeeded by re-fetching the resource after a PUT/POST.
5. When updating a question, GET it first to preserve existing fields, then merge changes and PUT back.
