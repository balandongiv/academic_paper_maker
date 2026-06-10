"""Build and save writing and consistency-checking prompts for ChatGPT.

Design rule: every field available for a study is sent in full.  No truncation.
The abstract (verbatim from source_row["Abstract Note"]) and the full ChatGPT
analysis (methodology, key_findings, literature_review_notes, performance_metrics)
are both included in every study block.  The Evidence Consistency Auditor in
particular needs the original abstract to catch misrepresentations that the
extracted summary fields may not surface.

All prompts are saved to the writing/prompts/ folder for QC inspection.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Writing style + section context
# ---------------------------------------------------------------------------

_WRITING_STYLE_EXCERPT = """\
Writing style guidelines (concept-centric thematic synthesis):
- Organise the paragraph around concepts, NOT paper-by-paper summaries.
- Use a critical voice: compare, contrast, challenge, and synthesise.
- Every factual claim must be traceable to the study evidence provided below.
- Avoid listing papers sequentially; instead group by method, finding, or argument.
- Use the "however pivot": establish trend -> identify contrast -> synthesise implication.
- Write approximately 280-380 words.
- Citations must use LaTeX \\cite{citation_key} format exactly as given.
- Do NOT introduce information that is not in the provided study summaries or abstracts.
- Highlight methodological strengths AND weaknesses.
- End the paragraph with a synthesis statement that draws out the collective implication.
"""

def _section_context(theme_code: str, theme_name: str, subtheme: str) -> str:
    topic = f"{theme_name}" + (f" — {subtheme}" if subtheme else "")
    return (
        "SECTION CONTEXT:\n"
        f"Main theme  : {theme_code} - {theme_name}\n"
        + (f"Subtheme    : {subtheme}\n" if subtheme else "")
        + "Time period : 2017-2026\n"
        f"Topic area  : EEG-based driver fatigue / drowsiness detection — {topic}\n"
    )


# ---------------------------------------------------------------------------
# Study block formatter  (no truncation)
# ---------------------------------------------------------------------------

def _format_study_block(s: dict, idx: int) -> str:
    """Format all available evidence for one study into a readable block.

    Includes:
      - Bibliographic metadata (title, authors, year, journal, DOI)
      - Methodology fields (channels, dataset, model, features, performance, etc.)
      - Verbatim abstract from source_row["Abstract Note"]
      - Full ChatGPT analysis (key_findings, methodology detail, strengths,
        limitations, literature_review_notes, performance_metrics)

    Nothing is truncated.
    """
    subthemes = ", ".join(s.get("subthemes", []))

    # ---- Parse chatgpt_raw_summary once ----
    raw_summary = s.get("chatgpt_raw_summary", "")
    parsed: dict = {}
    if raw_summary:
        try:
            parsed = json.loads(raw_summary)
        except Exception:
            pass

    meth: dict = parsed.get("methodology", {})
    key_findings: list = parsed.get("key_findings", [])
    lit_notes: dict = parsed.get("literature_review_notes", {})
    paper_strengths: list = lit_notes.get("paper_strengths", [])
    paper_limitations: list = lit_notes.get("paper_limitations_mentioned", [])
    writing_fit: list = lit_notes.get("writing_section_fit", [])
    possible_use: str = lit_notes.get("possible_use_in_literature_review", "")

    # ---- Build block ----
    lines = [
        f"[STUDY {idx}]  citation_key={s['citation_key']}",
        f"  Title          : {s['title']}",
        f"  Authors        : {s['author']}",
        f"  Year           : {s['year']}",
        f"  Journal        : {s['journal']}",
        f"  DOI            : {s['doi']}",
        "",
        "  --- Methodology ---",
        f"  EEG channel(s) : {s['eeg_channels'] or meth.get('eeg_channels_or_electrodes') or 'not specified'}",
        f"  EEG usage      : {meth.get('eeg_usage') or 'not specified'}",
        f"  Dataset        : {s['dataset'] or meth.get('data_source') or 'not specified'}",
        f"  Participants   : {s['participants'] or str(meth.get('participants') or 'not specified')}",
        f"  Driving protocol: {meth.get('driving_task_or_protocol') or 'not specified'}",
        f"  Preprocessing  : {s['preprocessing'] or meth.get('preprocessing') or 'not specified'}",
        f"  Feature extraction: {s['feature_extraction'] or meth.get('feature_extraction') or 'not specified'}",
        f"  Traditional ML : {meth.get('traditional_machine_learning_method') or 'none/not applicable'}",
        f"  Deep learning  : {meth.get('deep_learning_method') or 'none/not applicable'}",
        f"  Model category : {meth.get('model_category') or s['method'] or 'not specified'}",
        f"  Classification : {meth.get('classification_type') or 'not specified'}",
        f"  Evaluation     : {meth.get('evaluation_method') or 'not specified'}",
        f"  Performance    : {meth.get('performance_metrics') or 'not specified'}",
        "",
        "  --- Theme classification ---",
        f"  Subthemes      : {subthemes}",
        f"  Theme evidence : {s['theme_evidence']}",
        f"  Confidence     : {s['theme_confidence']}",
        "",
    ]

    # Verbatim abstract — the primary fact-checking ground truth
    abstract = s.get("abstract", "").strip()
    if abstract:
        lines += [
            "  --- ABSTRACT (verbatim from source) ---",
            f"  {abstract}",
            "",
        ]

    # Key findings from ChatGPT analysis
    if key_findings:
        lines.append("  --- Key findings (ChatGPT analysis) ---")
        for kf in key_findings:
            lines.append(f"  * {kf}")
        lines.append("")

    # Paper strengths
    if paper_strengths:
        lines.append("  --- Paper strengths ---")
        for ps in paper_strengths:
            lines.append(f"  + {ps}")
        lines.append("")

    # Limitations
    if paper_limitations:
        lines.append("  --- Limitations mentioned in paper ---")
        for lim in paper_limitations:
            lines.append(f"  - {lim}")
        lines.append("")
    elif s.get("limitation"):
        lines += [
            "  --- Limitation ---",
            f"  - {s['limitation']}",
            "",
        ]

    # Possible use / writing fit
    if possible_use:
        lines += [
            "  --- Possible use in literature review ---",
            f"  {possible_use}",
            "",
        ]
    if writing_fit:
        lines.append("  --- Writing section fit ---")
        for wf in writing_fit:
            lines.append(f"  - {wf}")
        lines.append("")

    return "\n".join(lines)


def _studies_block(studies: list[dict]) -> str:
    return "\n".join(_format_study_block(s, i) for i, s in enumerate(studies, 1))


# ---------------------------------------------------------------------------
# Writing prompt
# ---------------------------------------------------------------------------

def build_writing_prompt(
    paragraph_id: str,
    paragraph_title: str,
    paragraph_focus: str,
    studies: list[dict],
    theme_code: str = "?",
    theme_name: str = "EEG-based driver fatigue detection",
    subtheme: str = "",
    max_summary_chars: int = 0,  # kept for backward compat; value ignored
) -> str:
    study_block = _studies_block(studies)
    citation_list = "\n".join(
        f"  - \\cite{{{s['citation_key']}}}  ({s['author'].split(';')[0].split(',')[0].strip()}, {s['year']})"
        for s in studies
    )
    ctx = _section_context(theme_code, theme_name, subtheme)

    return f"""\
You are an expert academic writer specialising in EEG-based driver fatigue detection research.
Your task is to write ONE well-crafted, critical, and synthetic paragraph for a literature review.

{ctx}
PARAGRAPH ID    : {paragraph_id}
PARAGRAPH TITLE : {paragraph_title}

WRITING INSTRUCTIONS:
{_WRITING_STYLE_EXCERPT}

PARAGRAPH FOCUS (what this paragraph must argue / discuss):
{paragraph_focus.strip()}

AVAILABLE CITATION KEYS (use these exact keys in \\cite{{}} commands):
{citation_list}

STUDY EVIDENCE (verbatim abstracts + full analysis — your ONLY evidence source):
{study_block}

OUTPUT REQUIREMENT:
Write the paragraph now.
- Output only the paragraph text — no headers, no labels, no preamble.
- Use \\cite{{citation_key}} for all citations, using the exact keys listed above.
- The paragraph must be self-contained and critical.
- Every claim must be traceable to the abstracts or analysis sections above.
- Do NOT invent findings.
"""


# ---------------------------------------------------------------------------
# Consistency-check prompt
# ---------------------------------------------------------------------------

def build_consistency_prompt(
    paragraph_id: str,
    generated_paragraph: str,
    studies: list[dict],
    theme_code: str = "?",
    theme_name: str = "EEG-based driver fatigue detection",
    subtheme: str = "",
    max_summary_chars: int = 0,  # kept for backward compat; value ignored
) -> str:
    study_block = _studies_block(studies)
    ctx = _section_context(theme_code, theme_name, subtheme)

    return f"""\
You are an academic quality-control reviewer for a literature review on EEG-based driver fatigue detection.
Your task is to verify the factual accuracy and consistency of the paragraph below against the
provided study evidence.  The verbatim abstract of each paper is included so that you can check
every claim against the original source text, not only against extracted summaries.

{ctx}
PARAGRAPH ID: {paragraph_id}

PARAGRAPH TO CHECK:
---
{generated_paragraph}
---

STUDY EVIDENCE (verbatim abstracts + full analysis — the authoritative fact-checking source):
{study_block}

VERIFICATION CHECKLIST:
1. Is every factual claim in the paragraph supported by the abstracts or analysis above?
2. Are cited studies correctly matched to the claims?  Does \\cite{{key}} match the right study?
3. Has any study been misrepresented or over-claimed relative to what the abstract states?
4. Does the paragraph introduce unsupported generalisations not present in the evidence?
5. Does the paragraph maintain an academic and critical tone?
6. Are any citation keys used that do NOT appear in the study list above?
7. Are performance numbers (accuracy, sensitivity, specificity, AUC) correctly reported?
   Cross-check every number against the "Performance" and "Abstract" fields above.
8. Are electrode/channel claims accurate?  Cross-check against "EEG channel(s)" and the abstract.

YOUR RESPONSE FORMAT:
Start your response with exactly one of:
  VERDICT: PASS
  VERDICT: FAIL

Then write your feedback in plain prose.  If PASS, briefly confirm what was verified.
If FAIL, list each issue clearly: quote the problematic claim, identify which study/abstract
contradicts it, and state what the correct fact is and how the paragraph should be revised.
Be specific so the Academic Synthesis Agent can fix each issue precisely.
"""


# ---------------------------------------------------------------------------
# Revision prompt
# ---------------------------------------------------------------------------

def build_revision_prompt(
    paragraph_id: str,
    original_paragraph: str,
    auditor_feedback: str,
    studies: list[dict],
    theme_code: str = "?",
    theme_name: str = "EEG-based driver fatigue detection",
    subtheme: str = "",
    max_summary_chars: int = 0,  # kept for backward compat; value ignored
) -> str:
    study_block = _studies_block(studies)
    citation_list = "\n".join(
        f"  - \\cite{{{s['citation_key']}}}  ({s['author'].split(';')[0].split(',')[0].strip()}, {s['year']})"
        for s in studies
    )
    ctx = _section_context(theme_code, theme_name, subtheme)

    return f"""\
You are an expert academic writer. The paragraph below was reviewed by an Evidence Consistency Auditor
and did not pass. Revise it to address every issue raised in the auditor's feedback, while preserving
the paragraph's critical and synthetic character.

{ctx}
PARAGRAPH ID: {paragraph_id}

ORIGINAL PARAGRAPH:
---
{original_paragraph}
---

AUDITOR FEEDBACK (fix every issue listed here):
---
{auditor_feedback.strip()}
---

STUDY EVIDENCE (verbatim abstracts + full analysis — your ONLY permitted evidence source):
{study_block}

AVAILABLE CITATION KEYS:
{citation_list}

{_WRITING_STYLE_EXCERPT}

OUTPUT: Write only the revised paragraph. No headers, no labels.
Every claim must be traceable to the abstracts or analysis sections above.
"""


# ---------------------------------------------------------------------------
# Dataset comparison prompt
# ---------------------------------------------------------------------------

def build_dataset_comparison_prompt(
    studies: list[dict],
    theme_code: str = "?",
    theme_name: str = "EEG-based driver fatigue detection",
    subtheme: str = "",
    max_summary_chars: int = 0,  # kept for backward compat; value ignored
) -> str:
    study_block = _studies_block(studies)
    citation_list = "\n".join(
        f"  - \\cite{{{s['citation_key']}}}  ({s['author'].split(';')[0].split(',')[0].strip()}, {s['year']})"
        for s in studies
    )
    ctx = _section_context(theme_code, theme_name, subtheme)

    return f"""\
You are an expert academic writer specialising in EEG-based driver fatigue detection.
Write a DATASET COMPARISON SECTION for the literature review subsection on {theme_name}{" — " + subtheme if subtheme else ""}.

{ctx}

SECTION PURPOSE:
Compare the public and private datasets used across the single-channel EEG studies provided.
The section must cover:
1. Which public datasets were used (names, characteristics, sizes if available).
2. How performance (accuracy, F1, AUC) differs across datasets.
3. Whether single-channel EEG results are directly comparable across studies using different datasets.
4. Whether models appear to generalise across datasets (cross-dataset evidence or lack thereof).
5. Limitations arising from dataset differences: labelling protocols, driving protocols,
   subject numbers, EEG recording setups, and validation strategies (k-fold vs. LOSO vs. hold-out).

WRITING INSTRUCTIONS:
{_WRITING_STYLE_EXCERPT}
- This section should be 3-4 paragraphs (approximately 500-700 words total).
- Each paragraph should have a clear thematic focus.
- Use \\cite{{citation_key}} for all citations with the exact keys provided.
- All performance numbers must be taken directly from the abstracts or performance fields.

AVAILABLE CITATION KEYS:
{citation_list}

STUDY EVIDENCE (verbatim abstracts + full analysis):
{study_block}

OUTPUT: Write the dataset comparison section as plain LaTeX-compatible text with \\cite{{}} citations.
Do not use section headers - the section header will be added separately.
"""


# ---------------------------------------------------------------------------
# Save prompt to file
# ---------------------------------------------------------------------------

def save_prompt(prompt: str, output_folder: Path, filename: str) -> Path:
    output_folder.mkdir(parents=True, exist_ok=True)
    path = output_folder / filename
    path.write_text(prompt, encoding="utf-8")
    log.info("Saved prompt: %s  (%d chars)", path, len(prompt))
    return path
