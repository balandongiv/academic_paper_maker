"""Main orchestration for the literature-review writing pipeline.

Workflow per paragraph:
  1. Select relevant studies from the filtered pool.
  2. Build + save writing prompt.
  3. Send to ChatGPT (Selenium) → get paragraph.
  4. Build + save consistency-check prompt.
  5. Send to ChatGPT → get consistency report.
  6. If revision needed → build + send revision prompt.
  7. Save final paragraph as .tex.

Then:
  8. Write dataset comparison section.
  9. Assemble reference table.
  10. Build + merge BibTeX into writing/references.bib.
  11. Assemble section.tex + update main.tex.
  12. Compile PDF (if pdflatex available).
  13. Write pipeline log.

Output layout (relative to writing root):
  main.tex                         ← master document; regenerated each run
  references.bib                   ← single combined .bib for all themes
  <section_subfolder>/
    section.tex                    ← \subsection + \input paragraphs/*
    paragraphs/<pid>.tex
    dataset_comparison.tex
    reference_table.tex
    filtered_studies.json
    prompts/
    consistency_reports/
    pipeline_log.md
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .aggregator import load_filtered_studies, select_relevant_for_paragraph
from .bibtex_builder import build_bibtex_file, save_bibtex, extract_cited_keys
from .latex_builder import (
    build_reference_table,
    build_section_tex,
    collect_cited_keys,
    save_dataset_comparison_tex,
    save_master_tex,
    save_paragraph_tex,
    save_reference_table_tex,
    save_section_tex,
    update_themes_manifest,
)
from .prompt_builder import (
    build_consistency_prompt,
    build_dataset_comparison_prompt,
    build_revision_prompt,
    build_writing_prompt,
    save_prompt,
)
from .writer_agent import WriterAgent, clean_paragraph_response, detect_pass

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

@dataclass
class ParagraphDef:
    id: str
    title: str
    focus: str
    keyword_filter: list[str] = field(default_factory=list)


@dataclass
class PipelineConfig:
    project_root: Path
    fatigue_eeg_outputs_folder: str
    candidates_csv: str
    writing_folder: str
    theme_code: str
    theme_name: str
    subtheme: str
    max_studies_per_paragraph: int
    max_paragraph_revisions: int
    max_section_critique_cycles: int
    resume: bool
    paragraph_definitions: list[ParagraphDef]
    selenium_cfg: Any  # SeleniumConfig from apm.chatgpt_ui.config


def load_pipeline_config(config_path: str | Path) -> PipelineConfig:
    import yaml
    from apm.chatgpt_ui.config import SeleniumConfig

    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    root = Path(raw["project_root"])
    paragraph_defs = [
        ParagraphDef(
            id=p["id"],
            title=p["title"],
            focus=p["focus"],
            keyword_filter=p.get("keyword_filter", []),
        )
        for p in raw["writing"]["paragraph_definitions"]
    ]
    selenium_raw = raw.get("selenium", {})
    sel_cfg = SeleniumConfig(**selenium_raw)

    writing_cfg = raw["writing"]
    return PipelineConfig(
        project_root=root,
        fatigue_eeg_outputs_folder=raw["input"]["fatigue_eeg_outputs_folder"],
        candidates_csv=raw["input"]["candidates_csv"],
        writing_folder=raw["output"]["writing_folder"],
        theme_code=raw["target"]["theme_code"],
        theme_name=raw["target"]["theme_name"],
        subtheme=raw["target"]["subtheme"],
        max_studies_per_paragraph=writing_cfg.get("max_studies_per_paragraph", 15),
        max_paragraph_revisions=writing_cfg.get("max_paragraph_revisions", 5),
        max_section_critique_cycles=writing_cfg.get("max_section_critique_cycles", 20),
        resume=False,  # set by CLI --resume flag, not from YAML
        paragraph_definitions=paragraph_defs,
        selenium_cfg=sel_cfg,
    )


def _make_subfolder_name(theme_code: str, subtheme: str) -> str:
    """Derive a filesystem-safe subfolder name from theme code + subtheme string."""
    slug = re.sub(r"[^a-z0-9]+", "_", subtheme.lower()).strip("_")
    return f"theme_{theme_code.lower()}_{slug}"


# ---------------------------------------------------------------------------
# Pipeline log
# ---------------------------------------------------------------------------

class PipelineLog:
    def __init__(self, output_path: Path, theme_code: str, theme_name: str, subtheme: str):
        self._path = output_path
        self._lines: list[str] = [
            "# Literature-Review Pipeline Log",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Scope",
            f"Theme {theme_code} — {theme_name} — {subtheme}",
            "",
        ]

    def add(self, section: str, text: str) -> None:
        self._lines.append(f"## {section}")
        self._lines.append(text)
        self._lines.append("")
        self._save()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text("\n".join(self._lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-paragraph pipeline
# ---------------------------------------------------------------------------

def run_paragraph(
    para_def: ParagraphDef,
    all_studies: list[dict],
    agent: WriterAgent,
    prompts_folder: Path,
    consistency_folder: Path,
    paragraphs_folder: Path,
    max_studies: int,
    max_revisions: int,
    pipeline_log: PipelineLog,
    theme_code: str = "?",
    theme_name: str = "EEG-based driver fatigue detection",
    subtheme: str = "",
) -> tuple[str, str]:
    """Run the write → check → revise loop for one paragraph.

    The Evidence Consistency Auditor returns prose feedback.  The pipeline
    reads a VERDICT: PASS / VERDICT: FAIL line at the top of the response and,
    on FAIL, appends the full prose feedback to a revision prompt sent back to
    the Academic Synthesis Agent.  The loop repeats up to *max_revisions* times.

    Returns (paragraph_id, final_paragraph_text).
    """
    pid = para_def.id
    log.info("=== Processing paragraph: %s ===", pid)

    # 1. Select studies
    studies = select_relevant_for_paragraph(all_studies, para_def.keyword_filter, max_studies)
    pipeline_log.add(
        f"Paragraph {pid} — study selection",
        f"Selected {len(studies)} studies.\n"
        + "\n".join(f"  - [{s['citation_key']}] {s['title'][:70]}" for s in studies),
    )
    log.info("Selected %d studies for paragraph %s.", len(studies), pid)

    # 2. Writing prompt → initial draft
    writing_prompt = build_writing_prompt(
        pid, para_def.title, para_def.focus, studies,
        theme_code=theme_code, theme_name=theme_name, subtheme=subtheme,
    )
    save_prompt(writing_prompt, prompts_folder, f"writing_{pid}.md")

    raw_para = agent.write_paragraph(writing_prompt)
    paragraph_text = clean_paragraph_response(raw_para)
    (prompts_folder / f"response_writing_{pid}.txt").write_text(raw_para, encoding="utf-8")

    # 3. Evidence Consistency Auditor loop
    for attempt in range(1, max_revisions + 1):
        check_prompt = build_consistency_prompt(
            pid, paragraph_text, studies,
            theme_code=theme_code, theme_name=theme_name, subtheme=subtheme,
        )
        save_prompt(check_prompt, prompts_folder, f"consistency_{pid}_attempt{attempt}.md")

        auditor_feedback = agent.check_consistency(check_prompt)
        (consistency_folder / f"report_{pid}_attempt{attempt}.txt").write_text(
            auditor_feedback, encoding="utf-8"
        )

        passed = detect_pass(auditor_feedback)
        log.info("Paragraph %s — attempt %d — verdict: %s", pid, attempt, "PASS" if passed else "FAIL")
        pipeline_log.add(
            f"Paragraph {pid} — consistency check (attempt {attempt})",
            f"Verdict: {'PASS' if passed else 'FAIL'}\n\nAuditor feedback:\n{auditor_feedback}",
        )

        if passed:
            log.info("Paragraph %s passed consistency check on attempt %d.", pid, attempt)
            break

        if attempt == max_revisions:
            pipeline_log.add(
                f"Paragraph {pid} — WARNING",
                f"Reached max revisions ({max_revisions}) without PASS — saving current draft.",
            )
            log.warning("Paragraph %s: max revisions reached without PASS.", pid)
            break

        # Revision: append auditor prose feedback to revision prompt
        log.info("Paragraph %s failed — sending revision prompt (attempt %d).", pid, attempt)
        revision_prompt = build_revision_prompt(
            pid, paragraph_text, auditor_feedback, studies,
            theme_code=theme_code, theme_name=theme_name, subtheme=subtheme,
        )
        save_prompt(revision_prompt, prompts_folder, f"revision_{pid}_attempt{attempt}.md")

        raw_revised = agent.revise_paragraph(revision_prompt)
        paragraph_text = clean_paragraph_response(raw_revised)
        (prompts_folder / f"response_revision_{pid}_attempt{attempt}.txt").write_text(
            raw_revised, encoding="utf-8"
        )
        pipeline_log.add(
            f"Paragraph {pid} — revised (attempt {attempt})",
            "Paragraph revised with auditor feedback.",
        )

    # 4. Save .tex
    save_paragraph_tex(pid, para_def.title, paragraph_text, paragraphs_folder)

    return pid, paragraph_text


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_pipeline(config: PipelineConfig) -> None:
    root = config.project_root
    writing_root = root / config.writing_folder

    # Derive section subfolder from config (not hardcoded)
    section_subfolder = _make_subfolder_name(config.theme_code, config.subtheme)
    section_folder = writing_root / section_subfolder
    paragraphs_folder = section_folder / "paragraphs"
    prompts_folder = section_folder / "prompts"
    consistency_folder = section_folder / "consistency_reports"
    log_path = section_folder / "pipeline_log.md"

    for d in [paragraphs_folder, prompts_folder, consistency_folder]:
        d.mkdir(parents=True, exist_ok=True)

    pipeline_log = PipelineLog(log_path, config.theme_code, config.theme_name, config.subtheme)

    # Load and filter studies
    outputs_folder = root / config.fatigue_eeg_outputs_folder
    log.info("Loading studies from %s", outputs_folder)
    all_studies = load_filtered_studies(outputs_folder, config.theme_code, config.subtheme)

    filtered_path = section_folder / "filtered_studies.json"
    filtered_path.write_text(
        json.dumps(all_studies, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    pipeline_log.add(
        "Study filtering",
        f"Total studies found: {len(all_studies)}\n"
        f"Theme: {config.theme_code} — {config.theme_name}\n"
        f"Subtheme: {config.subtheme}\n"
        f"Filtered list saved: {filtered_path}",
    )
    log.info("Loaded %d studies for theme %s / %s.", len(all_studies), config.theme_code, config.subtheme)

    # Run ChatGPT writing agent
    paragraph_contents: dict[str, str] = {}
    paragraph_ids: list[str] = []
    dataset_comparison_text = ""

    with WriterAgent(config.selenium_cfg) as agent:
        for para_def in config.paragraph_definitions:
            existing_tex = paragraphs_folder / f"{para_def.id}.tex"
            if config.resume and existing_tex.exists():
                text = existing_tex.read_text(encoding="utf-8")
                paragraph_contents[para_def.id] = text
                paragraph_ids.append(para_def.id)
                log.info("Paragraph %s already exists — skipping (--resume).", para_def.id)
                pipeline_log.add(f"Paragraph {para_def.id} — SKIPPED", "Already exists on disk (--resume).")
                continue

            try:
                pid, text = run_paragraph(
                    para_def=para_def,
                    all_studies=all_studies,
                    agent=agent,
                    prompts_folder=prompts_folder,
                    consistency_folder=consistency_folder,
                    paragraphs_folder=paragraphs_folder,
                    max_studies=config.max_studies_per_paragraph,
                    max_revisions=config.max_paragraph_revisions,
                    pipeline_log=pipeline_log,
                    theme_code=config.theme_code,
                    theme_name=config.theme_name,
                    subtheme=config.subtheme,
                )
                paragraph_contents[pid] = text
                paragraph_ids.append(pid)
                log.info("Paragraph %s done.", pid)
            except Exception as exc:
                log.error("Paragraph %s failed: %s", para_def.id, exc)
                pipeline_log.add(f"Paragraph {para_def.id} — ERROR", str(exc))
            time.sleep(5)

        # Dataset comparison — skip if already written and resuming
        ds_tex_path = section_folder / "dataset_comparison.tex"
        if config.resume and ds_tex_path.exists():
            dataset_comparison_text = ds_tex_path.read_text(encoding="utf-8")
            log.info("Dataset comparison already exists — skipping (--resume).")
            pipeline_log.add("Dataset comparison — SKIPPED", "Already exists on disk (--resume).")
        else:
            try:
                log.info("Writing dataset comparison section...")
                ds_prompt = build_dataset_comparison_prompt(
                    all_studies[:20],
                    theme_code=config.theme_code,
                    theme_name=config.theme_name,
                    subtheme=config.subtheme,
                )
                save_prompt(ds_prompt, prompts_folder, "writing_dataset_comparison.md")
                raw_ds = agent.write_dataset_comparison(ds_prompt)
                dataset_comparison_text = clean_paragraph_response(raw_ds)
                save_dataset_comparison_tex(dataset_comparison_text, section_folder)
                pipeline_log.add("Dataset comparison", "Dataset comparison section written.")
            except Exception as exc:
                log.error("Dataset comparison failed: %s", exc)
                pipeline_log.add("Dataset comparison — ERROR", str(exc))

    # Assemble LaTeX
    log.info("Assembling LaTeX files...")
    cited_keys = collect_cited_keys(paragraph_contents, dataset_comparison_text)

    ref_table = build_reference_table(all_studies, cited_keys, section_subfolder=section_subfolder)
    save_reference_table_tex(ref_table, section_folder)

    section_tex = build_section_tex(
        paragraph_ids=paragraph_ids,
        section_subfolder=section_subfolder,
        subtheme_label=config.subtheme.title(),
        has_dataset_comparison=bool(dataset_comparison_text),
    )
    save_section_tex(section_tex, section_folder)

    # Update manifest and regenerate main.tex
    update_themes_manifest(writing_root, {
        "subfolder": section_subfolder,
        "theme_code": config.theme_code,
        "theme_name": config.theme_name,
        "subtheme": config.subtheme,
    })
    save_master_tex(writing_root)

    # BibTeX — merge into single writing/references.bib
    bibtex_path = writing_root / "references.bib"
    _merge_bibtex(writing_root, all_studies, cited_keys, bibtex_path)
    entry_count = bibtex_path.read_text(encoding="utf-8").count("@article")
    pipeline_log.add(
        "BibTeX",
        f"BibTeX merged into: {bibtex_path}\n"
        f"New entries from this run: {len(cited_keys)}\n"
        f"Total @article entries in file: {entry_count}",
    )

    # Compile PDF
    _compile_pdf(writing_root / "main.tex", writing_root, pipeline_log)

    pipeline_log.add(
        "Pipeline complete",
        f"All outputs saved under: {section_folder}\n"
        f"Paragraphs written: {len(paragraph_ids)}\n"
        f"Cited keys found: {len(cited_keys)}\n"
        f"BibTeX entries (total): {entry_count}",
    )
    log.info("Pipeline finished. Outputs in: %s", section_folder)


# ---------------------------------------------------------------------------
# BibTeX merge helper
# ---------------------------------------------------------------------------

def _merge_bibtex(writing_root: Path, new_studies: list[dict], cited_keys: set[str], bib_path: Path) -> None:
    """Merge new studies into writing/references.bib.

    Existing entries are kept; new entries from *new_studies* (all of them, not
    just cited ones) are appended if their key is not already present.
    """
    existing_keys: set[str] = set()
    existing_content = ""

    if bib_path.exists():
        existing_content = bib_path.read_text(encoding="utf-8")
        # Extract keys from existing file: @article{key,
        existing_keys = set(re.findall(r"@article\{([^,]+),", existing_content))

    new_entries_content = build_bibtex_file(
        [s for s in new_studies if s["citation_key"] not in existing_keys],
        cited_keys=None,  # include all new studies, not just cited ones
    )

    if existing_content:
        merged = existing_content.rstrip() + "\n\n" + _strip_header(new_entries_content)
    else:
        header = (
            "% BibTeX — EEG-based Driver Fatigue Detection Literature Review\n"
            "% Single combined bibliography for all themes.\n"
            "% Generated and maintained by the fatigue-EEG pipeline.\n\n"
        )
        merged = header + _strip_header(new_entries_content)

    bib_path.write_text(merged, encoding="utf-8")
    log.info("BibTeX written: %s  (keys this run: %d, new to file: %d)", bib_path, len(cited_keys),
             len(new_studies) - len(existing_keys & {s["citation_key"] for s in new_studies}))


def _strip_header(bibtex_content: str) -> str:
    """Remove the % comment header lines from a bibtex string."""
    lines = bibtex_content.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("@"):
            return "".join(lines[i:])
    return bibtex_content


# ---------------------------------------------------------------------------
# PDF compilation
# ---------------------------------------------------------------------------

def _compile_pdf(master_tex: Path, working_dir: Path, pipeline_log: PipelineLog) -> None:
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")
    if pdflatex is None:
        log.warning("pdflatex not found — skipping PDF compilation.")
        pipeline_log.add("PDF compilation", "SKIPPED — pdflatex not found in PATH.")
        return

    log.info("Compiling PDF: %s", master_tex)
    base_name = master_tex.stem  # "main"
    cmd_pdf = [pdflatex, "-interaction=nonstopmode", str(master_tex)]
    cmd_bib = [bibtex, base_name] if bibtex else None

    def run(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=str(working_dir), capture_output=True, text=True, timeout=180)

    run(cmd_pdf)                        # pass 1
    if cmd_bib:
        run(cmd_bib)                    # bibtex
    run(cmd_pdf)                        # pass 2
    result = run(cmd_pdf)               # pass 3

    pdf_path = working_dir / f"{base_name}.pdf"
    if pdf_path.exists():
        pipeline_log.add("PDF compilation", f"PDF compiled successfully: {pdf_path}")
        log.info("PDF compiled: %s", pdf_path)
    else:
        pipeline_log.add(
            "PDF compilation",
            f"PDF not found after compilation. Check pdflatex log.\n"
            f"Stderr (last 500 chars):\n{result.stderr[-500:]}",
        )
        log.warning("PDF not found after compilation attempt.")
