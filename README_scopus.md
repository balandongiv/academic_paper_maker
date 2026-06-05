# Scopus Citation & Keyword Search Pipeline

A YAML-driven pipeline that harvests citing papers from Scopus for a set of
parent references, deduplicates against the full Zotero library, and exports
only net-new references to a RIS file ready for direct Zotero import.

---

## Table of Contents

1. [What this pipeline does](#what-this-pipeline-does)
2. [Directory layout](#directory-layout)
3. [One-time setup](#one-time-setup)
4. [Running the pipeline — human approach](#running-the-pipeline--human-approach)
   - [Citation discovery](#a-citation-discovery)
   - [Keyword search](#b-keyword-search)
5. [Running the pipeline — agentic approach](#running-the-pipeline--agentic-approach)
6. [Configuration reference](#configuration-reference)
7. [Output files](#output-files)
8. [Master list schema](#master-list-schema)
9. [Deduplication rules](#deduplication-rules)
10. [Completed run — actual results](#completed-run--actual-results)
11. [Troubleshooting](#troubleshooting)

---

## What this pipeline does

```
get_children_050626.csv         ← parent papers (Zotero CSV export)
        │
        ▼
REFEID(2-s2.0-{scopus_id})      ← Scopus advanced-search query per parent
        │
        ▼
{scopus_id}_cited_by.ris        ← per-parent raw RIS download (Chrome automation)
        │
        ▼
7-rule deduplication            ← DOI > EID > ScopusID > PMID > ISBN >
        │                          title+year > title+author
        ▼
complete_file_available_in_zotero.csv   ← master list (already-in-library check)
        │
        ▼
scopus_children_YYYY-MM-DD_HHMMSS.ris  ← IMPORT THIS INTO ZOTERO
```

**Keyword search** works the same way but the entry point is a list of Scopus
advanced-search queries (e.g. `TITLE-ABS-KEY(...)`) instead of parent paper URLs.

---

## Directory layout

```
academic_paper_maker/
│
├── README_SCOPUS.md                    ← this file
│
├── setting/
│   └── scopus_setup/
│       ├── config_citation_discovery.yaml      ← settings for citation-discovery runs
│       ├── config_keyword_search.yaml          ← settings for keyword-search runs
│       ├── scopus_config.json                  ← Chrome profile path, timeouts (auto-created)
│       └── complete_file_available_in_zotero.csv  ← master list (DO NOT delete)
│
├── get_children_050626.csv             ← input: parent papers (Zotero CSV export)
│
├── apm/
│   ├── browser/
│   │   ├── chromedriver.exe            ← ChromeDriver binary
│   │   └── geckodriver.exe             ← GeckoDriver binary
│   └── scopus/
│       ├── fetch_cited_by_blinkers.py  ← fetch cited-by for all_blinkers.csv
│       ├── fetch_cited_by_latest.py    ← fetch cited-by for latest_blinker.csv
│       └── run_tutorial.py             ← end-to-end tutorial pipeline
│
├── pipeline/                           ← core pipeline package
│   ├── __init__.py
│   ├── api.py                          ← public API (run_pipeline, etc.)
│   ├── citation_discovery.py           ← citation-discovery workflow
│   ├── keyword_search.py               ← keyword-search workflow
│   ├── config.py                       ← YAML → PipelineConfig dataclass
│   ├── models.py                       ← Reference, RunSummary, DeduplicationResult
│   ├── master_list.py                  ← MasterList class (pandas-backed)
│   ├── input_loader.py                 ← load from CSV or Zotero API
│   ├── dedup_engine.py                 ← 7-rule deduplication
│   └── ris_exporter.py                 ← write References to RIS
│
├── scopus_automation/                  ← low-level Scopus browser automation
│   ├── browser.py                      ← Chrome driver builder
│   ├── login.py                        ← Scopus session guard
│   ├── search_export.py                ← advanced search → RIS download
│   ├── cited_by.py                     ← REFEID query → RIS download
│   ├── dedupe.py                       ← RIS-level deduplication helpers
│   ├── ris.py                          ← RIS parser / writer
│   ├── config.py                       ← ScopusConfig dataclass
│   └── logging_setup.py
│
├── tutorial/
│   ├── run_citation_discovery.py       ← MAIN ENTRY POINT (citation discovery)
│   └── run_keyword_search.py           ← MAIN ENTRY POINT (keyword search)
│
└── output/
    └── citation_discovery/
        ├── scopus_children_2026-06-05_124825.ris   ← last export (import into Zotero)
        ├── cited_by_raw/                            ← per-parent raw RIS files (110 files)
        ├── cited_by_per_paper_status.csv
        ├── duplicates_report.csv
        └── run_summary.json
```

---

## One-time setup

### 1. Install Python dependencies

```powershell
pip install -r requirements.txt
```

Key packages used by this pipeline:
`selenium`, `webdriver-manager`, `pandas`, `PyYAML`.
For Zotero API input (optional): `pip install pyzotero`

### 2. Create a dedicated Chrome Selenium profile

This is a **one-time step** that saves your Scopus login cookie so every
subsequent run starts pre-authenticated.

```powershell
# Open a separate Chrome instance using the dedicated Selenium profile
"C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --user-data-dir=C:\selenium\chrome-profile `
    --profile-directory=Default
```

In that Chrome window:
1. Navigate to `https://www.scopus.com`
2. Log in through your institution (e.g. Universiti Malaysia Sabah)
3. Tick **Keep me signed in**
4. Close Chrome

All subsequent pipeline runs reuse this saved session — no manual login required.

> **Important:** `headless: false` is required in `scopus_config.json`.
> Scopus detects and blocks headless Chrome. The browser window will be
> visible during runs — this is normal.

### 3. Verify `scopus_config.json`

Auto-created on first run with these defaults:

```json
{
  "chrome_profile_path": "C:\\Users\\balan\\AppData\\Local\\Google\\Chrome\\User Data",
  "chrome_profile_name": "Default",
  "output_dir": "output",
  "download_timeout_sec": 120,
  "page_load_timeout_sec": 60,
  "element_wait_sec": 30,
  "headless": false
}
```

The Selenium session always uses `C:\selenium\chrome-profile` (hardcoded in
`scopus_automation/browser.py`). Keep `headless: false`.

### 4. Prepare your input CSV

Export a Zotero collection as CSV:

```
Zotero Desktop → right-click collection → Export Collection → Format: CSV
```

Save as e.g. `get_children_050626.csv` in the project root.
Required columns: `Title`, `Url` (Scopus URL containing the paper ID), `DOI`.

---

## Running the pipeline — human approach

### A. Citation discovery

**Finds all papers that cite your parent references.**

#### Step 1 — Edit the config

Open `config_citation_discovery.yaml`:

```yaml
run:
  mode: citation_discovery
  force_rerun: false      # true = re-query already-processed parents

input:
  mode: csv
  csv_path: get_children_050626.csv   # ← your Zotero CSV export

master_list:
  path: complete_file_available_in_zotero.csv
  reuse_existing: true

output:
  directory: output/citation_discovery/
  filename: null            # null = auto-generate timestamp filename
```

**To use Zotero API instead of a CSV file:**

```yaml
input:
  mode: zotero_api
  zotero:
    library_type: user
    library_id: "1234567"          # your Zotero user ID
    api_key: "your_api_key_here"   # from zotero.org/settings/keys
    collection_key: "ABCD1234"
    include_subcollections: true
```

#### Step 2 — Dry run (validates config, no Chrome)

```powershell
python tutorial/run_citation_discovery.py --dry-run
```

Output: loads config, registers all parents in master list, prints which
REFEID queries would be sent, exits without launching Chrome.

#### Step 3 — Full run

```powershell
python tutorial/run_citation_discovery.py
```

Chrome opens automatically. Scopus is queried for each parent.
RIS files are downloaded, deduplicated, and the final export is written.

**Timing:** ~1 minute per parent paper. For 147 parents: ~84 minutes.

#### Step 4 — Resume after interruption

Re-run without `--force`. The pipeline checks which
`output/citation_discovery/cited_by_raw/{scopus_id}_cited_by.ris`
files already exist and skips them automatically.

```powershell
python tutorial/run_citation_discovery.py          # resumes from where it stopped
python tutorial/run_citation_discovery.py --force  # re-downloads everything
```

#### Step 5 — Debug logging

```powershell
python tutorial/run_citation_discovery.py --verbose
```

#### Step 6 — Import into Zotero

```
Zotero Desktop → File → Import
Select: output/citation_discovery/scopus_children_YYYY-MM-DD_HHMMSS.ris
Import into collection: e.g. "cited_by_2026-06"
```

After import, re-export your full Zotero library as CSV and replace
`complete_file_available_in_zotero.csv` so the master list stays current for
the next run.

---

### B. Keyword search

**Searches Scopus by one or more advanced-search query strings.**

#### Step 1 — Edit the config

Open `config_keyword_search.yaml` and define your queries:

```yaml
run:
  mode: keyword_search

keywords:
  - >-
    TITLE-ABS-KEY(
      (eeg OR electroencephalogra*)
      AND ("driver fatigue" OR "driver drowsiness")
      AND (driving OR driver*)
    ) AND PUBYEAR = 2026
  - TITLE-ABS-KEY("eye blink" AND eeg AND artifact) AND PUBYEAR > 2022

master_list:
  path: complete_file_available_in_zotero.csv
  reuse_existing: true

output:
  directory: output/keyword_search/
```

#### Step 2 — Dry run

```powershell
python tutorial/run_keyword_search.py --dry-run
```

#### Step 3 — Full run

```powershell
python tutorial/run_keyword_search.py
```

#### Step 4 — Import into Zotero

```
Zotero Desktop → File → Import
Select: output/keyword_search/scopus_export_YYYY-MM-DD_HHMMSS.ris
```

---

## Running the pipeline — agentic approach

You can delegate the entire pipeline to Claude Code (or any Claude-based agent).
Copy one of the prompts below into your Claude Code session.

---

### Prompt A — Citation discovery from a CSV file

```
I want to run the Scopus citation discovery pipeline on the file
`get_children_050626.csv` (already in the project root of academic_paper_maker/).

The pipeline entry point is `tutorial/run_citation_discovery.py`.
The config file is `config_citation_discovery.yaml`.

Please:
1. Verify `config_citation_discovery.yaml` has `input.csv_path` pointing to
   `get_children_050626.csv` and `master_list.path` pointing to
   `complete_file_available_in_zotero.csv`.
2. Run the dry run and confirm the correct number of parent references loads:
       python tutorial/run_citation_discovery.py --dry-run
3. Run the full pipeline in the background and monitor it:
       python tutorial/run_citation_discovery.py
   Report progress every ~20 minutes (how many RIS files are in
   output/citation_discovery/cited_by_raw/).
4. When complete, report:
   - How many parents were processed
   - Total Scopus citing papers found
   - Duplicates removed
   - Net-new references exported
   - Exact path of the RIS file to import into Zotero
   - Any errors from run_summary.json
5. Show the top 5 parents by number of citing papers from
   cited_by_per_paper_status.csv.

Note: Chrome opens visibly — this is required. Do not kill it.
The run takes ~1 min/paper. For 147 parents expect ~85 minutes.
```

---

### Prompt B — Keyword search

```
I want to run a Scopus keyword search using the pipeline in academic_paper_maker/.

The entry point is `tutorial/run_keyword_search.py`.
The config file is `config_keyword_search.yaml`.

Please:
1. Open `config_keyword_search.yaml` and replace the `keywords:` list with these
   Scopus advanced-search queries:
   [INSERT YOUR QUERIES HERE]

2. Run the dry run to validate:
       python tutorial/run_keyword_search.py --dry-run

3. Run the full pipeline:
       python tutorial/run_keyword_search.py

4. When complete, report:
   - Total Scopus results per keyword
   - Total duplicates removed (already in Zotero library)
   - Net-new references exported
   - Path to the RIS file for Zotero import
   - Any errors from output/keyword_search/run_summary.json

Note: Chrome opens visibly — this is required. Scopus blocks headless Chrome.
```

---

### Prompt C — Process a brand-new Zotero collection end-to-end

```
I have exported a new Zotero collection to `[YOUR_CSV_FILENAME].csv`
in the project root of academic_paper_maker/.

Please run the full Scopus citation discovery pipeline end-to-end:

1. Update `config_citation_discovery.yaml`:
   - Set `input.csv_path` to `[YOUR_CSV_FILENAME].csv`
   - Keep `run.force_rerun: false` (resume mode)
   - Confirm `master_list.path` is `complete_file_available_in_zotero.csv`
   - Confirm `output.directory` is `output/citation_discovery/`

2. Run the dry run and confirm the reference count looks right:
       python tutorial/run_citation_discovery.py --dry-run

3. Run the full pipeline, monitor it in the background, and report progress
   every 20 minutes:
       python tutorial/run_citation_discovery.py

4. When complete, provide:
   - The final run_summary.json numbers
   - The path to the RIS file to import into Zotero
   - Any errors or warnings

5. Remind me to re-export my Zotero library as CSV and replace
   `complete_file_available_in_zotero.csv` after I import the RIS file,
   so the master list stays current for the next run.
```

---

### Prompt D — Check status of a completed (or running) pipeline

```
Check the status of the most recent Scopus pipeline run in academic_paper_maker/.

1. Read `output/citation_discovery/run_summary.json` and show all fields.

2. Count RIS files in `output/citation_discovery/cited_by_raw/` to confirm
   how many parent papers were downloaded.

3. Show the top 10 parent papers by citing-paper count from
   `output/citation_discovery/cited_by_per_paper_status.csv`.

4. Show the current master list row count broken down by `reference_role`
   (parent vs. child) from `complete_file_available_in_zotero.csv`.

5. Confirm the output RIS file exists, show its path and size.

6. If the pipeline is still running, estimate time to completion based on
   current RIS file count vs. total parents.
```

---

### Prompt E — Retry failed / timed-out parents

```
Some parent papers in the last citation discovery run had errors or 0 results.
I want to retry only those.

Please:
1. Read `output/citation_discovery/cited_by_per_paper_status.csv` and list all
   rows where status != "ok" or result_count is 0.

2. For each such paper, check whether its `{scopus_id}_cited_by.ris` file exists
   in `output/citation_discovery/cited_by_raw/`. If it does and is empty or
   0 bytes, delete it.

3. Run with --force so the pipeline re-queries all parents (those with existing
   valid RIS files are still resumed automatically via the skip check):
       python tutorial/run_citation_discovery.py --force

4. Report the updated results when it completes.
```

---

### Prompt F — Update master list after Zotero import

```
I have just imported the RIS file into Zotero and re-exported my library
as a new CSV file called `[NEW_EXPORT_FILENAME].csv`.

Please update the master list:
1. Replace `complete_file_available_in_zotero.csv` with the new export by
   copying `[NEW_EXPORT_FILENAME].csv` to `complete_file_available_in_zotero.csv`.
2. Run a dry run to confirm the new master list loads correctly:
       python tutorial/run_citation_discovery.py --dry-run
3. Report the new row count and fingerprint count from the master list.
4. Confirm the pipeline is ready for the next batch.
```

---

## Configuration reference

### `config_citation_discovery.yaml` — full schema

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `run.mode` | string | `citation_discovery` | Workflow to run |
| `run.force_rerun` | bool | `false` | Re-query already-processed parents |
| `run.output_filename` | string\|null | `null` | Fixed RIS filename; null = auto timestamp |
| `input.mode` | string | `csv` | `csv` or `zotero_api` |
| `input.csv_path` | string | — | Path to Zotero CSV export |
| `input.zotero.library_type` | string | `user` | `user` or `group` |
| `input.zotero.library_id` | string | — | Zotero user/group ID |
| `input.zotero.api_key` | string | — | Zotero API key |
| `input.zotero.collection_key` | string | — | Zotero collection key |
| `input.zotero.include_subcollections` | bool | `false` | Include child collections |
| `zotero.deduplicate_against_master_list` | bool | `true` | Enable master list dedup |
| `zotero.export_format` | string | `ris` | Export format (only `ris` supported) |
| `master_list.path` | string | `complete_file_available_in_zotero.csv` | Master list CSV |
| `master_list.reuse_existing` | bool | `true` | Load existing master list |
| `output.directory` | string | `output/citation_discovery/` | Output folder |
| `output.filename` | string\|null | `null` | Fixed output filename |
| `scopus_config_path` | string | `scopus_config.json` | Chrome / timeout settings |

### `config_keyword_search.yaml` — additional key

| Key | Type | Description |
|-----|------|-------------|
| `keywords` | list of strings | Scopus advanced-search queries (one per item) |

---

## Output files

### Citation discovery

| File | Description |
|------|-------------|
| `output/citation_discovery/scopus_children_YYYY-MM-DD_HHMMSS.ris` | **Import into Zotero** |
| `output/citation_discovery/cited_by_raw/{scopus_id}_cited_by.ris` | Raw per-parent downloads |
| `output/citation_discovery/cited_by_per_paper_status.csv` | Per-parent: status, result_count, errors |
| `output/citation_discovery/duplicates_report.csv` | Which papers were removed and which dedup rule matched |
| `output/citation_discovery/run_summary.json` | Machine-readable run statistics |
| `complete_file_available_in_zotero.csv` | Updated master list |

### Keyword search

| File | Description |
|------|-------------|
| `output/keyword_search/scopus_export_YYYY-MM-DD_HHMMSS.ris` | **Import into Zotero** |
| `output/keyword_search/keyword_raw/{query_slug}.ris` | Raw per-keyword downloads |
| `output/keyword_search/keyword_search_status.csv` | Per-keyword result counts and errors |
| `output/keyword_search/keyword_duplicates_report.csv` | Duplicates removed |
| `output/keyword_search/run_summary.json` | Machine-readable run statistics |

### `run_summary.json` structure

```json
{
  "run_id": "11e74a24",
  "run_mode": "citation_discovery",
  "started_at": "2026-06-05T11:24:33",
  "completed_at": "2026-06-05T12:48:26",
  "total_parent_references": 147,
  "parents_skipped_already_processed": 0,
  "parents_processed": 147,
  "total_scopus_results": 2035,
  "duplicates_detected": 1931,
  "new_references_exported": 195,
  "ris_output_path": "output/citation_discovery/scopus_children_2026-06-05_124825.ris",
  "master_list_path": "complete_file_available_in_zotero.csv",
  "errors": [],
  "warnings": ["Parent EXMLDRXM has no Scopus URL — skipping."]
}
```

---

## Master list schema

`complete_file_available_in_zotero.csv` is the deduplication memory of the
entire pipeline. It combines original Zotero CSV columns with tracking columns
added by the pipeline. **Do not delete or rename this file.**

Current state: **1,756 rows** — 147 parents + 195 net-new children + 1,414 original Zotero library entries.

### Tracking columns added by the pipeline

| Column | Type | Description |
|--------|------|-------------|
| `record_id` | string | Unique ID (Zotero key, or UUID if none) |
| `reference_role` | string | `parent` or `child` |
| `scopus_eid` | string | Scopus EID, e.g. `2-s2.0-85111561189` |
| `scopus_id` | string | Numeric part, e.g. `85111561189` |
| `pmid` | string | PubMed ID (parsed from Zotero `Extra` field) |
| `source_input_file` | string | CSV file this reference was loaded from |
| `source_input_mode` | string | `csv`, `zotero_api`, or `scopus_ris` |
| `parent_record_id` | string | record_id of the parent (children only) |
| `parent_doi` | string | DOI of the parent paper (children only) |
| `parent_scopus_eid` | string | EID of the parent paper (children only) |
| `parent_title` | string | Title of the parent paper (children only) |
| `query` | string | The Scopus query that found this reference |
| `query_keyword` | string | The keyword used (keyword-search mode) |
| `has_been_processed_for_children` | bool | True after REFEID query has run for this parent |
| `children_last_run_at` | datetime | Timestamp of last citation query |
| `children_result_count` | int | Total Scopus hits from last query |
| `children_exported_count` | int | Net-new children exported to RIS |
| `already_in_zotero` | bool | True if loaded from a Zotero CSV export |
| `already_exported` | bool | True after reference appears in an output RIS |
| `result_count` | int | Scopus result count for this record |

---

## Deduplication rules

A child/search result is skipped if it matches any rule below, checked in
priority order. The matching rule is recorded in `duplicates_report.csv`.

| Priority | Rule | Field(s) checked |
|----------|------|-----------------|
| 1 | DOI exact match | `DOI` column (URL prefix stripped, lowercased) |
| 2 | Scopus EID match | `scopus_eid` tracking column |
| 3 | Scopus numeric ID match | `scopus_id` tracking column |
| 4 | PMID match | `pmid` tracking column |
| 5 | ISBN match | `ISBN` column (hyphens/spaces removed) |
| 6 | Normalised title + year | `Title` + `Publication Year` |
| 7 | Normalised title + first author last name | `Title` + `Author` |

Normalisation: lowercase → strip punctuation → collapse whitespace.

Within a single run, cross-parent and cross-keyword duplicates are also caught
so each paper is exported at most once per run.

---

## Completed run — actual results

Run executed **2026-06-05**, input: `get_children_050626.csv` (147 parents).

| Metric | Value |
|--------|-------|
| Parents with Scopus URL | 143 |
| Parents skipped (no URL) | 4 |
| Parents with ≥1 citing paper | 107 |
| Parents with 0 citing papers | 36 |
| Total Scopus citing papers found | **2,035** |
| Already in Zotero library (removed) | **1,931** |
| **Net-new exported to RIS** | **195** |
| Run duration | 84 minutes (11:24 → 12:48) |
| Output RIS | `output/citation_discovery/scopus_children_2026-06-05_124825.ris` |
| Master list size after run | **1,756 rows** |

### Top 5 parents by citing-paper count

| Paper | Citing papers |
|-------|--------------|
| Real-time classification for autonomous drowsiness detection | 173 |
| Automatic Eyeblink and Muscular Artifact Detection and Removal | 97 |
| Adjusting eye aspect ratio for strong eye blink detection | 89 |
| VME-DWT: An Efficient Algorithm for Detection and Elimination | 84 |
| Driver fatigue detection method based on eye states with pupil | 80 |

---

## Troubleshooting

### Chrome opens but search form not found

The Scopus session has expired. Re-authenticate:

```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --user-data-dir=C:\selenium\chrome-profile `
    --profile-directory=Default
```

Navigate to Scopus, log in, close Chrome. Then re-run the pipeline.

### Chrome fails to start ("session not created: Chrome instance exited")

A stale lock file from a previous interrupted run is blocking Chrome:

```powershell
# Kill any orphaned Chrome processes first
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue

# Then re-run normally
python tutorial/run_citation_discovery.py
```

### Download timed out

Scopus is slow. Increase `download_timeout_sec` in `scopus_config.json`
(default: 120 seconds). Try 180 or 240.

### `status: error` with `result_count: 0` in per-paper status CSV

This means Scopus returned no results for that REFEID query — the paper simply
has no citing papers yet (common for very recent publications). This is not a
crash. Re-running will retry these papers but the result will be the same.

### All results are duplicates — `new_references_exported: 0`

The master list (`complete_file_available_in_zotero.csv`) already contains
these papers. This is correct behaviour if you have a comprehensive Zotero library.
After importing the RIS into Zotero and re-exporting the library, re-run to check
for genuinely new papers.

### Two runs conflict / Chrome profile locked

Never run two instances simultaneously. They share `C:\selenium\chrome-profile`
and will deadlock. Kill all Chrome processes and start fresh:

```powershell
Stop-Process -Name chrome -Force -ErrorAction SilentlyContinue
python tutorial/run_citation_discovery.py
```

### After Zotero import, the next run still exports the same papers

You must re-export your full Zotero library as CSV and replace
`setting/scopus_setup/complete_file_available_in_zotero.csv` before the next run.
The pipeline only deduplicates against the snapshot that was in place when the
file was last updated.

---

## Running tests

### Unit tests (no browser required — runs offline)
```powershell
pytest tests/test_ris_parser.py tests/test_combine_ris.py tests/test_unit_features.py -v
```

### End-to-end tests (require active Scopus browser session)
```powershell
pytest -m e2e tests/test_feature_search_export.py tests/test_feature_cited_by.py -v
```

Fixture files used by unit tests live in `test_file/`.

---

## Programmatic API

```python
from pipeline import run_pipeline, load_config
from pipeline.master_list import MasterList
from pipeline.input_loader import load_references_from_csv

# One-liner: run everything from a config file
summary = run_pipeline("config_citation_discovery.yaml")
print(f"Exported {summary.new_references_exported} new refs → {summary.ris_output_path}")

# Step-by-step access
cfg = load_config("config_citation_discovery.yaml")
ml  = MasterList.load("complete_file_available_in_zotero.csv")
parents = load_references_from_csv("get_children_050626.csv")
print(f"{len(parents)} parents, {ml.row_count} rows in master list")

# Dry run (no Chrome)
summary = run_pipeline("config_citation_discovery.yaml", dry_run=True)
```

All public API functions:

| Function | Description |
|----------|-------------|
| `run_pipeline(config_path, dry_run)` | Run full workflow from YAML config |
| `load_config(config_path)` | Load `PipelineConfig` from YAML |
| `load_references_from_csv(csv_path)` | Load parents from Zotero CSV |
| `load_references_from_zotero(config)` | Load parents from Zotero API |
| `get_scopus_citing_children(parent, driver, cfg, output_dir)` | Download citing papers for one parent |
| `search_scopus_by_keyword(keyword, driver, cfg, output_dir)` | Run one keyword search |
| `load_master_list(path)` | Load `MasterList` from CSV |
| `update_master_list(master_list, records)` | Add/update records and save |
| `deduplicate_references(references, master_list)` | 7-rule deduplication |
| `export_to_ris(references, output_path)` | Write `Reference` list to RIS file |
