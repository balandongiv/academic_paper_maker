# Handoff — Abstract Screening (EEG Driver Fatigue)

**Created:** 2026-06-09 06:38  
**Status at handoff:** Loop was running, interrupted by laptop restart  
**Resumed:** 2026-06-09 on machine `rpb` (G: drive mapped to Google Drive)

---

## DB state at handoff

| Status | Count |
|--------|-------|
| Yet To Process | 10,720 |
| Already Processing | 98 ← stuck, reclaim on resume |
| In Progress | 1 ← stuck, reclaim on resume |
| Completed | 6 |
| Failed | 17 |
| **Keyword candidates (968 total screened so far)** | **6 done, ~962 remaining** |

## DB state at resume (2026-06-09, machine rpb)

| Status | Count |
|--------|-------|
| Yet To Process | 10,696 (18 reclaimed from stuck) |
| Completed | 129 |
| Failed | 17 |

Config paths updated for this machine:
- `project_root` → `G:/My Drive/iterate_literature_review`
- `chrome_exe` → `C:/Program Files/Google/Chrome/Application/chrome.exe`
- Chrome profile dir created: `C:\selenium\chrome-profile`

---

## What was done before restart

1. Full `--rescreen` was triggered — all previous results from the old prompt were wiped.
2. New prompt `prompt_check_eeg_fatigue_driving.md` is live on Google Drive.
3. `run_until_done.py` was running the loop (batch-size 20, auto Chrome kill between batches).
4. Only ~6 papers completed under the new prompt before the restart.

---

## Resume steps after restart

### Step 1 — Reclaim stuck rows (mandatory first step)

```powershell
cd C:\Users\balan\IdeaProjects\academic_paper_maker

python -c "
from apm.chatgpt_ui.config import load_config
from apm.chatgpt_ui.database import open_db, STATUS_PENDING
cfg = load_config('setting/chatgpt_ui/config_fatigue_eeg.yaml')
conn = open_db(cfg.db_path)
with conn:
    cur = conn.execute(\"UPDATE articles SET status=?, machine_id=NULL, locked_at=NULL WHERE status IN ('Already Processing', 'In Progress')\", (STATUS_PENDING,))
    print(f'Reclaimed {cur.rowcount} stuck rows')
conn.close()
"
```

### Step 2 — Run the auto-loop until all 968 are done

```powershell
python run_until_done.py
```

That's it. The loop runs batches of 20, kills Chrome between each batch, and stops automatically when all 968 keyword-candidates are completed.

---

## Check progress at any time

```powershell
python screen_abstracts.py --stats
```

## Export relevant papers at any time

```powershell
python screen_abstracts.py --export-relevant
# Output: C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review\relevant_fatigue_eeg.csv
```

---

## Key files

| File | Location |
|------|----------|
| Config | `setting/chatgpt_ui/config_fatigue_eeg.yaml` |
| Loop script | `run_until_done.py` |
| Main script | `screen_abstracts.py` |
| Prompt (new) | Google Drive: `iterate_literature_review/prompt_check_eeg_fatigue_driving.md` |
| Database | Google Drive: `iterate_literature_review/chatgpt_fatigue_eeg.db` |
| JSON outputs | Google Drive: `iterate_literature_review/fatigue_eeg_outputs/` |
| Relevant CSV | Google Drive: `iterate_literature_review/relevant_fatigue_eeg.csv` |
| Logs | `logs/screen_abstracts_*.log` |

---

## If something goes wrong

**Too many Chrome windows open:**
```powershell
Stop-Process -Name chrome -Force -Confirm:$false
# then reclaim stuck rows (Step 1 above), then re-run loop
```

**Check what's in the relevant CSV so far:**
```powershell
python screen_abstracts.py --export-relevant
```

**Full re-screen from scratch (only if prompt changes again):**
```powershell
python screen_abstracts.py --rescreen --batch-size 20
# then run the loop
```
