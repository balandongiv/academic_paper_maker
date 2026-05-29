---

# Academic Paper Maker

A toolkit for automating academic research workflows — from **Scopus literature collection** to **LLM-powered analysis and synthesis**.

---

## What This Project Does

Two complementary automation layers:

**Scopus Automation** — drive your browser to search Scopus, export RIS files, and build cited-by paper sets, with no API key needed (uses your existing institutional login).

**LLM Research Pipeline** — filter, classify, extract methodology, summarize, and export to BibTeX using OpenAI or Gemini agents.

---

## Scopus Automation

> Full walkthrough: [docs/tutorial.md](docs/tutorial.md)

### Features

| Feature | Command | What it does |
|---------|---------|--------------|
| Advanced search + RIS export | `python main.py search` | Run a Scopus advanced query and download results as a `.ris` file |
| Cited-by download | `python main.py cited-by` | For each paper in a CSV, download all papers that cite it |
| Combine + deduplicate | `python main.py combine-ris` | Merge multiple `.ris` files and remove duplicates |

### Quick start

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Set up a Chrome profile with your Scopus login**

```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --user-data-dir=C:\selenium\chrome-profile --profile-directory=Default
```

Log in to Scopus, then close Chrome.

**3. Configure**

Create `scopus_config.json`:

```json
{
  "chrome_profile_path": "C:\\selenium\\chrome-profile",
  "chrome_profile_name": "Default",
  "output_dir": "output"
}
```

**4. Search and export**

```bash
python main.py search --query "TITLE-ABS-KEY(\"machine learning\" AND EEG AND fatigue) AND PUBYEAR = 2026"
```

**5. Download cited-by papers**

```bash
python main.py cited-by --input my_papers.csv
```

The input CSV needs a `Link` column with Scopus publication URLs. Output:
- `my_papers_cite_paper.ris` — combined RIS of all citing papers
- `my_papers_cite_status.csv` — per-paper download status

---

## LLM Research Pipeline

> Powered by OpenAI and Google Gemini.

| Step | Task | Output |
|------|------|--------|
| 5–6 | Filter and classify papers | LLM-augmented relevance scoring |
| 9 | Extract methodology from full text | JSON per paper |
| 10 | Combine JSON and draft summaries | Narrative insights |
| 11 | Export to BibTeX | `.bib` for LaTeX |

---

## Environment Setup

### With Conda

```bash
conda create --name research-tools python=3.12
conda activate research-tools
pip install -r requirements.txt
```

### With Virtualenv

```bash
pip install virtualenv
virtualenv -p python3.12 myenv
# Windows
myenv\Scripts\activate
# macOS/Linux
source myenv/bin/activate
pip install -r requirements.txt
```

---

## Project Structure

```
academic_paper_maker/
├── main.py                        # Scopus automation CLI
├── scopus_automation/             # Automation package
│   ├── search_export.py           # Feature 1: advanced search + RIS export
│   ├── cited_by.py                # Feature 2: cited-by download
│   ├── dedupe.py                  # Feature 3: combine + deduplicate RIS
│   ├── browser.py                 # Chrome driver setup
│   ├── config.py                  # ScopusConfig dataclass
│   ├── login.py                   # Scopus login detection
│   └── ris.py                     # RIS file parsing utilities
├── tests/
│   ├── test_unit_features.py      # Unit tests (no browser required)
│   ├── test_feature_search_export.py  # E2E tests for Feature 1
│   └── test_feature_cited_by.py   # E2E tests for Feature 2
├── test_file/                     # Development fixtures
│   ├── ml_eeg_fatigue_driving_2026.ris
│   ├── jui2026.csv
│   ├── jui2026_cite_paper.ris
│   └── jui2026_cite_status.csv
├── docs/
│   └── tutorial.md                # Step-by-step feature guide
├── scopus_config.json             # Chrome + output configuration
├── execution_guide.ipynb          # LLM pipeline setup and API key guide
├── helper/                        # Utility functions
├── setting/                       # Project path configs
└── requirements.txt
```

---

## Running Tests

```bash
# Unit tests — no browser, no Scopus session needed
pytest tests/test_unit_features.py -v

# End-to-end tests — requires Scopus session
pytest -m e2e tests/ -v
```

---

## API Keys (LLM features only)

To use the LLM pipeline, add your keys to a `.env` file. See `execution_guide.ipynb` for setup instructions.
