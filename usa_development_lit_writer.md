# Literature Review Writer — Agent Guide

This document explains how to operate the literature-review writing pipeline and identifies the files a future agent should focus on if refactoring is needed.

---

## Overview

The pipeline generates a structured academic literature review from a corpus of pre-screened EEG study JSON files. It uses Selenium to automate ChatGPT (via a persistent Chrome profile) as a writing and auditing agent. Each run produces LaTeX paragraphs, a dataset comparison section, a reference table, and a merged BibTeX file — all written to Google Drive.

---

## How to Run

All commands are run from the project root (`C:\Users\rpb\IdeaProjects\academic_paper_maker`).

### Full run for a theme

```powershell
python -m apm.lit_review.run_pipeline --config setting/lit_review/config_theme_B.yaml
```

### Resume a partial run (skips paragraphs whose `.tex` already exists)

```powershell
python -m apm.lit_review.run_pipeline --config setting/lit_review/config_theme_E.yaml --resume
```

### Filter studies only (no ChatGPT)

```powershell
python -m apm.lit_review.run_pipeline --config setting/lit_review/config_theme_B.yaml --filter-only
```

---

## Config Files

Each theme has its own YAML under `setting/lit_review/`:

| File | Theme |
|---|---|
| `config_theme_B.yaml` | Multiclass Sleepiness Classification |
| `config_theme_C.yaml` | Signal Preprocessing and Artefact Removal |
| `config_theme_D.yaml` | Feature Extraction Methods |
| `config_theme_E.yaml` | Subject-Dependent vs Independent Generalisation |
| `config_theme_F.yaml` | Deep Learning Architectures |
| `config_theme_G.yaml` | Real-Time and Embedded Systems |
| `config_theme_H.yaml` | Hybrid Modality Fusion |
| `config_theme_I.yaml` | Benchmarking and Cross-Study Comparison |
| `config_theme_J.yaml` | Temporal Dynamics and Non-Stationarity |
| `config_theme_K.yaml` | Explainability and Interpretability |
| `config_theme_L.yaml` | Simulation and Naturalistic Driving |
| `config_theme_M.yaml` | Wireless and Wearable EEG |
| `config_theme_P.yaml` | Online Adaptive Learning |

Key YAML fields:

```yaml
project_root: "G:/My Drive/iterate_literature_review"   # Google Drive root
target:
  theme_code: "B"
  theme_name: "..."
  subtheme: ""
selenium:
  wait_seconds: 180    # increase to 300 if ChatGPT is slow
writing:
  max_studies_per_paragraph: 15
  max_paragraph_revisions: 10
  paragraph_definitions:
    - id: "p01_overview"
      title: "..."
      focus: "..."
      keyword_filter: []
```

`wait_seconds: 180` is the safe default for most themes. Use `300` if you see timeouts.

---

## Pipeline Internals

### File map

```
apm/lit_review/
  run_pipeline.py      CLI entry point; parses --config, --resume, --filter-only, --verbose
  pipeline.py          Main orchestration: load studies → write paragraphs → assemble LaTeX
  writer_agent.py      WriterAgent class: Chrome lifecycle, send/check/revise helpers
  aggregator.py        Loads and filters study JSONs from fatigue_eeg_outputs/
  prompt_builder.py    Builds writing, consistency-check, revision, and dataset-comparison prompts
  latex_builder.py     Saves .tex files, assembles section.tex, updates themes_manifest.json, writes main.tex
  bibtex_builder.py    Generates BibTeX entries; _merge_bibtex() merges into references.bib

apm/chatgpt_ui/
  selenium_client.py   Low-level Selenium helpers: build_driver, ensure_logged_in, send_prompt_and_wait
  config.py            SeleniumConfig dataclass

setting/lit_review/
  config_theme_*.yaml  Per-theme pipeline config
```

### Per-paragraph loop (inside `pipeline.py:run_paragraph`)

```
1. select_relevant_for_paragraph()   → pick up to 15 studies
2. build_writing_prompt()            → construct prompt (~87k chars)
3. agent.write_paragraph()           → send to ChatGPT, get raw text
4. for attempt in 1..max_revisions:
     build_consistency_prompt()      → send to ChatGPT as auditor
     detect_pass()                   → read "VERDICT: PASS / FAIL" in first 300 chars
     if PASS → save .tex, break
     build_revision_prompt()         → append auditor prose, re-send to ChatGPT
5. save_paragraph_tex()              → write paragraphs/<pid>.tex
```

### Chrome restart strategy (`writer_agent.py:WriterAgent._restart`)

Before every `send()` call the agent kills Chrome, clears four cache directories (`Cache`, `Code Cache`, `IndexedDB`, `GPUCache`), and relaunches. This prevents DOM accumulation that causes `invalid session id` crashes on long runs.

### Session expiry handling (`selenium_client.py:ensure_logged_in`)

If ChatGPT is not logged in, the pipeline blocks for up to 3 minutes, printing instructions to the Chrome window. Once login is confirmed the run continues uninterrupted.

### Google Drive I/O resilience (`pipeline.py`)

All writes to `G:\My Drive\` are wrapped in `try/except OSError` so a Google Drive sync hiccup does not abort the pipeline. Affected files: `response_writing_<pid>.txt`, `consistency_reports/report_<pid>_attempt<n>.txt`, `response_revision_<pid>_attempt<n>.txt`, and `pipeline_log.md`.

### `--resume` logic

When `--resume` is passed, `run_pipeline()` checks whether `paragraphs/<pid>.tex` exists before calling `run_paragraph()`. If it does, the paragraph is skipped. The dataset comparison is similarly skipped if `dataset_comparison.tex` exists. Use this to recover from a crash without regenerating already-good paragraphs.

---

## Output Layout (Google Drive)

```
G:/My Drive/iterate_literature_review/writing/
  main.tex                            master document (regenerated every run)
  references.bib                      single combined bibliography
  themes_manifest.json                tracks all 13 theme entries
  theme_<code>_<slug>/
    section.tex
    paragraphs/
      p01_overview.tex
      p02_*.tex
      p03_*.tex
      p04_*.tex
      p05_synthesis.tex
    dataset_comparison.tex
    reference_table.tex
    filtered_studies.json
    prompts/
      writing_p01_overview.md
      consistency_p01_overview_attempt1.md
      revision_p01_overview_attempt1.md
      ...
    consistency_reports/
    pipeline_log.md
```

---

## Completed Themes (as of 2026-06-11)

All 13 themes are complete. Each has 5 paragraphs + dataset_comparison written to Google Drive:

B, C, D, E, F, G, H, I, J, K, L, M, P

---

## Refactoring Priorities

If a future agent needs to refactor this pipeline, these are the highest-value targets in order:

### 1. `apm/lit_review/pipeline.py` — coupling and error recovery

- `run_paragraph()` and `run_pipeline()` are long functions that mix I/O, prompt construction, and retry logic. Extract a `_consistency_loop()` helper and a `_save_output()` helper.
- The Google Drive `try/except OSError` blocks are copy-pasted four times. Centralise into a `safe_write(path, text)` utility.
- Empty-response failures (caught as `ValueError("ChatGPT returned an empty response.")`) move on silently. Consider writing a sentinel file so `--resume` can detect that the paragraph needs re-generation rather than just being absent.

### 2. `apm/lit_review/writer_agent.py` — Chrome restart granularity

- `_restart()` is called before every single `send()`, including consistency-check and revision sends for the same paragraph. This is conservative but slow (adds ~12 s per send). Consider restarting only between paragraphs (i.e., once per `run_paragraph()` call) and falling back to per-send restart only after a session error.
- `_kill_chrome_processes()` uses a hard `time.sleep(3)` — replace with a poll on process exit.

### 3. `apm/chatgpt_ui/selenium_client.py` — prompt injection and timing

- `send_prompt_and_wait()` uses a fixed `wait_seconds` timeout with no adaptive backoff. Large prompts (~90k chars) sometimes return in 25 s and sometimes in 55 s. Consider polling the "stop generating" button state rather than sleeping a fixed interval.
- The off-by-one char count (`input box contains 87694 chars, prompt was 87695`) is caused by a trailing newline being trimmed by the textarea. This is harmless but worth documenting or removing.

### 4. `apm/lit_review/prompt_builder.py` — prompt size control

- Writing prompts reach ~90k characters. If ChatGPT context limits tighten, `build_writing_prompt()` will need a truncation strategy. The `max_summary_chars` config field exists but is not enforced in the builder — wire it up.

### 5. `setting/lit_review/config_theme_*.yaml` — deduplication

- All 13 configs repeat the same `selenium`, `input`, `output`, and `writing` blocks. Extract a shared base YAML and use YAML anchors or a two-file scheme (base + override) to avoid drift.

---

## Known Fragile Points

| Issue | Mitigation already in place |
|---|---|
| `invalid session id` Chrome crash mid-paragraph | Per-send Chrome restart; `--resume` skips completed paragraphs |
| Google Drive I/O error during write | All Drive writes wrapped in `try/except OSError` |
| ChatGPT session expiry | `ensure_logged_in()` polls for up to 3 minutes |
| Empty ChatGPT response (prompt too large or rate limit) | Caught as pipeline error; paragraph absent → re-run with `--resume` |
| `pdflatex` not installed | Warning logged, pipeline continues without PDF compilation |
