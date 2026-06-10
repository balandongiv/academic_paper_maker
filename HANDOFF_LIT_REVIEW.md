# Literature Review Pipeline — Handoff

**Date:** 2026-06-10  
**Machine:** `C:\Users\balan\IdeaProjects\academic_paper_maker`  
**Python:** `C:\Users\balan\anaconda3\envs\academic_paper_maker\python.exe`  
**Output:** `C:\Users\balan\My Drive (balandong@ums.edu.my)\iterate_literature_review\writing\`

---

## Completed (exit 0, PDF updated after each)

| Theme | Name | Folder |
|-------|------|--------|
| B | Multiclass Sleepiness or Drowsiness Classification | `theme_b_` |
| C | Explainable Artificial Intelligence | `theme_c_` |
| D | Public Dataset Introduction and Benchmarking | `theme_d_` |
| E | Interindividual and Cross-Subject Considerations | `theme_e_` |

Each completed theme has: `paragraphs/p01–p05.tex`, `reference_table.tex`, `section.tex`, `dataset_comparison.tex`.  
`writing\main.tex` and `writing\references.bib` are cumulative across all themes.

---

## Remaining — run in this order

```powershell
Set-Location "C:\Users\balan\IdeaProjects\academic_paper_maker"
$py = "C:\Users\balan\anaconda3\envs\academic_paper_maker\python.exe"

foreach ($cfg in @(
    "config_theme_F.yaml",
    "config_theme_G.yaml",
    "config_theme_H.yaml",
    "config_theme_I.yaml",
    "config_theme_J.yaml",
    "config_theme_K.yaml",
    "config_theme_L.yaml",
    "config_theme_M.yaml",
    "config_theme_P.yaml"
)) {
    Write-Host "=== Starting $cfg ===" -ForegroundColor Cyan
    & $py -m apm.lit_review.run_pipeline --config "setting/lit_review/$cfg"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED — retrying with --resume" -ForegroundColor Yellow
        & $py -m apm.lit_review.run_pipeline --config "setting/lit_review/$cfg" --resume
    }
}
```

### Themes F–P quick reference

| Config | Theme |
|--------|-------|
| `config_theme_F.yaml` | EEG Feature Engineering |
| `config_theme_G.yaml` | EEG Preprocessing and Artifact Removal |
| `config_theme_H.yaml` | Traditional Machine Learning Models |
| `config_theme_I.yaml` | Deep Learning Models |
| `config_theme_J.yaml` | Transfer Learning and Domain Adaptation |
| `config_theme_K.yaml` | Multimodal Driver Fatigue Detection |
| `config_theme_L.yaml` | Experimental Design and Driving Protocol |
| `config_theme_M.yaml` | Real-Time and Practical ESDS Deployment |
| `config_theme_P.yaml` | Safety, Human Factors, and Intervention |

---

## If Chrome crashes mid-theme

Re-run the failed theme with `--resume` — it skips any paragraph `.tex` files already saved:

```powershell
$py = "C:\Users\balan\anaconda3\envs\academic_paper_maker\python.exe"
& $py -m apm.lit_review.run_pipeline --config "setting/lit_review/config_theme_F.yaml" --resume
```

---

## Key facts

- Each theme takes ~25–35 min (5 paragraphs × write → audit → revise loop, up to 10 revisions each)
- `--resume` checks for existing `.tex` files in `paragraphs/` and skips them
- Each completed theme appends its section to `writing\main.tex` and recompiles `writing\main.pdf`
- ChromeDriver auto-downloads via webdriver-manager (cached at `C:\Users\balan\.wdm\`)
- ChatGPT must be logged in on the Chrome profile at `C:\selenium\chrome-profile` — if the session has expired, open Chrome manually with that profile and log in before running the pipeline
- To keep a persistent log: append `2>&1 | Tee-Object "theme_F_log.txt"` to the command
