# Abstract Screening Pipeline — EEG Driver Fatigue Papers

Screens `complete_file_available_in_zotero.csv` (10,842 papers) down to papers
relevant to **EEG-based machine learning for driver fatigue / drowsiness detection**,
using a two-stage approach:

| Stage | Method | Input | Output |
|-------|--------|-------|--------|
| 1 — SQL pre-filter | Keyword matching on title + abstract | 10,842 papers | ~968 candidates |
| 2 — AI screening | ChatGPT evaluates each abstract | 968 candidates | relevant papers CSV |

All state is stored in a SQLite database on Google Drive, so the run can be
**stopped and resumed at any time** across multiple computers.

---

## Quick start

```powershell
cd C:\Users\balan\IdeaProjects\academic_paper_maker

# 1 — First run: import and inspect candidates (no ChatGPT yet)
python screen_abstracts.py --import-only

# 2 — Open the candidates CSV to verify the SQL filter looks right
#     C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review\candidates_eeg_fatigue_driver.csv

# 3 — Run a small trial (batch_size is 3 in config — change to 20 when ready)
python screen_abstracts.py

# 4 — Keep re-running to process the remaining candidates
python screen_abstracts.py --batch-size 20

# 5 — At any point, export the papers found so far
python screen_abstracts.py --export-relevant
```

---

## Config file — `setting/chatgpt_ui/config_fatigue_eeg.yaml`

```yaml
project_root: "C:/Users/balan/My Drive (balandong@ums.edu.my)/iterate_literature_review"

input:
  master_file: "complete_file_available_in_zotero.csv"   # source CSV
  prompt_file: "prompt_check_eeg_fatigue_driving.md"     # ChatGPT screening prompt

output:
  json_output_folder: "fatigue_eeg_outputs"              # one JSON per screened paper
  db_file: "chatgpt_fatigue_eeg.db"                      # SQLite tracking database

processing:
  batch_size: 3            # papers to claim per run — change to 20 for full sweep
  machine_id: ""           # leave blank → auto-detected from hostname
  max_retries: 3           # retry failed rows up to this many times
  stale_lock_hours: 2.0    # reclaim rows locked longer than this (crashed-machine recovery)
  keyword_filter: ...      # SQL WHERE fragment — only these rows are sent to ChatGPT

selenium:
  headless: false
  wait_seconds: 120        # max seconds to wait for ChatGPT to respond
  chrome_exe: "C:/Users/balan/AppData/Local/Google/Chrome/Application/chrome.exe"
  chrome_profile: "C:/selenium/chrome-profile"
```

### Key settings to change

| Setting | When to change |
|---------|---------------|
| `batch_size` | Use `3` for a trial; use `20` for the full sweep |
| `machine_id` | Set to `"computer_2"` etc. when running on a second machine |
| `keyword_filter` | Edit the SQL fragment to broaden or narrow the candidate set |

---

## All command-line options

```
python screen_abstracts.py [OPTIONS]

  --config PATH          YAML config file (default: setting/chatgpt_ui/config_fatigue_eeg.yaml)
  --import-only          Import CSV → DB, refresh candidates CSV, show stats, exit (no ChatGPT)
  --export-candidates    Refresh candidates_eeg_fatigue_driver.csv and exit
  --export-relevant      Refresh relevant_fatigue_eeg.csv from existing JSON outputs and exit
  --stats                Show database stats and exit
  --batch-size N         Override batch_size from config for this run
  --rescreen             Reset completed rows and delete their outputs so they are screened again
  --verbose / -v         DEBUG-level logging
```

---

## Pipeline steps (what `screen_abstracts.py` does)

```
Step 1 — Import CSV
    Reads complete_file_available_in_zotero.csv and inserts new rows into
    chatgpt_fatigue_eeg.db. Already-imported rows are skipped (safe to re-run).

Step 2 — Export candidates CSV
    Runs a SQL keyword query (EEG AND fatigue/drowsiness AND driver/driving)
    against the database and writes candidates_eeg_fatigue_driver.csv.
    968 papers out of 10,842 match. Open this CSV to verify the filter.

Step 3 — Screen abstracts via ChatGPT
    Claims the next batch_size rows that match the keyword filter.
    For each paper, sends Title + Abstract to ChatGPT using the prompt template.
    Saves the response as a JSON file in fatigue_eeg_outputs/.
    Marks the row Completed or Failed in the database.

Step 4 — Export relevant papers CSV
    Reads all JSON files in fatigue_eeg_outputs/, collects papers where
    is_relevant=true, and writes relevant_fatigue_eeg.csv.
    Safe to run at any time — even mid-sweep.
```

---

## Output files (all on Google Drive)

| File | Description |
|------|-------------|
| `candidates_eeg_fatigue_driver.csv` | 968 keyword-filtered candidates — open to verify the SQL filter |
| `relevant_fatigue_eeg.csv` | Papers marked relevant by ChatGPT — your final literature set |
| `fatigue_eeg_outputs/*.json` | One JSON per screened paper (ChatGPT response + metadata) |
| `chatgpt_fatigue_eeg.db` | SQLite database tracking processing status of every paper |

### `candidates_eeg_fatigue_driver.csv` columns

`id`, `doi_hash`, `doi`, `title`, `publication_year`, `abstract`, `author`, `publication_title`, `status`

### `relevant_fatigue_eeg.csv` columns

`doi_hash`, `doi`, `title`, `publication_year`, `is_relevant`, `relevance_reason`,
`data_source`, `eeg_usage`, `preprocessing`, `feature_extraction`,
`machine_learning_method`, `evaluation_method`, `key_findings`,
`machine_id`, `processed_at`, `output_file`

---

## Row statuses in the database

| Status | Meaning |
|--------|---------|
| `Yet To Process` | Not started — eligible for claiming |
| `Already Processing` | Claimed by a machine, about to start |
| `In Progress` | ChatGPT has been sent the prompt, waiting for response |
| `Completed` | JSON output saved successfully |
| `Failed` | Error — will be retried up to `max_retries` times |

---

## Skipping already-screened papers (default) vs. re-screening

By default every run **skips** rows that are already `Completed`.
The log will tell you how many are being skipped:

```
INFO  Skipping 250 already-completed rows. Use --rescreen to re-screen them.
INFO  718 rows eligible for this batch.
```

To re-screen from scratch — for example after editing the prompt template — use `--rescreen`:

```powershell
python screen_abstracts.py --rescreen --batch-size 20
```

What `--rescreen` does:
1. Resets every `Completed` row (that matches the keyword filter) back to `Yet To Process`
2. Deletes the corresponding JSON output files
3. Proceeds with a normal batch run

Only rows that match the keyword filter are reset — papers that would never be sent
to ChatGPT anyway (e.g. eye-blink papers outside the filter) are left untouched.

---

## Resume after interruption

The pipeline resumes automatically. Re-run the same command:

```powershell
python screen_abstracts.py --batch-size 20
```

- Rows already `Completed` are skipped.
- Rows stuck at `Already Processing` are automatically reclaimed after `stale_lock_hours`.
- To reclaim stuck rows immediately:

```python
from apm.chatgpt_ui.config import load_config
from apm.chatgpt_ui.database import open_db, STATUS_PENDING

cfg  = load_config("setting/chatgpt_ui/config_fatigue_eeg.yaml")
conn = open_db(cfg.db_path)
with conn:
    conn.execute(
        "UPDATE articles SET status=?, machine_id=NULL, locked_at=NULL "
        "WHERE status IN ('Already Processing', 'In Progress')",
        (STATUS_PENDING,)
    )
conn.close()
```

---

## Multi-computer setup

Each computer needs:
1. Google Drive syncing the same folder.
2. Chrome installed + Selenium profile logged in to ChatGPT.
3. This repo cloned with dependencies installed.
4. A copy of `config_fatigue_eeg.yaml` with `project_root` matching its local Drive path.

Set a distinct `machine_id` on each computer so logs are attributable:

```yaml
processing:
  machine_id: "computer_2"
```

Then run `python screen_abstracts.py --batch-size 20` on each machine independently.
SQLite `BEGIN IMMEDIATE` transactions prevent any two machines from claiming the same row.

---

## Logs

Each run writes a timestamped log file to `logs/screen_abstracts_YYYYMMDD_HHMMSS.log`.
The same output is also printed to the console.

---

## Troubleshooting

### `session not created: Chrome instance exited`
Another Chrome instance is holding the Selenium profile lock.

```powershell
Stop-Process -Name chrome -Force -Confirm:$false
python screen_abstracts.py
```

### `database is locked`
Two machines are writing simultaneously. The script retries automatically up to 5 times.
If it persists, ensure all machines sync the same Drive folder.

### ChatGPT rate limit reached
Rows time out after `wait_seconds` and are marked `Failed` for automatic retry.
Wait for the limit to reset, then re-run.

### Check what has been processed so far

```powershell
python screen_abstracts.py --stats
```

---

## Module map

```
screen_abstracts.py                  ← single entry point (this script)
setting/chatgpt_ui/
  config_fatigue_eeg.yaml            ← all runtime settings

apm/chatgpt_ui/
  config.py                          ← YAML config loader
  database.py                        ← SQLite store + keyword-filtered claim_rows
  export_candidates.py               ← keyword-filtered candidates → CSV
  export_relevant.py                 ← relevant papers → CSV
  processor.py                       ← per-row pipeline: prompt → ChatGPT → JSON
  selenium_client.py                 ← Chrome driver + ChatGPT send/wait logic
  output_writer.py                   ← builds JSON output, parses ChatGPT response

C:/.../iterate_literature_review/    (Google Drive)
  complete_file_available_in_zotero.csv
  prompt_check_eeg_fatigue_driving.md
  chatgpt_fatigue_eeg.db
  candidates_eeg_fatigue_driver.csv
  relevant_fatigue_eeg.csv
  fatigue_eeg_outputs/
```
