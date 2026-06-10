"""Generate LaTeX files for the literature-review pipeline.

Directory layout (all paths relative to the writing root, where pdflatex is run):

  main.tex                               <- master document; one \\section per theme
  references.bib                         <- single combined bibliography
  theme_A_single_channel/
    section.tex                          <- \\subsection + \\input paragraphs/*
    paragraphs/p01_overview.tex
    paragraphs/p02_electrode_sites.tex
    ...
    dataset_comparison.tex
    reference_table.tex
  theme_B_.../
    section.tex
    ...
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _latex_safe(text: str) -> str:
    if not text:
        return "---"
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("^",  r"\^{}"),
        ("~",  r"\~{}"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("$",  r"\$"),
    ]
    for src, dst in replacements:
        text = text.replace(src, dst)
    return text


def _trunc(text: str, n: int = 60) -> str:
    text = _latex_safe(text)
    return text[:n] + "..." if len(text) > n else text


# ---------------------------------------------------------------------------
# Paragraph .tex file
# ---------------------------------------------------------------------------

def save_paragraph_tex(paragraph_id: str, paragraph_title: str, content: str, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{paragraph_id}.tex"
    path.write_text(
        f"% Paragraph: {paragraph_title}\n% ID: {paragraph_id}\n\n{content.strip()}\n",
        encoding="utf-8",
    )
    log.info("Saved paragraph TeX: %s", path)
    return path


# ---------------------------------------------------------------------------
# Reference summary table
# ---------------------------------------------------------------------------

def build_reference_table(
    studies: list[dict],
    cited_keys: set[str],
    section_subfolder: str = "theme",
) -> str:
    rows: list[str] = []
    for s in studies:
        if s["citation_key"] not in cited_keys:
            continue
        authors = _trunc(s["author"].split(";")[0] if s["author"] else "---", 25)
        year    = _latex_safe(s["year"] or "---")
        channel = _trunc(s["eeg_channels"] or "---", 30)
        dataset = _trunc(s["dataset"] or "---", 30)
        method  = _trunc(s["method"] or "---", 30)
        finding = _trunc(s["key_finding"] or "---", 60)
        limit   = _trunc(s["limitation"] or "---", 50)
        rows.append(
            f"    \\cite{{{s['citation_key']}}} & {authors} & {year} & "
            f"{channel} & {dataset} & {method} & {finding} & {limit} \\\\"
        )

    if not rows:
        return "% No studies matched for reference table.\n"

    label = re.sub(r"[^a-z0-9]", "_", section_subfolder.lower()).strip("_")
    caption = _latex_safe(section_subfolder.replace("_", " ").title())

    return (
        "\\begin{landscape}\n"
        "\\begin{longtable}{lllllllp{4cm}}\n"
        f"\\caption{{Reference summary — {caption}.}}\n"
        f"\\label{{tab:ref_{label}}} \\\\\n"
        "\\hline\n"
        "\\textbf{Citation} & \\textbf{First Author} & \\textbf{Year} & "
        "\\textbf{EEG Channel} & \\textbf{Dataset} & \\textbf{Method} & "
        "\\textbf{Key Finding} & \\textbf{Limitation} \\\\\n"
        "\\hline\n"
        "\\endfirsthead\n"
        "\\hline\n"
        "\\textbf{Citation} & \\textbf{First Author} & \\textbf{Year} & "
        "\\textbf{EEG Channel} & \\textbf{Dataset} & \\textbf{Method} & "
        "\\textbf{Key Finding} & \\textbf{Limitation} \\\\\n"
        "\\hline\n"
        "\\endhead\n"
        "\\hline\n"
        "\\endfoot\n"
        + "\n".join(rows) + "\n"
        "\\end{longtable}\n\\end{landscape}\n"
    )


# ---------------------------------------------------------------------------
# Dataset comparison .tex
# ---------------------------------------------------------------------------

def save_dataset_comparison_tex(content: str, output_folder: Path) -> Path:
    output_folder.mkdir(parents=True, exist_ok=True)
    path = output_folder / "dataset_comparison.tex"
    path.write_text(
        "% Dataset Comparison\n\n"
        "\\subsection*{Dataset Comparison and Performance Benchmarking}\n\n"
        f"{content.strip()}\n",
        encoding="utf-8",
    )
    log.info("Saved dataset comparison: %s", path)
    return path


# ---------------------------------------------------------------------------
# Per-theme section file  (section.tex inside the theme subfolder)
# ---------------------------------------------------------------------------

def build_section_tex(
    paragraph_ids: list[str],
    section_subfolder: str,
    subtheme_label: str,
    has_dataset_comparison: bool = True,
) -> str:
    """Return the content of section.tex for one theme/subtheme run.

    All \\input{} paths are relative to the writing root (where pdflatex is run),
    so they must be prefixed with the theme subfolder name.
    """
    prefix = f"{section_subfolder}/"
    label = section_subfolder.replace(" ", "_").lower()

    inputs = "\n".join(f"\\input{{{prefix}paragraphs/{pid}}}" for pid in paragraph_ids)
    dataset_line = f"\n\\input{{{prefix}dataset_comparison}}" if has_dataset_comparison else ""
    table_line = f"\n\\input{{{prefix}reference_table}}"

    return (
        f"% Theme section: {subtheme_label}\n"
        f"% Subfolder: {section_subfolder}\n"
        f"% Auto-generated by the fatigue-EEG literature-review pipeline.\n\n"
        f"\\subsection{{{subtheme_label}}}\n"
        f"\\label{{subsec:{label}}}\n\n"
        f"{inputs}\n"
        f"{dataset_line}\n"
        f"{table_line}\n"
    )


def save_section_tex(content: str, output_folder: Path) -> Path:
    """Save the section content to section.tex inside *output_folder*."""
    output_folder.mkdir(parents=True, exist_ok=True)
    path = output_folder / "section.tex"
    path.write_text(content, encoding="utf-8")
    log.info("Saved section TeX: %s", path)
    return path


# ---------------------------------------------------------------------------
# Reference table file
# ---------------------------------------------------------------------------

def save_reference_table_tex(content: str, output_folder: Path) -> Path:
    path = output_folder / "reference_table.tex"
    path.write_text(content, encoding="utf-8")
    log.info("Saved reference table: %s", path)
    return path


# ---------------------------------------------------------------------------
# Themes manifest  (writing/themes_manifest.json)
# ---------------------------------------------------------------------------

_MANIFEST_FILE = "themes_manifest.json"


def update_themes_manifest(writing_root: Path, entry: dict) -> list[dict]:
    """Add or update one entry in the themes manifest; return the full list.

    Each entry: {"subfolder", "theme_code", "theme_name", "subtheme"}.
    Entries are keyed by *subfolder* — updating is idempotent.
    """
    manifest_path = writing_root / _MANIFEST_FILE
    if manifest_path.exists():
        manifest: list[dict] = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = []

    # Replace existing entry for this subfolder, or append
    found = False
    for i, m in enumerate(manifest):
        if m["subfolder"] == entry["subfolder"]:
            manifest[i] = entry
            found = True
            break
    if not found:
        manifest.append(entry)

    manifest.sort(key=lambda m: (m["theme_code"], m["subfolder"]))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Updated themes manifest: %s  (%d entries)", manifest_path, len(manifest))
    return manifest


def read_themes_manifest(writing_root: Path) -> list[dict]:
    manifest_path = writing_root / _MANIFEST_FILE
    if not manifest_path.exists():
        return []
    return json.loads(manifest_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Master LaTeX file  (writing/main.tex)
# ---------------------------------------------------------------------------

_PREAMBLE = r"""\documentclass[12pt,a4paper]{article}

% ── packages ─────────────────────────────────────────────────────────────────
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{geometry}
\geometry{a4paper, margin=2.5cm}
\usepackage{setspace}
\onehalfspacing
\usepackage{parskip}
\usepackage{microtype}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{lscape}
\usepackage{hyperref}
\hypersetup{colorlinks=true, linkcolor=blue, citecolor=blue, urlcolor=blue}
\usepackage{natbib}
\bibliographystyle{apalike}

% ── document ─────────────────────────────────────────────────────────────────
\begin{document}

\title{Literature Review: EEG-Based Driver Fatigue Detection (2017--2026)}
\author{Generated by the fatigue-EEG literature-review pipeline}
\date{\today}
\maketitle
\tableofcontents
\newpage

"""

_POSTAMBLE = r"""
\bibliography{references}

\end{document}
"""


def save_master_tex(writing_root: Path) -> Path:
    """Regenerate main.tex from the themes manifest.

    Groups subtheme runs by theme_code so that each theme gets exactly one
    \\section{} header, with one \\input{subfolder/section} per subtheme beneath it.
    """
    manifest = read_themes_manifest(writing_root)

    # Group by theme_code (preserving sort order from manifest)
    from collections import OrderedDict
    groups: OrderedDict[str, list[dict]] = OrderedDict()
    for entry in manifest:
        tc = entry["theme_code"]
        groups.setdefault(tc, []).append(entry)

    body_lines: list[str] = []
    for theme_code, entries in groups.items():
        theme_name = entries[0]["theme_name"]
        label = f"sec:theme_{theme_code}"
        body_lines.append(f"\\section{{{theme_code}. {theme_name}}}")
        body_lines.append(f"\\label{{{label}}}\n")
        for entry in entries:
            subfolder = entry["subfolder"]
            body_lines.append(f"\\input{{{subfolder}/section}}")
        body_lines.append("")

    body = "\n".join(body_lines)
    content = _PREAMBLE + body + _POSTAMBLE

    path = writing_root / "main.tex"
    path.write_text(content, encoding="utf-8")
    log.info("Saved master TeX: %s  (%d theme group(s))", path, len(groups))
    return path


# ---------------------------------------------------------------------------
# Extract cited keys from paragraph TeX content
# ---------------------------------------------------------------------------

def collect_cited_keys(paragraph_contents: dict[str, str], extra_content: str = "") -> set[str]:
    """Return every citation key used across all paragraph content.

    Handles comma-separated keys inside a single \\cite{a,b,c}.
    """
    all_text = " ".join(paragraph_contents.values()) + " " + extra_content
    raw = re.findall(r"\\cite\{([^}]+)\}", all_text)
    keys: set[str] = set()
    for group in raw:
        for k in group.split(","):
            k = k.strip()
            if k:
                keys.add(k)
    return keys
