# Scopus Automation

Automates Scopus search, RIS export, cited-by download, and deduplication using your existing Chrome login session.

---

## Requirements

```bash
pip install -r requirements.txt
```

Key packages: `selenium`, `rispy`, `click`, `pandas`, `openpyxl`, `pytest`, `pytest-timeout`

---

## 1. Chrome Profile Setup (Session Reuse)

The tool reuses your existing Chrome login so you do **not** need to log in again programmatically.

**Step 1 — Log into Scopus in Chrome** (your normal browser, not through this tool).

**Step 2 — Find your Chrome profile path:**

| OS      | Default path |
|---------|-------------|
| Windows | `C:\Users\<YOU>\AppData\Local\Google\Chrome\User Data` |
| macOS   | `~/Library/Application Support/Google/Chrome` |
| Linux   | `~/.config/google-chrome` |

**Step 3 — Set the path in `scopus_config.json`:**

```json
{
  "chrome_profile_path": "C:\\Users\\balan\\AppData\\Local\\Google\\Chrome\\User Data",
  "chrome_profile_name": "Default",
  "chromedriver_path": "browser\\chromedriver.exe"
}
```

Or pass on the CLI:

```bash
python main.py search --query "..." --profile-path "C:\Users\balan\AppData\Local\Google\Chrome\User Data"
```

> **Important:** Close Chrome before running the tool, because only one process can use a Chrome profile at a time.

---

## 2. Verify Scopus Login

When the tool starts it opens `https://www.scopus.com/sources#` and checks for an authenticated session. If not logged in, it opens the browser and waits for you to log in manually, then continues automatically.

---

## 3. Feature 1 — Search and Export RIS

### Single query

```bash
python main.py search --query "TITLE-ABS-KEY(\"machine learning\" AND EEG AND fatigue AND driving) AND PUBYEAR = 2026"
```

### Multiple queries from a file

```bash
python main.py search --queries-file input/queries.txt --output-dir output/search
```

`input/queries.txt` format — one query per line, `#` for comments:

```text
# EEG fatigue 2026
TITLE-ABS-KEY("machine learning" AND EEG AND fatigue AND driving) AND PUBYEAR = 2026
```

**Output files:**

| File | Description |
|------|-------------|
| `output/search/<query_slug>.ris` | Exported RIS file |
| `output/search_results_index.csv` | Index of all exports |
| `output/logs/scopus_automation_YYYYMMDD_HHMMSS.log` | Run log |

---

## 4. Feature 2 — Cited-By Papers

Download the papers that cite each parent paper listed in a CSV or Excel file.

### Input format

The file must have a `Link` column with Scopus paper URLs:

```
https://www.scopus.com/pages/publications/105021869515?origin=resultslist
```

### Command

```bash
python main.py cited-by --input test_file/jui2026.csv --output-dir output/cited_by
```

Force re-download of already processed papers:

```bash
python main.py cited-by --input test_file/jui2026.csv --force
```

**Output files:**

| File | Description |
|------|-------------|
| `output/cited_by/<id>_cited_by.ris` | Cited-by RIS per parent paper |
| `output/jui2026_with_cited_by_status.csv` | Status enrichment of input file |

Status columns added to the CSV:

```
cited_by_downloaded, cited_by_downloaded_at, cited_by_ris_file, cited_by_result_count, cited_by_error
```

---

## 5. Feature 3 — Combine RIS and Remove Duplicates

```bash
python main.py combine-ris --input-dir output --output output/combined/combined_unique.ris
```

**Deduplication priority:**

1. DOI (normalised, case-insensitive)
2. Scopus EID (`2-s2.0-...`)
3. Normalised title + publication year

**Output files:**

| File | Description |
|------|-------------|
| `output/combined/combined_unique.ris` | Merged, deduplicated RIS |
| `output/combined/duplicates_report.csv` | Details of removed duplicates |

---

## 6. Running Tests

### Unit tests (no login required)

```bash
pytest
```

### End-to-end tests (requires Scopus session)

```bash
pytest -m e2e
```

Run a specific e2e test:

```bash
pytest -m e2e tests/test_feature_search_export.py -v
```

---

## 7. Handling Expired Sessions

If your Scopus session expires mid-run:

1. The tool detects the login redirect.
2. It opens the Scopus login page in the browser.
3. Log in manually in the opened browser window.
4. The tool resumes automatically once login is detected.

To avoid this: ensure you are logged into Scopus in Chrome before starting.

---

## 8. Output File Locations

| Feature | Default output |
|---------|---------------|
| Search RIS | `output/search/` |
| Cited-by RIS | `output/cited_by/` |
| Combined RIS | `output/combined/` |
| Logs | `output/logs/` |

Override with `--output-dir` on any command.

---

## 9. All CLI Options

```
python main.py --help
python main.py search --help
python main.py cited-by --help
python main.py combine-ris --help
```

Global options:

```
--verbose / -v      Enable DEBUG logging
```

Per-command options:

```
--profile-path      Chrome user data directory
--profile-name      Chrome profile name (default: Default)
--chromedriver      Path to chromedriver.exe
--config            JSON config file path (default: scopus_config.json)
--headless          Run Chrome headlessly (not recommended for Scopus)
```

---

## 10. Known Limitations

- **Scopus UI changes:** Selectors are based on the 2024/2025 Scopus interface. If Scopus updates its UI, some selectors may need adjustment in `scopus_automation/search_export.py` and `cited_by.py`.
- **Profile lock:** Only one Chrome instance can use a profile at a time. Close your regular Chrome before running.
- **Rate limiting:** The tool runs one operation at a time with conservative waits. Do not modify it to run parallel requests.
- **Export limits:** Scopus limits RIS exports (typically 2000 records per export). Very large result sets may require pagination.
- **Login:** Institutional SSO and CAPTCHA must be handled by the user. The tool waits for manual login completion.
- **Download directory:** The browser must write downloads to `output/search/` or `output/cited_by/`. Ensure these paths are writable.
