# ChatGPT Browser Automation

Selenium-based scripts that open ChatGPT in Chrome, send prompts, extract responses, and save results — no API key required.

Two modes are available:

| Mode | Script | Use case |
|---|---|---|
| **Single prompt** | `tutorial/run_chatgpt_prompt.py` | Test a prompt interactively |
| **Batch iterator** | `python -m apm.chatgpt_ui.run_batch` | Process thousands of abstracts across multiple computers |

For full batch documentation see [README_CHATGPT_ITERATE_ABSTRACT.md](README_CHATGPT_ITERATE_ABSTRACT.md).

---

## How it works

The scripts control the **ChatGPT web UI** directly through Chrome using Selenium WebDriver.  
A dedicated Chrome profile (`C:\selenium\chrome-profile`) stores your login session, so you only need to log in once per computer.

```
promp_check_blink.md                        ← prompt template (editable, no code change needed)
complete_file_available_in_zotero.csv       ← master literature list
        │
        ▼  (import once)
chatgpt_processing.db                       ← SQLite tracking database (shared via Google Drive)
        │
        ▼  (each computer claims rows atomically)
        │  Selenium → Chrome → chatgpt.com
        ▼
chatgpt_outputs/
  ddf8ef2137a0b3ba.json                     ← one JSON file per processed article
  e530020afbd24b1d.json
  ...
```

---

## Module structure

```
apm/chatgpt_ui/
  __init__.py         — public API reference
  config.py           — YAML config loader
  database.py         — SQLite store: import, atomic row claiming, status tracking
  csv_store.py        — CSV inspection and validation helpers
  locking.py          — advisory .lock file for shared-folder operations
  selenium_client.py  — Chrome driver + ChatGPT send/wait logic
  processor.py        — per-row pipeline: prompt → ChatGPT → save JSON → update DB
  output_writer.py    — builds the output JSON, parses ChatGPT response
  run_batch.py        — CLI entry point

setting/chatgpt_ui/
  config.yaml         — all runtime settings

tutorial/
  run_chatgpt_prompt.py   — one-shot example (delegates to apm.chatgpt_ui)
```

---

## Prerequisites

| Requirement | Version tested |
|---|---|
| Python | 3.10+ |
| Google Chrome | 148+ |
| selenium | `pip install selenium` |
| webdriver-manager | `pip install webdriver-manager` |
| pyyaml | `pip install pyyaml` |

ChromeDriver is resolved automatically by `webdriver-manager`.  
The bundled fallback is at `apm/browser/chromedriver.exe`.

---

## First-time setup — log in to ChatGPT

1. Run either script once.
2. Chrome opens and shows the ChatGPT login page.
3. Click **Continue with Google** and complete sign-in.
4. Return to the terminal and press **Enter** when prompted.

The session is saved in the Selenium profile. All future runs skip the login step automatically.

---

## Script 1 — Single prompt: `tutorial/run_chatgpt_prompt.py`

Sends one prompt to ChatGPT, prints the response in the terminal.  
This script is a thin wrapper around `apm.chatgpt_ui` — all logic lives in the module.

### Usage

```bash
# Default prompt (machine learning example)
python tutorial/run_chatgpt_prompt.py

# Custom prompt
python tutorial/run_chatgpt_prompt.py "Explain gradient descent in 3 bullet points"
python tutorial/run_chatgpt_prompt.py "Summarise the PRISMA checklist for systematic reviews"
```

Settings are read from `setting/chatgpt_ui/config.yaml` — Chrome path, profile directory, and wait timeout all come from there.

---

## Script 2 — Batch abstract iterator: `apm.chatgpt_ui.run_batch`

Processes the full literature CSV through ChatGPT.  
Uses SQLite for atomic row claiming so multiple computers can run simultaneously without duplicate work.

### Quick start

```bash
# 1. Import CSV into SQLite (safe to re-run)
python -m apm.chatgpt_ui.run_batch --import-only

# 2. Check pending rows
python -m apm.chatgpt_ui.run_batch --stats

# 3. Process next batch
python -m apm.chatgpt_ui.run_batch

# 4. Override machine ID (for multi-computer setups)
python -m apm.chatgpt_ui.run_batch --machine-id computer_2
```

See [README_CHATGPT_ITERATE_ABSTRACT.md](README_CHATGPT_ITERATE_ABSTRACT.md) for the full guide.

### Processing statuses

| Status | Meaning |
|---|---|
| `Yet To Process` | Not started |
| `Already Processing` | Claimed by a machine |
| `In Progress` | Selenium prompt submitted, waiting for response |
| `Completed` | JSON output saved |
| `Failed` | Error — retried up to `max_retries` times |

---

## Configuration — `setting/chatgpt_ui/config.yaml`

```yaml
project_root: "C:/Users/balan/My Drive (balandong@ums.edu.my)/iterate_literature_review"

input:
  master_file: "complete_file_available_in_zotero.csv"
  prompt_file: "promp_check_blink.md"

output:
  json_output_folder: "chatgpt_outputs"

processing:
  batch_size: 10
  machine_id: ""          # blank = auto-detect from hostname
  max_retries: 3
  stale_lock_hours: 2.0   # reclaim rows locked longer than this

selenium:
  browser: "chrome"
  headless: false
  wait_seconds: 120
  chrome_exe: "C:/Users/balan/AppData/Local/Google/Chrome/Application/chrome.exe"
  chrome_profile: "C:/selenium/chrome-profile"
```

The only file you need to edit between computers is `config.yaml` — change `project_root` and optionally `machine_id`.

---

## Troubleshooting

### `SessionNotCreatedException: Chrome instance exited`

A leftover Selenium Chrome session is holding the profile lock.

```powershell
Stop-Process -Name chrome -Force
```

Then re-run.

### Rows stuck at `Already Processing`

Rows are auto-recovered after `stale_lock_hours`. To reclaim immediately:

```bash
python -m apm.chatgpt_ui.run_batch --stats   # check state first
```

Then see the recovery snippet in [README_CHATGPT_ITERATE_ABSTRACT.md](README_CHATGPT_ITERATE_ABSTRACT.md).

### Text not appearing in the ChatGPT textarea

`selenium_client.py` uses a two-method fallback:
1. `document.execCommand('insertText')` — fast, works on contenteditable
2. Selenium `send_keys` — universal fallback

If both fail, check that Chrome opened correctly and `chatgpt.com` is accessible.

### ChromeDriver version mismatch

`webdriver-manager` downloads the matching driver automatically.  
If it fails (no internet), download manually from:  
https://googlechromelabs.github.io/chrome-for-testing/  
and replace `apm/browser/chromedriver.exe`.
