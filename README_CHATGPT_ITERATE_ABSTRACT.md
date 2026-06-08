# ChatGPT Abstract Iterator

Batch-process thousands of literature entries through ChatGPT using Selenium — no API key required.  
Designed to run across **multiple computers sharing the same Google Drive folder**, with SQLite-backed locking to prevent duplicate work.

---

## How it works

```
complete_file_available_in_zotero.csv   ← master literature list (Google Drive)
promp_check_blink.md                    ← prompt template (Google Drive)
         │
         ▼  (first run: import CSV → SQLite)
chatgpt_processing.db                   ← SQLite tracking database (Google Drive, shared)
         │
         ▼  (each machine claims a batch of rows atomically)
         │
         ▼  Selenium → Chrome → chatgpt.com
         │
         ▼
chatgpt_outputs/
  ddf8ef2137a0b3ba.json                 ← one JSON file per article (DOI hash as filename)
  e530020afbd24b1d.json
  ...
```

Each row goes through these statuses:

| Status | Meaning |
|---|---|
| `Yet To Process` | Not started — eligible for claiming |
| `Already Processing` | Claimed by a machine, about to start |
| `In Progress` | Selenium has sent the prompt, waiting for response |
| `Completed` | JSON output saved successfully |
| `Failed` | Error occurred — will be retried up to `max_retries` times |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | Anaconda recommended |
| Google Chrome 120+ | Must be installed |
| `selenium` | `pip install selenium` |
| `webdriver-manager` | `pip install webdriver-manager` |
| `pyyaml` | `pip install pyyaml` |
| Shared Google Drive folder | All computers must sync the same folder |

ChromeDriver is resolved automatically by `webdriver-manager`.  
The bundled fallback is at `apm/browser/chromedriver.exe`.

---

## Configuration — `setting/chatgpt_ui/config.yaml`

```yaml
project_root: "C:/Users/balan/My Drive (balandong@ums.edu.my)/iterate_literature_review"

input:
  master_file: "complete_file_available_in_zotero.csv"   # CSV to import from
  prompt_file: "promp_check_blink.md"                    # prompt template

output:
  json_output_folder: "chatgpt_outputs"                  # folder for per-article JSON

processing:
  batch_size: 10          # rows to claim per run
  machine_id: ""          # leave blank → auto-detected from hostname
  max_retries: 3          # how many times a Failed row is retried
  stale_lock_hours: 2.0   # reclaim rows locked longer than this (crashed-machine recovery)

selenium:
  browser: "chrome"
  headless: false         # true = run without visible window (login must already be saved)
  wait_seconds: 120       # max seconds to wait for ChatGPT to finish responding
  chrome_exe: "C:/Users/balan/AppData/Local/Google/Chrome/Application/chrome.exe"
  chrome_profile: "C:/selenium/chrome-profile"           # separate from your regular Chrome
```

### Key settings to change per computer

| Setting | Why you might change it |
|---|---|
| `project_root` | Must match the local path to your Google Drive sync folder |
| `machine_id` | Leave blank to use the hostname automatically, or set `"computer_2"` explicitly |
| `batch_size` | Reduce to `5` on a slow connection; increase to `20` on a fast machine |
| `chrome_exe` | Update if Chrome is installed at a non-default path |
| `chrome_profile` | Must be the same path used when you first logged in to ChatGPT |
| `stale_lock_hours` | Increase to `4.0` if a single article takes a very long time |

---

## First-time setup — log in to ChatGPT

The Selenium Chrome profile stores your login session so you only log in once per computer.

1. Run the batch script once on the computer.
2. Chrome opens and shows the ChatGPT login page.
3. Click **Continue with Google** and complete sign-in.
4. Return to the terminal and press **Enter** when prompted.

From that point on, all future runs on that computer skip the login step automatically.

---

## Running the batch

All commands are run from the project repository root (`C:\Users\balan\IdeaProjects\academic_paper_maker`).

### Step 1 — Import the CSV

On the first run, import the master CSV into the SQLite database:

```bash
python -m apm.chatgpt_ui.run_batch --import-only
```

This is safe to re-run at any time. New rows are added; already-imported rows are skipped.

### Step 2 — Check what is pending

```bash
python -m apm.chatgpt_ui.run_batch --stats
```

Example output:

```
--- Processing stats ---
  Yet To Process              10812
  Completed                       0
  TOTAL                       10812
```

### Step 3 — Process a batch

```bash
python -m apm.chatgpt_ui.run_batch
```

The script will:
1. Import any new rows from the CSV.
2. Atomically claim the next `batch_size` rows.
3. Open Chrome (log in if needed).
4. Send each abstract to ChatGPT using the prompt template.
5. Save the response as a JSON file.
6. Mark each row `Completed` or `Failed` in the database.

### Override options

```bash
# Override machine ID (useful if hostname is not descriptive)
python -m apm.chatgpt_ui.run_batch --machine-id computer_2

# Use a different config file
python -m apm.chatgpt_ui.run_batch --config path/to/other_config.yaml

# Verbose logging (debug level)
python -m apm.chatgpt_ui.run_batch --verbose
```

---

## Multi-computer setup

All computers must:

1. Have Google Drive syncing the shared folder.
2. Have the same `project_root` path **as seen locally** in `config.yaml`.
3. Have Chrome installed and the Selenium profile logged in.
4. Have this repository cloned and dependencies installed.

Because the SQLite database sits on the shared Drive folder, machines coordinate automatically:

- Each machine runs `python -m apm.chatgpt_ui.run_batch` independently.
- SQLite's `BEGIN IMMEDIATE` transaction ensures no two machines claim the same row.
- If a machine crashes mid-batch, its rows are automatically reclaimed after `stale_lock_hours`.

### Example setup for three computers

**`setting/chatgpt_ui/config.yaml` on computer_1:**
```yaml
project_root: "C:/Users/balan/My Drive (balandong@ums.edu.my)/iterate_literature_review"
processing:
  machine_id: "computer_1"
  batch_size: 10
```

**`setting/chatgpt_ui/config.yaml` on computer_2:**
```yaml
project_root: "C:/Users/user2/Google Drive/iterate_literature_review"
processing:
  machine_id: "computer_2"
  batch_size: 10
```

Only `project_root` and `machine_id` need to differ. Everything else can be identical.

---

## Prompt template — `promp_check_blink.md`

The prompt file sits in `project_root` (on the shared Drive).  
The script appends the article's Title and Abstract Note after the template:

```
<contents of promp_check_blink.md>

Title: Detection of eye blink artifacts from single prefrontal channel EEG
Abstract: Eye blinks are one of the most influential artifact sources...
```

Edit `promp_check_blink.md` to change what question is asked — no code changes needed.  
Changes take effect immediately on the next run.

---

## Output JSON format

Each processed article is saved as `<doi_hash>.json` in the `chatgpt_outputs` folder:

```json
{
  "title": "Detection of eye blink artifacts from single prefrontal channel electroencephalogram",
  "doi": "10.1016/j.cmpb.2015.10.011",
  "doi_hash": "ddf8ef2137a0b3ba",
  "source_row": {
    "row_index": 1,
    "record_id": "EXMLDRXM",
    "Author": "Chang, Won-Du; ...",
    "Publication Year": "2016",
    "...": "all other CSV columns are included"
  },
  "chatgpt_response": {
    "raw_text": "{ \"is_relevant\": false, \"relevance_reason\": \"...\" }",
    "parsed_json": {
      "is_relevant": false,
      "relevance_reason": "The abstract involves EEG data and a computational rule-based artifact detection method..."
    },
    "parse_error": null
  },
  "processing_metadata": {
    "machine_id": "rpb",
    "processed_at": "2026-06-08T12:19:06.123456",
    "status": "Completed",
    "error": null
  }
}
```

- `doi_hash` is the first 16 hex characters of `SHA-256(doi)`. Used as a stable, filesystem-safe filename.
- `chatgpt_response.parsed_json` is populated if ChatGPT returned valid JSON (most prompts are written to request JSON output).
- `chatgpt_response.parse_error` contains the parse error string if JSON parsing failed; `raw_text` always holds the original.

---

## Reprocessing completed rows

To force-reprocess rows that are already `Completed` (e.g. after changing the prompt template):

```python
# Reset all rows to 'Yet To Process'
import sys; sys.path.insert(0, '.')
from pathlib import Path
from apm.chatgpt_ui.config import load_config
from apm.chatgpt_ui.database import open_db, STATUS_PENDING

cfg  = load_config('setting/chatgpt_ui/config.yaml')
conn = open_db(cfg.db_path)
with conn:
    conn.execute("UPDATE articles SET status=?, machine_id=NULL, locked_at=NULL, output_file=NULL, error_message=NULL, retry_count=0", (STATUS_PENDING,))
conn.close()
print("All rows reset to 'Yet To Process'.")
```

Then delete the old JSON files and re-run:

```bash
# Delete old outputs (PowerShell)
Remove-Item "C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review\chatgpt_outputs\*.json"

# Re-run
python -m apm.chatgpt_ui.run_batch
```

---

## Module structure

```
apm/chatgpt_ui/
  __init__.py         — public API reference
  config.py           — YAML config loader (dataclasses)
  database.py         — SQLite store: schema, import, claim, update, stats
  csv_store.py        — CSV inspection and validation helpers
  locking.py          — advisory .lock file for shared-folder writes
  selenium_client.py  — Chrome driver builder + ChatGPT send/wait logic
  processor.py        — per-row pipeline: prompt → ChatGPT → JSON → DB update
  output_writer.py    — builds the JSON output dict, parses ChatGPT response
  run_batch.py        — CLI entry point

setting/chatgpt_ui/
  config.yaml         — all runtime settings (edit this, not the code)

tutorial/
  run_chatgpt_prompt.py   — minimal one-shot example (delegates to apm.chatgpt_ui)
```

---

## Troubleshooting

### `SessionNotCreatedException: Chrome instance exited`

A previous Selenium Chrome session is still running with the same profile locked.

```powershell
# Kill all Chrome processes
Stop-Process -Name chrome -Force
```

Then re-run the batch.

### Rows stuck at `Already Processing`

If a machine crashed mid-batch, its rows stay locked.  
They are automatically reclaimed after `stale_lock_hours` (default: 2 hours).  
To reclaim immediately:

```python
import sys; sys.path.insert(0, '.')
from apm.chatgpt_ui.config import load_config
from apm.chatgpt_ui.database import open_db, STATUS_PENDING

cfg  = load_config('setting/chatgpt_ui/config.yaml')
conn = open_db(cfg.db_path)
with conn:
    conn.execute(
        "UPDATE articles SET status=?, machine_id=NULL, locked_at=NULL "
        "WHERE status IN ('Already Processing', 'In Progress')",
        (STATUS_PENDING,)
    )
conn.close()
```

### ChatGPT returned an empty response

The script raises `ValueError: ChatGPT returned an empty response` and marks the row `Failed`.  
It will be retried automatically on the next run (up to `max_retries` times).  
Check the JSON `processing_metadata.error` field for details.

### Database file locked (`sqlite3.OperationalError: database is locked`)

Happens briefly when two machines try to write at the same moment.  
The script retries automatically up to 5 times with increasing delays.  
If it persists, ensure all machines use the same Drive sync folder and no other program has the `.db` file open.

### `No new rows to import` but the CSV was updated

Re-run with `--import-only`. The importer adds only rows whose DOI hash is not already in the database, so new rows in the CSV are picked up safely.

### ChatGPT shows a "Usage limit reached" banner

The script does not currently detect rate-limit banners. If ChatGPT stops responding,  
the rows will time out after `wait_seconds` and be marked `Failed` for retry.  
Wait for the limit to reset, then re-run.
