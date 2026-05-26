---
name: workbook-corruption-recovery
description: Recover from "Bad magic number for central directory" (or similar zipfile corruption errors) when opening the ADVANCE live workbook with openpyxl. The on-disk file may look valid (PK header OK, MD5 matches a known backup) but openpyxl refuses to load it because the ZIP central directory is mid-write or trailing bytes are off. Invoke whenever an ADVANCE script raises `zipfile.BadZipFile` on `Qualtrics_ADVANCE_recruitment_live.xlsx` or similar — before assuming the file is truly destroyed.
---

# Workbook Corruption Recovery — openpyxl "Bad magic number for central directory"

The ADVANCE live workbook is a shared OneDrive file that the 15-min cycle reads + writes through `rclone`. Mid-cycle, the local copy can be in an intermediate state where the PK header looks right but the central directory at the end of the file is incomplete. openpyxl raises:

```
zipfile.BadZipFile: Bad magic number for central directory
```

This is almost never real corruption — it's a temporary state. The fix is usually a fresh pull from OneDrive.

---

## Diagnosis (in order)

```bash
# 1. Is the PK header intact? (should print "PK..")
head -c 4 ~/email_draft_automation/Qualtrics_ADVANCE_recruitment_live.xlsx | xxd

# 2. Is the End-of-Central-Directory record intact? (should end with PK\05\06 + ~20 bytes)
tail -c 50 ~/email_draft_automation/Qualtrics_ADVANCE_recruitment_live.xlsx | xxd

# 3. file(1) says it's still an xlsx?
file ~/email_draft_automation/Qualtrics_ADVANCE_recruitment_live.xlsx
# expected: Microsoft Excel 2007+

# 4. md5 it vs the latest daily backup
md5sum ~/email_draft_automation/Qualtrics_ADVANCE_recruitment_live.xlsx \
       ~/email_draft_automation/backups/Qualtrics_ADVANCE_recruitment_live_$(date +%F).xlsx
```

If steps 1–3 pass but openpyxl still fails, the file is in transit — proceed to recovery.

---

## Recovery — pull from OneDrive

The authoritative copy lives on OneDrive. The local server file may be stale or mid-write. Pull a fresh copy:

```bash
bash ~/email_draft_automation/run/run_rclone_excel_sync.sh
```

This runs `rclone copy` with the one-way pull contract (OneDrive → local; never the other direction). After it completes, retry the openpyxl load:

```python
from openpyxl import load_workbook
wb = load_workbook("Qualtrics_ADVANCE_recruitment_live.xlsx", read_only=True, data_only=True)
print(wb.sheetnames[:6])
wb.close()
```

If this now works, you're done. If it still fails, see "If pull doesn't help" below.

---

## If pull doesn't help

In rare cases the corruption is real. Options in increasing order of intrusiveness:

1. **Try `zip -FF` salvage** on a copy (never on the live file):
   ```bash
   cp Qualtrics_ADVANCE_recruitment_live.xlsx /tmp/wb.xlsx
   zip -FF /tmp/wb.xlsx --out /tmp/wb_fixed.xlsx
   .venv/bin/python3 -c "from openpyxl import load_workbook; load_workbook('/tmp/wb_fixed.xlsx', read_only=True)"
   ```
   Note: `zip -FF` is interactive; pipe `y\n` if running unattended.

2. **Fall back to the most recent backup**:
   ```bash
   ls -lt ~/email_draft_automation/backups/Qualtrics_ADVANCE_recruitment_live_*.xlsx | head -3
   cp ~/email_draft_automation/backups/Qualtrics_ADVANCE_recruitment_live_<latest>.xlsx \
      ~/email_draft_automation/Qualtrics_ADVANCE_recruitment_live.xlsx
   ```
   Backups are daily at 01:01 server time. Coordinate with the team before overwriting the live file — the cycle may have made important writes since the last backup.

3. **Ask the user to re-save the file from Excel** (sometimes the canonical fix when the OneDrive copy is also corrupt). Excel re-writes a clean ZIP central directory on save.

---

## Defensive code patterns

Any tool that opens the live workbook should degrade gracefully when load fails — especially read-only diagnostics that don't strictly need the workbook. Pattern:

```python
def _load_or_warn(path):
    try:
        return load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        logger.warning("Workbook load failed (%s); proceeding with empty fallback.", exc)
        return None
```

The ADVANCE `build_template_matrix.py` uses this pattern — if the workbook is mid-write, the matrix is built with empty recipient lookups (record_id columns blank) and the user can re-run later when the file settles. Better than crashing the diagnostic.

---

## Anti-patterns to avoid

- ❌ Assuming the file is dead and reaching for backups before trying `rclone_excel_sync.sh`. Most "corruption" is transient.
- ❌ Running `rclone_excel_push.sh` while the live workbook is in a weird state — you'll propagate the corruption back to OneDrive. Pull first, verify, then push.
- ❌ Editing the workbook directly while the 15-min cycle is running. Stop the cycle (`reference_manual_cycle_control` memory) before any surgical write.
- ❌ Blindly `cp backups/<latest>.xlsx live.xlsx` without coordinating — the cycle may have written stamps in between that aren't in the backup.

---

## Reference incident

2026-05-26: `build_template_matrix.py` failed with `zipfile.BadZipFile: Bad magic number for central directory` on the live workbook (size 299467, file(1) said valid xlsx, PK\05\06 EOCD present at the right offset). `run_rclone_excel_sync.sh` pulled a fresh 318KB copy from OneDrive that loaded fine. Root cause was a mid-rclone-push window on the server. Total resolution time: 30 seconds once the right command was run.
