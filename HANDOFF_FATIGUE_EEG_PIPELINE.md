# Handoff: Fatigue EEG ML Pipeline

**Project:** `academic_paper_maker/`
**Script:** `tutorial/run_fatigue_eeg_pipeline.py`
**Stopped at:** 2026-06-06 ~22:04 (mid Generation 2)
**Resume command:** `python tutorial/run_fatigue_eeg_pipeline.py --max-gen 5`

---

## What this pipeline does

Full automated literature search for EEG-based driver fatigue/drowsiness detection using ML/DL:

1. **Phase 1 — Keyword search (Generation 0):** 25 Scopus advanced-search queries → seed papers
2. **Phase 2 — Forward citation expansion (Generations 1–5):** For each new paper found, retrieve all papers that cite it; repeat for 5 generations

---

## Current state (as of stop)

| Generation | Status | Papers found | RIS files downloaded |
|-----------|--------|-------------|---------------------|
| Gen 0 | ✅ Complete | 1,042 | 25 keyword RIS cached |
| Gen 1 | ✅ Complete | 9,654 | 783 cited-by RIS |
| Gen 2 | 🔄 In progress | N/A (stopped mid-run) | **982 of 9,654** done |
| Gen 3 | ⏳ Not started | — | 0 |
| Gen 4 | ⏳ Not started | — | 0 |
| Gen 5 | ⏳ Not started | — | 0 |

**Master list:** `setting/scopus_setup/complete_file_available_in_zotero.csv` — **10,843 rows**
- 147 original Zotero library entries
- 1,042 Gen 0 seed papers
- 9,654 Gen 1 new papers

---

## How to resume

The pipeline resumes automatically with no manual steps needed.

```powershell
cd C:\Users\balan\IdeaProjects\academic_paper_maker
python tutorial/run_fatigue_eeg_pipeline.py --max-gen 5
```

**What happens on resume:**
- Phase 1 (Gen 0): All 25 keyword RIS files are cached → loads instantly from `output/fatigue_eeg_pipeline/keyword_raw/`
- Gen 0 dedup: returns 0 new (already in master list) → loads 1,042 papers from `generation_0.csv` automatically
- Gen 1 expansion: `generation_1.csv` exists → skipped, loads 9,654 papers from CSV automatically
- **Gen 2 expansion: resumes from paper #983** — the 982 already-downloaded `gen2_cited_by_raw/*.ris` files are detected and skipped by `download_cited_by()` automatically
- Gen 3–5: will run after Gen 2 completes

---

## Output files

All outputs in `output/fatigue_eeg_pipeline/`:

| File | Description |
|------|-------------|
| `generation_0.csv` | 1,042 seed papers (complete) |
| `generation_1.csv` | 9,654 Gen 1 papers (complete) |
| `generation_2.csv` | Will be written when Gen 2 finishes |
| `keyword_raw/kw01_*.ris` … `kw25_*.ris` | All 25 keyword search RIS files (cached) |
| `gen1_cited_by_raw/` | 783 cited-by RIS files for Gen 1 |
| `gen2_cited_by_raw/` | 982 cited-by RIS files so far (Gen 2 in progress) |
| `parent_child_relations.csv` | Gen 1 parent→child citation links |
| `citation_status_per_paper.csv` | Per-paper status for Gen 1 |
| `master_all_papers.csv` | All new papers from completed gens |
| `final_export_2026-06-05_163634.ris` | Gen 0 only — will be regenerated at end |
| `pipeline_log.json` | Run statistics |

---

## Time estimates

- **Gen 2 remaining:** ~8,672 papers × ~60s = ~145 hours (~6 days) at current rate
- **Gen 3–5:** depends on how many new papers Gen 2 finds (likely shrinking)
- Rate: ~50–90 Scopus queries/hour (browser automation, ~60s/paper)

---

## Key bugs already fixed (do NOT revert)

1. **Chrome download directory mismatch** — `set_download_dir(driver, raw_dir)` called at the start of each phase so Chrome downloads to the same folder `wait_for_download` watches.

2. **scopus_id missing from keyword RIS** — Scopus keyword-search RIS puts the paper ID in the `UR` field (not `C7`/`AN`). `_fix_scopus_ids()` extracts it via regex on the URL. Called after `from_ris_entry()` in both phases.

3. **Resume: Gen 0 already in master list** — On re-run, dedup returns 0 new. `_load_gen_csv_as_references()` loads `generation_0.csv` instead, including `scopus_id` extracted from the `Url` column.

4. **Resume: per-generation CSV check** — Each generation checks if its `generation_N.csv` already exists before running citation expansion. If it exists, loads from CSV and skips re-querying.

5. **download_timeout_sec** — Set to 300s in `setting/scopus_setup/scopus_config.json` (was 120s, caused timeouts on large exports).

---

## Scopus session

The browser uses a saved Selenium Chrome profile at `C:\selenium\chrome-profile`.
If Scopus session has expired when resuming:

```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --user-data-dir=C:\selenium\chrome-profile `
    --profile-directory=Default
```

Navigate to scopus.com, log in via Universiti Malaysia Sabah, tick "Keep me signed in", close Chrome. Then re-run the pipeline.

---

## Pipeline script location

`tutorial/run_fatigue_eeg_pipeline.py`

Key functions:
- `KEYWORDS` — list of 25 Scopus advanced search strings (top of file)
- `_fix_scopus_ids(refs)` — patches missing `scopus_id` from `UR` field
- `run_keyword_phase(driver, scopus_cfg, ml, output_dir)` — Phase 1
- `run_one_generation(driver, scopus_cfg, ml, parents, gen_num, output_dir)` — Phase 2 per-gen
- `_load_gen_csv_as_references(csv_path)` — resume helper, reads gen CSV back as References
- `main()` — orchestrates everything, handles all resume logic

CLI flags:
- `--max-gen N` — stop after generation N (default 5)
- `--force` — re-download everything (ignore cache)
- `--dry-run` — validate config without launching Chrome
- `--verbose` — DEBUG logging

---

## Final deliverables (when all gens complete)

Import into Zotero:
```
output/fatigue_eeg_pipeline/final_export_<timestamp>.ris
```

Then update master list:
```
setting/scopus_setup/complete_file_available_in_zotero.csv
```
(replace with new Zotero CSV export after import)
