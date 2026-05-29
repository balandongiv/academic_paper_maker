# Scopus Automation Tutorial

Step-by-step guide for the two core automation features: **Feature 1** (advanced search + RIS export) and **Feature 2** (cited-by paper download).

---

## Prerequisites

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. One-time Chrome profile setup

The tool drives your real Chrome browser so it can use your existing Scopus institutional login. Create a dedicated Selenium profile:

```bash
mkdir C:\selenium\chrome-profile
```

Then launch Chrome once with that profile to log in to Scopus:

```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --user-data-dir=C:\selenium\chrome-profile ^
  --profile-directory=Default
```

Navigate to [https://www.scopus.com](https://www.scopus.com), log in through your institution, and close the browser.

### 3. Configure the tool

Create (or edit) `scopus_config.json` in the project root. The defaults work if you used the path above:

```json
{
  "chromedriver_path": "browser/chromedriver.exe",
  "chrome_profile_path": "C:\\selenium\\chrome-profile",
  "chrome_profile_name": "Default",
  "output_dir": "output",
  "download_timeout_sec": 120
}
```

Download the matching ChromeDriver from https://chromedriver.chromium.org and place it at `browser/chromedriver.exe`, or install it system-wide and set `"chromedriver_path": "chromedriver"`.

---

## Feature 1 — Advanced Search and RIS Export

Export Scopus search results to a RIS file with a single command.

### Basic usage

```bash
python main.py search --query "TITLE-ABS-KEY(\"machine learning\" AND EEG AND fatigue AND driving) AND PUBYEAR = 2026"
```

The output RIS is saved to `output/search/` with a filename derived from the query. The exact file used in development:

```
output/search/ml_eeg_fatigue_driving_2026.ris
```

### Multiple queries from a file

Create `queries.txt` with one Scopus advanced search query per line:

```
TITLE-ABS-KEY("machine learning" AND EEG AND fatigue AND driving) AND PUBYEAR = 2026
TITLE-ABS-KEY("deep learning" AND EEG AND drowsiness) AND PUBYEAR >= 2024
```

Then run:

```bash
python main.py search --queries-file queries.txt
```

### Custom output directory

```bash
python main.py search --query "..." --output-dir my_results/
```

### What happens during a search

1. Chrome opens Scopus Advanced Search and enters the query.
2. All results are selected.
3. The Export button is clicked, RIS format is chosen.
4. A confirmation modal is handled automatically.
5. The downloaded `.ris` file is moved to the output directory and renamed.

### RIS output format

Each entry in the exported file follows the standard RIS format:

```
TY  - JOUR
AU  - Smith, J.
TI  - Paper Title Here
PY  - 2026
DO  - 10.1016/j.example.2026.001
UR  - https://www.scopus.com/pages/publications/...
ER  -
```

---

## Feature 2 — Cited-By Paper Download

Download all papers that cite a given parent paper, using a CSV of parent paper Scopus URLs.

### Prepare the input CSV

Create a CSV file with a `Link` column containing the Scopus publication URL for each parent paper. The URL must be the full Scopus record URL, for example:

```
Title,Authors,Link
Trust in automation,Jui et al.,https://www.scopus.com/pages/publications/105021869515?origin=resultslist
```

The development fixture used during testing:

```
test_file/jui2026.csv
```

### Run the command

```bash
python main.py cited-by --input test_file/jui2026.csv
```

Output files are saved to `output/cited_by/` by default. Two additional files are written next to the input CSV:

| File | Content |
|------|---------|
| `jui2026_cite_paper.ris` | Combined RIS of all citing papers |
| `jui2026_cite_status.csv` | Per-paper download status |

### Custom output directory

```bash
python main.py cited-by --input jui2026.csv --output-dir results/cited_by/
```

### Re-download already processed papers

By default, papers that already have a downloaded RIS file are skipped. To force re-download:

```bash
python main.py cited-by --input jui2026.csv --force
```

### What happens during cited-by download

For each row in the input CSV:

1. The numeric paper ID is extracted from the Scopus URL  
   (`https://www.scopus.com/pages/publications/105021869515` → `105021869515`)
2. A `REFEID(2-s2.0-105021869515)` advanced search query is built.
3. Feature 1's full pipeline runs the query and exports the citing papers.
4. The downloaded RIS is renamed to `105021869515_cited_by.ris`.
5. Status is saved to the CSV after each paper.

After all papers, all individual RIS files are combined into `{input_stem}_cite_paper.ris`.

### Status CSV columns

| Column | Meaning |
|--------|---------|
| `cited_by_downloaded` | `True` if download succeeded |
| `cited_by_downloaded_at` | ISO timestamp of download |
| `cited_by_ris_file` | Path to the individual RIS file |
| `cited_by_result_count` | Number of citing papers found |
| `cited_by_error` | Error message if download failed |

---

## Feature 3 — Combine and Deduplicate RIS Files

Merge all `.ris` files in a directory into a single deduplicated file.

```bash
python main.py combine-ris --input-dir output/cited_by/ --output output/combined_unique.ris
```

A duplicates report CSV is written alongside the output file.

---

## CLI Reference

```
python main.py --help
python main.py search --help
python main.py cited-by --help
python main.py combine-ris --help
```

### Common options (search and cited-by)

| Option | Default | Description |
|--------|---------|-------------|
| `--config` | `scopus_config.json` | Path to JSON config file |
| `--profile-path` | from config | Chrome user data directory |
| `--profile-name` | from config | Chrome profile name |
| `--chromedriver` | from config | Path to chromedriver.exe |
| `--headless` | off | Run Chrome headlessly |
| `--verbose` / `-v` | off | Enable debug logging |

---

## Running the Tests

### Unit tests (no browser required)

```bash
pytest tests/test_unit_features.py -v
```

These tests run entirely offline against the fixture files in `test_file/`:

- `test_file/ml_eeg_fatigue_driving_2026.ris` — Feature 1 output fixture
- `test_file/jui2026.csv` — Feature 2 input fixture
- `test_file/jui2026_cite_paper.ris` — Feature 2 output fixture
- `test_file/jui2026_cite_status.csv` — Feature 2 status fixture

### End-to-end tests (requires Scopus session)

```bash
pytest -m e2e tests/test_feature_search_export.py -v
pytest -m e2e tests/test_feature_cited_by.py -v
```

---

## Troubleshooting

**Download times out**: Scopus can be slow. Increase `download_timeout_sec` in `scopus_config.json` (default 120 seconds).

**Chrome opens but stays blank**: The Selenium profile may not be logged in. Open Chrome manually with the same `--user-data-dir` and log in to Scopus again.

**"no such element" errors**: Chrome or Scopus UI may have updated. Check the `output/logs/` directory for screenshots taken at key steps.

**Modal not detected**: The export confirmation modal selector is version-dependent. Check `output/logs/` for a screenshot named `export_modal_*.png` showing what Scopus returned.

**"Column 'Link' not found"**: The input CSV must have a column named exactly `Link` (capital L). Use `--link-column` to specify a different name.
