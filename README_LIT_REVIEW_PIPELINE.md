# Literature-Review Writing Pipeline

Automated pipeline that filters EEG fatigue studies, writes academic paragraphs through the ChatGPT UI (Selenium), runs iterative evidence consistency checking, performs section-level critique and repair (up to 20 cycles), and finishes with a global narrative flow audit across all completed sections.

---

## 1. Core agent names and roles

The pipeline uses several conceptual agents. All writing-related agents must be executed through the ChatGPT UI agent driver, using Selenium or an equivalent browser automation implementation similar to `chatgpt_ui`.

### 1.1 Academic Synthesis Agent

**Role:** Generate academic literature-review paragraphs.

The Academic Synthesis Agent writes critical, evidence-grounded academic prose using only the selected study summaries extracted from `chatgpt_response`. It must follow the writing style and rhetorical guidance in `writing_technique.MD`.

This agent is responsible for:

- writing each paragraph as a separate LaTeX file;
- synthesising studies rather than merely listing them;
- comparing and contrasting findings across studies;
- discussing methodological strengths and weaknesses;
- maintaining a coherent argumentative flow;
- using only evidence traceable to the selected input summaries;
- inserting citation keys in the required format: `\cite{author_year_hash}`;
- receiving every field of every selected study in full — **no field may be truncated or omitted when building the writing prompt**. All information extracted from `chatgpt_response` is evidence. Truncating it is equivalent to destroying evidence before the agent can use it.

### 1.2 Evidence Consistency Auditor

**Role:** Check every generated paragraph against the full study evidence, including verbatim abstracts.

The Evidence Consistency Auditor uses the same ChatGPT UI agent driver, but with a dedicated consistency-checking prompt. It verifies whether each paragraph remains faithful to the complete study evidence: the extracted `chatgpt_response` fields **and** the verbatim abstract from `source_row["Abstract Note"]`.

This agent is responsible for checking:

- whether every factual claim is supported by the verbatim abstract or the extracted evidence fields;
- whether cited papers actually support the claims attached to them;
- whether any study has been misrepresented relative to what its abstract states;
- whether performance numbers (accuracy, sensitivity, specificity, AUC, F1) are correctly reported and match the abstract;
- whether electrode or channel claims are accurate relative to the abstract;
- whether any unsupported generalisation has been introduced;
- whether the paragraph remains aligned with the target theme and subtheme;
- whether the paragraph maintains an academic and critical tone.

No paragraph may be accepted unless the Evidence Consistency Auditor returns a clear **PASS**. If the audit returns **FAIL**, the paragraph is sent back to the Academic Synthesis Agent with the specific issues listed. This loop repeats until the paragraph passes or a configurable maximum revision limit is reached (default: 5 attempts per paragraph).

The consistency-check prompt must supply the auditor with the same complete study blocks given to the Academic Synthesis Agent — verbatim abstracts included, with no truncation. An auditor that checks a paragraph against incomplete or truncated evidence cannot catch misrepresentations in the omitted content.

### 1.3 Section Critique Agent

**Role:** Critique a completed section after all paragraph-level consistency checks have passed.

The Section Critique Agent reviews the assembled section or theme after all paragraph files in that section have passed evidence consistency checking. Its goal is not only to detect factual errors, but to improve the academic quality of the section as a whole.

This agent is responsible for identifying:

- weak argumentative flow;
- missing transitions between paragraphs;
- shallow critique or excessive reporting;
- redundant content;
- missing comparison across studies;
- weak explanation of methodological trade-offs;
- missing links between datasets, EEG channels, models, and validation choices;
- opportunities to improve the reference-summary table;
- areas where the section does not yet tell a coherent scholarly story.

The Section Critique Agent produces a structured critique and a repair plan. The repair plan is then sent back to the Academic Synthesis Agent, which revises the affected paragraphs. Each revised paragraph must pass the Evidence Consistency Auditor again before being accepted. This critique-and-repair cycle repeats until the Section Critique Agent reports no remaining issues, or until 20 cycles have been completed.

### 1.4 Global Narrative Flow Auditor

**Role:** Check the flow of the entire literature review after all sections are completed.

The Global Narrative Flow Auditor reviews the complete assembled literature review. It checks whether the full document has a coherent progression across sections and whether the overall story of fatigue-driving EEG research from 2017 to 2026 is clear.

This agent is responsible for checking:

- whether the ordering of sections is logical;
- whether transitions between sections are smooth;
- whether the literature review has a clear beginning, development, and conclusion;
- whether concepts are introduced before they are used;
- whether there are contradictions across sections;
- whether the same study is described inconsistently in different places;
- whether themes are balanced and not unnecessarily repetitive;
- whether the dataset-comparison section is properly connected to the rest of the review.

Feedback from the Global Narrative Flow Auditor must be used to repair the affected sections. Any repaired paragraph must be sent back through the Evidence Consistency Auditor before being accepted.

---

## 2. Pipeline overview

```
fatigue_eeg_outputs/*.json          ← study analysis JSON files (one per paper)
setting/lit_review/config.yaml      ← pipeline configuration
         │
         ▼  filter by theme + subtheme
filtered_studies.json
         │
         ▼  for each paragraph definition
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │  PARAGRAPH LOOP                                             │
         │  │                                                             │
         │  │  Academic Synthesis Agent writes paragraph                  │
         │  │        │                                                    │
         │  │        ▼                                                    │
         │  │  Evidence Consistency Auditor checks                        │
         │  │        │                                                    │
         │  │      PASS? ──no──▶ Academic Synthesis Agent revises        │
         │  │        │           (repeat until PASS or max 5 attempts)   │
         │  │      yes                                                    │
         │  │        ▼                                                    │
         │  │  Save paragraph .tex                                        │
         │  └─────────────────────────────────────────────────────────────┘
         │
         ▼  all paragraphs in section have PASSED
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │  SECTION CRITIQUE LOOP  (max 20 cycles)                    │
         │  │                                                             │
         │  │  Section Critique Agent reviews assembled section           │
         │  │        │                                                    │
         │  │  No issues? ──yes──▶ exit loop                             │
         │  │        │                                                    │
         │  │  Issues found ──▶ Academic Synthesis Agent repairs          │
         │  │        │          affected paragraphs                       │
         │  │        ▼                                                    │
         │  │  Evidence Consistency Auditor re-checks each repaired para  │
         │  │        │                                                    │
         │  │  All pass ──▶ next critique cycle                          │
         │  └─────────────────────────────────────────────────────────────┘
         │
         ▼  all sections completed
         │
         │  ┌─────────────────────────────────────────────────────────────┐
         │  │  GLOBAL NARRATIVE FLOW AUDIT                                │
         │  │                                                             │
         │  │  Global Narrative Flow Auditor reviews full document        │
         │  │        │                                                    │
         │  │  Issues found ──▶ repair affected paragraphs               │
         │  │                   re-check each with Evidence Auditor      │
         │  └─────────────────────────────────────────────────────────────┘
         │
         ▼
writing/
  main.tex                          ← master LaTeX (all sections)
  references.bib                    ← single combined bibliography
  themes_manifest.json              ← registry of completed theme runs
  main.pdf
  theme_A_single_channel/
    section.tex                     ← \subsection + \input paragraphs/*
    paragraphs/
      p01_overview.tex
      p02_electrode_sites.tex
      ...
    dataset_comparison.tex
    reference_table.tex
    prompts/                        ← all prompts saved for QC
    consistency_reports/            ← Evidence Auditor outputs per paragraph
    section_critique_reports/       ← Section Critique Agent outputs
    filtered_studies.json
    pipeline_log.md
```

---

## 3. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | Anaconda recommended |
| Google Chrome | Must be installed |
| `selenium`, `webdriver-manager`, `pyyaml` | `pip install selenium webdriver-manager pyyaml` |
| Selenium Chrome profile logged into ChatGPT | See first-time setup below |
| Study JSON files | In `fatigue_eeg_outputs/` folder on Google Drive |
| `pdflatex` (optional) | For PDF compilation; install MiKTeX or TeX Live |

---

## 4. First-time setup — log in to ChatGPT

Run any existing Selenium script once to open the dedicated Chrome profile and log in manually. The session is saved and all future runs skip the login.

```powershell
python tutorial/run_chatgpt_prompt.py
# Chrome opens → log in → press Enter in terminal
```

---

## 5. Configuration — `setting/lit_review/config.yaml`

```yaml
project_root: "C:/Users/balan/My Drive (balandong@ums.edu.my)/iterate_literature_review"

input:
  fatigue_eeg_outputs_folder: "fatigue_eeg_outputs"
  candidates_csv: "candidates_eeg_fatigue_driver.csv"
  writing_technique_file: "writing_technique.MD"
  literature_review_theme_file: "literature_review_theme.md"

output:
  writing_folder: "writing"

target:
  theme_code: "A"
  theme_name: "Limited Number of EEG Electrodes"
  subtheme: "single-channel EEG"

selenium:
  headless: false
  wait_seconds: 300
  chrome_exe: "C:/Users/balan/AppData/Local/Google/Chrome/Application/chrome.exe"
  chrome_profile: "C:/selenium/chrome-profile"

writing:
  max_studies_per_paragraph: 50
  # max_summary_chars is intentionally absent.
  # All study fields must be passed to ChatGPT in full.
  # Do NOT add a character-limit truncation here.
  max_paragraph_revisions: 10         # max Evidence Auditor → revise cycles per paragraph
  max_section_critique_cycles: 20    # max Section Critique loops per section

  paragraph_definitions:
    - id: "p01_overview"
      title: "Overview and Motivation"
      focus: >
        Write a paragraph introducing ...
      keyword_filter: []

    - id: "p02_electrode_sites"
      title: "Electrode Site Selection"
      focus: >
        Write a paragraph critically analysing ...
      keyword_filter: ["frontal", "Fz", "Oz"]
```

### Key settings

| Setting | When to change |
|---|---|
| `theme_code` | For a different main theme (B, C, D, …) |
| `subtheme` | For a different subtheme within that theme |
| `paragraph_definitions` | To add, remove, or reword paragraphs |
| `max_paragraph_revisions` | Revision cap per paragraph (Evidence Auditor loop) |
| `max_section_critique_cycles` | Section Critique loop cap (default 20) |
| `max_studies_per_paragraph` | Increase if ChatGPT context allows |
| `chrome_profile` | Must match the profile where ChatGPT login is saved |

> **Do not add `max_summary_chars` or any per-field character limit.** Study data must be passed to every agent prompt in full. Truncation silently degrades evidence quality and causes the Evidence Consistency Auditor to miss misrepresentations.

---

## 6. Running the pipeline

All commands are run from the project root (`C:\Users\balan\IdeaProjects\academic_paper_maker`).

### Step 1 — Dry run: check study selection

```powershell
python -m apm.lit_review.run_pipeline --filter-only
```

Prints the count of matched studies and saves `filtered_studies.json`. No ChatGPT calls are made.

### Step 2 — Full run

```powershell
python -m apm.lit_review.run_pipeline
```

Chrome opens automatically. The pipeline:
1. Writes each paragraph via the Academic Synthesis Agent.
2. Audits each paragraph with the Evidence Consistency Auditor; revises and re-audits until it passes or the revision cap is reached.
3. After all paragraphs pass, enters the Section Critique loop (up to 20 cycles).
4. After all sections are complete, runs the Global Narrative Flow Auditor.
5. Assembles `section.tex`, updates `main.tex` and `references.bib`, compiles `main.pdf`.

Expect ~5–8 minutes per paragraph (write + audit), plus additional time for section critique cycles.

### Step 3 — Verbose logging

```powershell
python -m apm.lit_review.run_pipeline --verbose
```

### Step 4 — Custom config

```powershell
python -m apm.lit_review.run_pipeline --config setting/lit_review/config_theme_B.yaml
```

### Step 5 — Regenerate references.bib only

```powershell
python -m apm.lit_review.regenerate_bib
```

Scans all theme subfolders under `writing/` for `filtered_studies.json` files, merges all studies, and overwrites `writing/references.bib`. Useful if the pipeline was run before the single-bib structure was introduced.

---

## 7. Paragraph-level consistency loop (Evidence Consistency Auditor)

For each paragraph, the pipeline runs the following loop:

```
1. Build writing prompt.
   RULE: Include every field of every selected study with no truncation.
   Each study block must contain:
     - Bibliographic metadata: title, authors, year, journal, DOI
     - Methodology: EEG channel(s), dataset, participants, driving protocol,
       preprocessing, feature extraction, ML/DL method, classification type,
       evaluation method, performance metrics
     - Theme classification: matched subthemes, theme evidence, confidence
     - ABSTRACT (verbatim from source_row["Abstract Note"]) — this is the
       primary fact-checking ground truth; it must always be present
     - ChatGPT analysis: key findings, paper strengths, limitations mentioned,
       possible use in literature review, writing section fit
   No field may be truncated. No study may be silently dropped.
   Save the complete prompt to prompts/writing_<pid>.md before sending.

2. Academic Synthesis Agent writes paragraph.
3. Save raw response to prompts/response_writing_<pid>.txt.

4. Build consistency-check prompt.
   RULE: Embed the same complete study blocks as step 1 — including the
   verbatim abstract. The auditor must cross-check every performance number,
   electrode claim, and methodological statement against the original abstract
   text, not only against the extracted summary fields.
   Save the complete prompt to prompts/consistency_<pid>.md before sending.

5. Evidence Consistency Auditor returns JSON:
     {
       "passes_check": true/false,
       "overall_score": 0–10,
       "issues_found": [...],
       "revision_needed": true/false,
       "revision_instructions": "..."
     }

6. If passes_check == true → accept paragraph → save .tex → exit loop.

7. If passes_check == false:
     a. Build revision prompt with the specific issues from step 5.
        RULE: Again include the full study blocks including verbatim abstracts.
        The revision agent must be able to verify what the correct fact is
        before rewriting the claim.
     b. Academic Synthesis Agent revises.
     c. Return to step 4.

8. If max_paragraph_revisions reached without PASS → save current draft with
   a WARNING flag in the pipeline log and continue.
```

All intermediate drafts, prompts, and audit reports are saved under `prompts/` and `consistency_reports/` for QC inspection.

---

## 8. Section critique loop (Section Critique Agent)

After all paragraphs in a section have passed the Evidence Consistency Auditor, the pipeline enters the section critique loop:

```
Cycle 1 … 20:
  1. Assemble full section text (concatenate all accepted paragraph texts).
  2. Build section-critique prompt (full section text + complete study blocks
     including verbatim abstracts for all studies cited in the section).
  3. Section Critique Agent returns structured feedback:
       {
         "section_passes": true/false,
         "issues": [...],
         "affected_paragraphs": ["p02_electrode_sites", ...],
         "repair_instructions": { "<pid>": "instruction..." }
       }
  4. If section_passes == true → exit loop.
  5. For each affected paragraph:
       a. Academic Synthesis Agent rewrites the paragraph using the repair instruction.
       b. Evidence Consistency Auditor re-audits the revised paragraph.
          If FAIL → revise again (up to max_paragraph_revisions).
       c. Save updated .tex.
  6. Increment cycle counter → return to step 1.
If 20 cycles reached without section_passes → log WARNING and continue.
```

All critique prompts and structured reports are saved under `section_critique_reports/`.

---

## 9. Global Narrative Flow Auditor

After all sections have completed their critique loops, the Global Narrative Flow Auditor reviews the full assembled document:

```
1. Concatenate all section texts into a single review document.
2. Build global-flow audit prompt (full document + high-level study summaries).
3. Global Narrative Flow Auditor returns structured feedback:
     {
       "flow_passes": true/false,
       "global_issues": [...],
       "affected_sections": [...],
       "repair_instructions": { "<section_subfolder>/<pid>": "instruction..." }
     }
4. For each affected paragraph:
     a. Academic Synthesis Agent rewrites using the repair instruction.
     b. Evidence Consistency Auditor re-audits.
     c. Save updated .tex.
5. Regenerate main.tex, references.bib, and recompile main.pdf.
```

The Global Narrative Flow Auditor runs once after all sections are assembled. Its output is saved to `writing/global_flow_report.json` and `writing/global_flow_report.txt`.

---

## 10. Mandatory LaTeX output requirements

The following elements are **required** in every compiled PDF. Their absence is a pipeline error, not a cosmetic issue.

### 10.1 Reference summary table

Every theme section must include a reference summary table generated from all studies that were cited in the section's paragraphs. The table must appear in the compiled PDF as a `longtable` (landscape orientation) with the following columns:

| Column | Source field |
|---|---|
| Citation | `\cite{citation_key}` |
| First Author | `author` (first name before `;`) |
| Year | `year` |
| EEG Channel(s) | `eeg_channels` |
| Dataset | `dataset` |
| Method | `method` |
| Key Finding | `key_finding` |
| Limitation | `limitation` |

Implementation requirements:

- `reference_table.tex` must be generated by `latex_builder.build_reference_table()` using all studies whose `citation_key` appears in the section's paragraphs.
- `section.tex` must `\input{<subfolder>/reference_table}` so the table is always compiled into the PDF.
- **The table must not be silently skipped** if `cited_keys` is empty — a build error should be raised instead, as an empty table means citation keys were not extracted correctly.
- The pipeline log must record the number of rows written to the table; if the count is zero, the log entry must be flagged as ERROR.

### 10.2 Dataset comparison section

Every theme section must include a dataset comparison section (`dataset_comparison.tex`) that compares the datasets used across all cited studies. It must be `\input`-ed from `section.tex` immediately after the paragraph content.

### 10.3 Verification checklist before marking a run complete

Before a pipeline run is considered finished, verify the compiled `main.pdf` contains:

- [ ] All paragraphs for the section
- [ ] The dataset comparison section
- [ ] The reference summary table with at least one row per cited study
- [ ] A bibliography section with resolved references (no `?` citation markers)

If any item is missing, identify the root cause in the pipeline log and fix it before proceeding to the next theme.

---

## 11. Output files

| File | Location | Description |
|---|---|---|
| Filtered studies | `theme_.../filtered_studies.json` | JSON list of matched papers |
| Paragraph files | `theme_.../paragraphs/<pid>.tex` | One .tex per paragraph |
| Section file | `theme_.../section.tex` | `\input{}` of all paragraphs |
| Dataset comparison | `theme_.../dataset_comparison.tex` | Dataset comparison section |
| Reference table | `theme_.../reference_table.tex` | Longtable with study metadata |
| Master LaTeX | `writing/main.tex` | Full document; auto-regenerated each run |
| Combined BibTeX | `writing/references.bib` | One entry per study across all themes |
| Themes manifest | `writing/themes_manifest.json` | Registry of all completed theme runs |
| Compiled PDF | `writing/main.pdf` | Final output |
| Writing prompts | `theme_.../prompts/writing_*.md` | Academic Synthesis Agent prompts |
| Consistency prompts | `theme_.../prompts/consistency_*.md` | Evidence Auditor prompts |
| Revision prompts | `theme_.../prompts/revision_*.md` | Revision prompts after FAIL |
| Consistency reports | `theme_.../consistency_reports/report_*.json` | Evidence Auditor outputs |
| Section critique prompts | `theme_.../section_critique_reports/prompt_cycle*.md` | Section Critique prompts |
| Section critique reports | `theme_.../section_critique_reports/report_cycle*.json` | Section Critique outputs |
| Global flow report | `writing/global_flow_report.json` | Global Narrative Flow Auditor output |
| Pipeline log | `theme_.../pipeline_log.md` | Full audit trail |

---

## 12. Adapting to a new theme or subtheme

1. Copy the config:
   ```powershell
   Copy-Item setting\lit_review\config.yaml setting\lit_review\config_theme_B.yaml
   ```

2. Edit: change `theme_code`, `theme_name`, `subtheme`, and `paragraph_definitions`.

3. Dry run to confirm study count:
   ```powershell
   python -m apm.lit_review.run_pipeline --config setting/lit_review/config_theme_B.yaml --filter-only
   ```

4. Full run:
   ```powershell
   python -m apm.lit_review.run_pipeline --config setting/lit_review/config_theme_B.yaml
   ```

Outputs land in `writing/theme_B_.../`. The pipeline appends the new theme to `themes_manifest.json` and regenerates `main.tex` and `references.bib` automatically.

---

## 13. Running all themes sequentially

```powershell
foreach ($cfg in @("config_theme_A_single.yaml", "config_theme_A_few.yaml", "config_theme_B.yaml")) {
    python -m apm.lit_review.run_pipeline --config "setting/lit_review/$cfg"
}
```

Each run contributes its section to `main.tex` and merges its studies into `references.bib`. The Global Narrative Flow Auditor runs after the final theme completes (or can be triggered independently after all themes are done).

---

## 14. Compiling the PDF manually

```powershell
cd "C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review\writing"
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

If `pdflatex` is not installed, install [MiKTeX](https://miktex.org/) or [TeX Live](https://tug.org/texlive/).

---

## 15. Module structure

```
apm/lit_review/
  __init__.py              ← package marker
  aggregator.py            ← loads JSON files, filters by theme/subtheme
  prompt_builder.py        ← builds all agent prompts
  writer_agent.py          ← Selenium ChatGPT wrapper
  latex_builder.py         ← generates .tex files, section.tex, main.tex
  bibtex_builder.py        ← generates BibTeX with author_year_hash keys
  pipeline.py              ← orchestrates all agents and loops
  run_pipeline.py          ← CLI entry point
  regenerate_bib.py        ← standalone script to rebuild references.bib

setting/lit_review/
  config.yaml              ← default config (Theme A single-channel EEG)
```

---

## 16. Troubleshooting

### Evidence Consistency Auditor: "Could not parse JSON — skipping revision"

ChatGPT sometimes wraps the JSON response in explanation text. The raw ChatGPT response is saved to:

```
theme_.../consistency_reports/report_<pid>.txt
```

To inspect and manually apply the feedback, edit the paragraph `.tex` file directly. On the next run with `--filter-only` the LaTeX assembly will pick up the edited file.

### Section Critique loop: WARNING after 20 cycles

The pipeline logs a warning and moves on. Review:

```
theme_.../section_critique_reports/report_cycle20.json
```

and apply remaining fixes manually.

### Chrome profile locked (`SessionNotCreatedException`)

A previous Selenium session is still holding the profile.

```powershell
Stop-Process -Name chrome -Force
```

Then re-run.

### `pdflatex` fails on first run

Run the full four-command sequence (pdflatex → bibtex → pdflatex → pdflatex). See section 13 above.
