"""
Fatigue/Drowsiness EEG ML Pipeline
====================================
Full workflow:
  Phase 1  — 25 keyword searches → Generation 0 (seed papers)
  Phase 2  — Forward citation expansion, Generations 1–5

Outputs (under output/fatigue_eeg_pipeline/):
  master_all_papers.csv           All new papers across all generations
  generation_0.csv … generation_5.csv   Per-generation new papers
  parent_child_relations.csv      Parent → child citation links
  keyword_search_status.csv       Per-keyword result counts / errors
  pipeline_log.json               Full run statistics
  final_export_<timestamp>.ris    All new papers (import into Zotero)

Usage:
  python tutorial/run_fatigue_eeg_pipeline.py              # full run (resume)
  python tutorial/run_fatigue_eeg_pipeline.py --dry-run    # no browser
  python tutorial/run_fatigue_eeg_pipeline.py --force      # re-download all
  python tutorial/run_fatigue_eeg_pipeline.py --max-gen 3  # stop after gen 3
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

MASTER_LIST_PATH = BASE_DIR / "setting/scopus_setup/complete_file_available_in_zotero.csv"
SCOPUS_CONFIG_PATH = BASE_DIR / "setting/scopus_setup/scopus_config.json"
OUTPUT_DIR = BASE_DIR / "output/fatigue_eeg_pipeline"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

from scopus_automation.logging_setup import setup_logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 25 Scopus Advanced Search Queries
# ---------------------------------------------------------------------------

KEYWORDS: list[str] = [
    # ── Search 1: Broad search ──────────────────────────────────────────────
    """TITLE-ABS-KEY(
  ( "driver fatigue" OR "driving fatigue" OR "driver drowsiness" OR
    "driving drowsiness" OR "drowsy driving" OR "driver sleepiness" OR
    "driving sleepiness" OR "driver vigilance" OR "driving vigilance" OR
    "fatigue detection" OR "drowsiness detection" )
  AND ( EEG OR electroencephalograph* OR electroencephalogram* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR "artificial intelligence" OR
        classification OR classifier OR "neural network" OR "support vector machine" OR SVM OR
        CNN OR LSTM OR RNN OR transformer OR "random forest" )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 2: Human driving fatigue/drowsiness classification using EEG ─
    """TITLE-ABS-KEY(
  ( driver* OR driving OR "vehicle driver*" OR "car driver*" OR "human driver*" )
  AND ( fatigue OR drowsiness OR sleepy OR sleepiness OR vigilance OR alertness OR inattention )
  AND ( EEG OR electroencephalograph* OR electroencephalogram* OR electroencephalography )
  AND ( classification OR classify OR classifier OR "fatigue classification" OR
        "drowsiness classification" OR "state classification" )
  AND ( "machine learning" OR "deep learning" OR "artificial intelligence" OR AI )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 3: Deep learning specific ────────────────────────────────────
    """TITLE-ABS-KEY(
  ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "driving drowsiness" OR "drowsy driving" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "deep learning" OR CNN OR "convolutional neural network" OR LSTM OR
        "long short-term memory" OR RNN OR "recurrent neural network" OR
        transformer OR "attention mechanism" OR "graph neural network" OR GNN )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 4: Classical ML models ───────────────────────────────────────
    """TITLE-ABS-KEY(
  ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "drowsy driving" OR "driver vigilance" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR SVM OR "support vector machine" OR
        "random forest" OR "decision tree" OR kNN OR "k-nearest neighbor" OR
        "naive bayes" OR "logistic regression" OR XGBoost OR AdaBoost )
  AND ( classification OR classifier OR detection OR recognition )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 5: Cross-subject / subject-independent ───────────────────────
    """TITLE-ABS-KEY(
  ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "driving drowsiness" OR "drowsy driving" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR classification OR classifier )
  AND ( "cross subject" OR "cross-subject" OR "inter subject" OR "inter-subject" OR
        "subject independent" OR "subject-independent" OR "leave one subject out" OR
        "leave-one-subject-out" OR LOSO OR "domain adaptation" OR
        "transfer learning" OR generalization OR generalisation )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 6: XAI / Explainable AI ──────────────────────────────────────
    """TITLE-ABS-KEY(
  ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "driving drowsiness" OR "drowsy driving" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR "artificial intelligence" OR classification )
  AND ( XAI OR "explainable artificial intelligence" OR "explainable AI" OR
        "interpretable machine learning" OR interpretability OR explainability OR
        SHAP OR LIME OR "Grad-CAM" OR saliency OR "attention mechanism" OR
        "feature importance" )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 7: Binary and multi-class classification ──────────────────────
    """TITLE-ABS-KEY(
  ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
    "driving drowsiness" OR "driver vigilance" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR classifier OR classification )
  AND ( binary OR "binary classification" OR "two class" OR "two-class" OR
        multiclass OR "multi class" OR "multi-class" OR "three class" OR
        "three-class" OR "fatigue level*" OR "drowsiness level*" OR
        alert OR drowsy OR fatigued )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 8: Driving simulator ──────────────────────────────────────────
    """TITLE-ABS-KEY(
  ( "driving simulator" OR "simulated driving" OR "driver simulation" OR
    "virtual driving" OR "real driving" OR "on-road driving" )
  AND ( fatigue OR drowsiness OR sleepiness OR vigilance OR alertness )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR classification OR classifier OR
        "artificial intelligence" )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 9: EEG features + ML classification ───────────────────────────
    """TITLE-ABS-KEY(
  ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR "drowsy driving" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "feature extraction" OR "frequency band*" OR alpha OR beta OR theta OR delta OR
        "power spectral density" OR PSD OR "time frequency" OR "wavelet transform" OR
        entropy OR "differential entropy" )
  AND ( classification OR classifier OR "machine learning" OR "deep learning" )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 10: Very narrow best-match ────────────────────────────────────
    """TITLE-ABS-KEY(
  ( "driver drowsiness detection" OR "driver fatigue detection" OR
    "driving drowsiness detection" OR "driving fatigue detection" )
  AND ( EEG OR electroencephalography )
  AND ( "machine learning" OR "deep learning" )
  AND ( classification OR classifier )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 11: Mental / cognitive fatigue ────────────────────────────────
    """TITLE-ABS-KEY(
  ( "mental fatigue" OR "cognitive fatigue" OR "reduced vigilance" OR
    "vigilance decrement" )
  AND ( driver* OR driving OR "vehicle driver*" OR "car driver*" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR classification OR classifier )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 12: Driver alertness / inattention ────────────────────────────
    """TITLE-ABS-KEY(
  ( "driver alertness" OR "driver inattention" OR "sleepiness detection" OR
    "fatigue level" OR "drowsiness level" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR "artificial intelligence" OR
        classification OR classifier )
  AND ( driving OR driver* )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 13: Brain signal / brain wave terminology ─────────────────────
    """TITLE-ABS-KEY(
  ( "brain signal*" OR "brain wave*" OR "brainwave*" OR "EEG signal*" OR "EEG-based" )
  AND ( "driver fatigue" OR "driving fatigue" OR "driver drowsiness" OR "drowsy driving" )
  AND ( "machine learning" OR "deep learning" OR classification OR classifier )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 14: Physiological signal with EEG focus ───────────────────────
    """TITLE-ABS-KEY(
  ( "physiological signal*" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( driver* OR driving )
  AND ( fatigue OR drowsiness OR vigilance OR sleepiness )
  AND ( "machine learning" OR "deep learning" OR classifier OR classification )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 15: Real-time detection ───────────────────────────────────────
    """TITLE-ABS-KEY(
  ( "real-time" OR "real time" OR online )
  AND ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR "drowsy driving" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR classification OR classifier OR detection )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 16: Wearable EEG ──────────────────────────────────────────────
    """TITLE-ABS-KEY(
  ( wearable OR portable OR "dry electrode*" OR "wireless EEG" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( driver* OR driving )
  AND ( fatigue OR drowsiness OR vigilance OR sleepiness )
  AND ( "machine learning" OR "deep learning" OR classification )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 17: CNN-specific ───────────────────────────────────────────────
    """TITLE-ABS-KEY(
  ( CNN OR "convolutional neural network" OR "convolutional network" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
        "drowsy driving" OR "driver vigilance" OR "fatigue detection" OR
        "drowsiness detection" )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 18: LSTM/RNN-specific ─────────────────────────────────────────
    """TITLE-ABS-KEY(
  ( LSTM OR "long short-term memory" OR RNN OR "recurrent neural network" OR
    "temporal model" OR "sequence model" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
        "drowsy driving" OR "fatigue detection" OR "drowsiness detection" )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 19: Transformer / attention ───────────────────────────────────
    """TITLE-ABS-KEY(
  ( transformer OR "self-attention" OR "multi-head attention" OR "attention mechanism" OR
    "vision transformer" OR ViT OR BERT )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
        "drowsy driving" OR fatigue OR drowsiness )
  AND ( driving OR driver* )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 20: Ensemble learning ─────────────────────────────────────────
    """TITLE-ABS-KEY(
  ( "ensemble learning" OR "ensemble method*" OR bagging OR boosting OR stacking OR
    "hybrid model" OR "fusion" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR "drowsy driving" )
  AND ( classification OR classifier OR "machine learning" OR "deep learning" )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 21: Personalized / subject-specific model ─────────────────────
    """TITLE-ABS-KEY(
  ( "personalized model" OR "subject-specific" OR "individual model" OR
    "subject adaptation" OR "fine-tuning" OR "few-shot" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR "drowsy driving" OR
        fatigue OR drowsiness )
  AND ( driving OR driver* )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 22: Transfer learning / domain adaptation ─────────────────────
    """TITLE-ABS-KEY(
  ( "transfer learning" OR "domain adaptation" OR "domain generalization" OR
    "pre-trained" OR "fine-tune" OR "knowledge transfer" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
        "drowsy driving" OR "fatigue detection" OR "drowsiness detection" )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 23: Public EEG dataset (SEED-VIG, DEAP, etc.) ─────────────────
    """TITLE-ABS-KEY(
  ( "SEED-VIG" OR "SEED VIG" OR "DEAP dataset" OR "MAHNOB-HCI" OR "driving dataset" OR
    "fatigue dataset" OR "drowsiness dataset" OR "EEG benchmark" )
  AND ( fatigue OR drowsiness OR vigilance OR sleepiness OR alertness )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( "machine learning" OR "deep learning" OR classification )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 24: Multimodal (EEG + other biosignals) ───────────────────────
    """TITLE-ABS-KEY(
  ( multimodal OR "multi-modal" OR "EEG and EOG" OR "EEG and EMG" OR "EEG and ECG" OR
    "EEG and eye" OR "EEG and heart rate" OR "EEG and GSR" )
  AND ( "driver fatigue" OR "driver drowsiness" OR "driving fatigue" OR
        "drowsy driving" OR fatigue OR drowsiness )
  AND ( driving OR driver* )
  AND ( "machine learning" OR "deep learning" OR classification )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",

    # ── Search 25: Graph neural network / functional connectivity ─────────────
    """TITLE-ABS-KEY(
  ( "graph neural network" OR GNN OR "graph convolutional" OR GCN OR
    "functional connectivity" OR "brain connectivity" OR "brain network" )
  AND ( EEG OR electroencephalograph* OR electroencephalography )
  AND ( fatigue OR drowsiness OR vigilance OR "driver fatigue" OR "driver drowsiness" )
  AND ( driving OR driver* OR "fatigue detection" OR "drowsiness detection" )
  AND ( "machine learning" OR "deep learning" OR classification )
) AND PUBYEAR > 2015 AND LANGUAGE(english) AND (DOCTYPE(ar) OR DOCTYPE(cp))""",
]

assert len(KEYWORDS) == 25, f"Expected 25 keywords, got {len(KEYWORDS)}"


# ---------------------------------------------------------------------------
# Imports from pipeline
# ---------------------------------------------------------------------------

from pipeline.dedup_engine import deduplicate_references
from pipeline.master_list import MasterList
from pipeline.models import Reference
from pipeline.ris_exporter import export_to_ris


# ---------------------------------------------------------------------------
# Helper: query slug for file naming
# ---------------------------------------------------------------------------

def _query_slug(query: str, index: int) -> str:
    stem = re.sub(r"[^\w\s-]", "", query.lower())
    stem = re.sub(r"[\s_]+", "_", stem).strip("_")
    return f"kw{index:02d}_{stem[:60]}"


# ---------------------------------------------------------------------------
# Helper: fill in missing scopus_id from the UR (URL) field in the raw entry
# ---------------------------------------------------------------------------

def _fix_scopus_ids(refs: list) -> int:
    """Extract scopus_id from UR field for references that have no EID.

    Scopus keyword-search RIS exports put the ID in the URL:
      UR  - https://www.scopus.com/pages/publications/85213530694?origin=...
    but not in C7/AN as a '2-s2.0-...' string.
    Returns the number of references fixed.
    """
    fixed = 0
    for ref in refs:
        if ref.scopus_id:
            continue
        raw = ref._raw or {}
        ur = ""
        ur_val = raw.get("UR") or raw.get("ur") or ""
        if isinstance(ur_val, list):
            ur = str(ur_val[0]) if ur_val else ""
        else:
            ur = str(ur_val)
        m = re.search(r"scopus\.com/pages/publications/(\d+)", ur)
        if m:
            ref.scopus_id = m.group(1)
            ref.scopus_eid = f"2-s2.0-{ref.scopus_id}"
            fixed += 1
    return fixed


# ---------------------------------------------------------------------------
# Phase 1: Keyword searches → Generation 0
# ---------------------------------------------------------------------------

def run_keyword_phase(
    driver,
    scopus_cfg,
    ml: MasterList,
    output_dir: Path,
    resume: bool = True,
    force: bool = False,
) -> tuple[list[Reference], list[dict]]:
    """Run all 25 keyword searches. Returns (new_references, per_keyword_status)."""
    from scopus_automation.browser import set_download_dir
    from scopus_automation.ris import parse_ris_file
    from scopus_automation.search_export import search_and_export

    raw_dir = output_dir / "keyword_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # CRITICAL: Chrome's download directory must match the directory that
    # search_and_export / wait_for_download watches.
    set_download_dir(driver, raw_dir)
    scopus_cfg.output_dir = str(raw_dir)

    all_refs: list[Reference] = []
    per_keyword_status: list[dict] = []

    print(f"\n{'=' * 60}")
    print("  PHASE 1 — KEYWORD SEARCHES (Generation 0)")
    print(f"  {len(KEYWORDS)} queries to run")
    print(f"{'=' * 60}")

    for i, keyword in enumerate(KEYWORDS, 1):
        slug = _query_slug(keyword, i)
        ris_path = raw_dir / f"{slug}.ris"

        if resume and not force and ris_path.exists() and ris_path.stat().st_size > 10:
            # Resume: parse existing file without re-querying Scopus
            print(f"\n  [{i:2d}/{len(KEYWORDS)}] RESUME: {slug[:55]}")
            raw_entries = parse_ris_file(str(ris_path))
            refs = [
                Reference.from_ris_entry(e, source_file=str(ris_path),
                                         query=keyword, query_keyword=keyword)
                for e in raw_entries
            ]
            _fix_scopus_ids(refs)
            all_refs.extend(refs)
            n = len(raw_entries)
            print(f"           → {n} results loaded from cache.")
            per_keyword_status.append({
                "index": i, "slug": slug, "status": "resumed",
                "result_count": n, "ris_file": str(ris_path), "error": "",
            })
            continue

        print(f"\n  [{i:2d}/{len(KEYWORDS)}] {keyword[:70]}")

        meta = search_and_export(
            driver=driver,
            query=keyword,
            config=scopus_cfg,
            output_dir=raw_dir,
        )

        n = meta.get("result_count", 0)
        downloaded_ris = meta.get("ris_file", "")
        err = meta.get("error", "")

        # Rename/copy to our slug-named file for consistent resume
        if downloaded_ris and Path(downloaded_ris).exists() and downloaded_ris != str(ris_path):
            import shutil
            shutil.copy2(downloaded_ris, ris_path)

        if ris_path.exists() and ris_path.stat().st_size > 10:
            raw_entries = parse_ris_file(str(ris_path))
            refs = [
                Reference.from_ris_entry(e, source_file=str(ris_path),
                                         query=keyword, query_keyword=keyword)
                for e in raw_entries
            ]
            _fix_scopus_ids(refs)
            all_refs.extend(refs)
            print(f"           → {n} results found.")
            per_keyword_status.append({
                "index": i, "slug": slug, "status": "ok",
                "result_count": n, "ris_file": str(ris_path), "error": "",
            })
        else:
            msg = f"ERROR: {err}" if err else "0 results / no RIS file."
            print(f"           → {msg}")
            per_keyword_status.append({
                "index": i, "slug": slug,
                "status": "error" if err else "no_results",
                "result_count": 0, "ris_file": "", "error": err,
            })

    return all_refs, per_keyword_status


# ---------------------------------------------------------------------------
# Phase 2: Citation expansion — one generation
# ---------------------------------------------------------------------------

def run_one_generation(
    driver,
    scopus_cfg,
    ml: MasterList,
    parents: list[Reference],
    gen_num: int,
    output_dir: Path,
    force: bool = False,
) -> tuple[list[Reference], list[dict], list[dict]]:
    """Forward-citation search for all parents.

    Returns:
      (all_children_raw, per_paper_status, parent_child_relations)
    """
    from scopus_automation.browser import set_download_dir
    from scopus_automation.cited_by import download_cited_by
    from scopus_automation.ris import parse_ris_file

    raw_dir = output_dir / f"gen{gen_num}_cited_by_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Redirect Chrome downloads to this generation's raw directory
    set_download_dir(driver, raw_dir)
    scopus_cfg.output_dir = str(raw_dir)

    all_children: list[Reference] = []
    per_paper_status: list[dict] = []
    parent_child_relations: list[dict] = []

    # Only parents with a Scopus ID can be queried
    queryable = [p for p in parents if p.scopus_id]
    no_id = [p for p in parents if not p.scopus_id]

    print(f"\n{'=' * 60}")
    print(f"  PHASE 2 — CITATION EXPANSION — Generation {gen_num}")
    print(f"  Parents with Scopus ID: {len(queryable)} / {len(parents)}")
    if no_id:
        print(f"  Skipped (no Scopus ID): {len(no_id)}")
    print(f"{'=' * 60}")

    for i, parent in enumerate(queryable, 1):
        url = f"https://www.scopus.com/pages/publications/{parent.scopus_id}"
        print(f"\n  [{i:3d}/{len(queryable)}] {parent.title[:65]}")
        print(f"          EID: {parent.scopus_eid or '—'}")

        result = download_cited_by(
            driver=driver,
            paper_link=url,
            config=scopus_cfg,
            output_dir=raw_dir,
            force=force,
        )

        n = result.get("cited_by_result_count", 0)
        ris_path = result.get("cited_by_ris_file", "")
        err = result.get("cited_by_error", "")

        if ris_path and Path(ris_path).exists():
            raw_entries = parse_ris_file(ris_path)
            children = [
                Reference.from_ris_entry(
                    e,
                    source_file=ris_path,
                    parent=parent,
                    query=f"REFEID({parent.scopus_eid})",
                )
                for e in raw_entries
            ]
            _fix_scopus_ids(children)
            all_children.extend(children)

            for child in children:
                parent_child_relations.append({
                    "generation": gen_num,
                    "parent_record_id": parent.record_id,
                    "parent_scopus_eid": parent.scopus_eid,
                    "parent_title": parent.title[:100],
                    "child_record_id": child.record_id,
                    "child_scopus_eid": child.scopus_eid,
                    "child_title": child.title[:100],
                    "child_doi": child.doi,
                    "child_year": child.year,
                })

            print(f"          → {n} citing papers found.")
            per_paper_status.append({
                "generation": gen_num,
                "record_id": parent.record_id,
                "scopus_eid": parent.scopus_eid,
                "title": parent.title[:80],
                "status": "ok",
                "result_count": n,
                "ris_file": ris_path,
                "error": "",
            })
        else:
            msg = f"ERROR: {err}" if err else "0 citing papers."
            print(f"          → {msg}")
            per_paper_status.append({
                "generation": gen_num,
                "record_id": parent.record_id,
                "scopus_eid": parent.scopus_eid,
                "title": parent.title[:80],
                "status": "error" if err else "no_results",
                "result_count": 0,
                "ris_file": "",
                "error": err,
            })

        # Mark parent as processed in master list
        ml.mark_parent_processed(
            parent,
            result_count=n,
            exported_count=0,
            timestamp=datetime.now().isoformat(),
        )

    for p in no_id:
        per_paper_status.append({
            "generation": gen_num,
            "record_id": p.record_id,
            "scopus_eid": "",
            "title": p.title[:80],
            "status": "skipped_no_scopus_id",
            "result_count": 0,
            "ris_file": "",
            "error": "no_scopus_id",
        })

    return all_children, per_paper_status, parent_child_relations


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def _write_csv(rows: list[dict], path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), path)


def write_references_to_csv(refs: list[Reference], path: Path) -> None:
    """Write a list of References to a flat CSV (master list schema)."""
    if not refs:
        return
    rows = [r.to_master_list_row() for r in refs]
    # Collect all unique keys across rows
    all_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                all_keys.append(k)
    _write_csv(rows, path, all_keys)


def write_keyword_status(status: list[dict], path: Path) -> None:
    fields = ["index", "slug", "status", "result_count", "ris_file", "error"]
    _write_csv(status, path, fields)


def write_per_paper_status(rows: list[dict], path: Path, append: bool = False) -> None:
    fields = ["generation", "record_id", "scopus_eid", "title",
              "status", "result_count", "ris_file", "error"]
    mode = "a" if append else "w"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode, newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if not append or path.stat().st_size == 0:
            w.writeheader()
        w.writerows(rows)


def write_parent_child_csv(relations: list[dict], path: Path) -> None:
    fields = ["generation", "parent_record_id", "parent_scopus_eid", "parent_title",
              "child_record_id", "child_scopus_eid", "child_title", "child_doi", "child_year"]
    _write_csv(relations, path, fields)


def write_pipeline_log(log_data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(log_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Pipeline log: {path}")


def _load_gen_csv_as_references(csv_path: Path) -> list[Reference]:
    """Reload a generation CSV as Reference objects (for resume across runs).

    Only scopus_id, scopus_eid, doi, title, year, authors, record_id are needed
    for citation expansion — these are all present in the CSV.
    """
    import pandas as pd
    if not csv_path.exists():
        return []
    try:
        df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig").fillna("")
    except Exception as exc:
        log.warning("Could not load %s: %s", csv_path, exc)
        return []
    refs = []
    for _, row in df.iterrows():
        ref = Reference(
            record_id=row.get("record_id", ""),
            title=row.get("Title", ""),
            year=row.get("Publication Year", ""),
            doi=row.get("DOI", ""),
            scopus_eid=row.get("scopus_eid", ""),
            scopus_id=row.get("scopus_id", ""),
            reference_role=row.get("reference_role", "child"),
            source_input_mode="csv_resume",
        )
        authors_raw = row.get("Author", "")
        if authors_raw:
            ref.authors = [a.strip() for a in authors_raw.split(";") if a.strip()]
        # If scopus_id is missing, extract from Url column
        if not ref.scopus_id:
            url = row.get("Url", "")
            m = re.search(r"scopus\.com/pages/publications/(\d+)", url)
            if m:
                ref.scopus_id = m.group(1)
                ref.scopus_eid = f"2-s2.0-{ref.scopus_id}"
        refs.append(ref)
    log.info("Loaded %d references from %s for resume", len(refs), csv_path)
    return refs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fatigue EEG ML pipeline: keyword search + 5-generation citation expansion"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate setup without launching Chrome")
    parser.add_argument("--force", action="store_true",
                        help="Re-download all Scopus queries (no resume)")
    parser.add_argument("--max-gen", type=int, default=5,
                        help="Maximum generations of citation expansion (default 5)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable DEBUG logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(OUTPUT_DIR / "logs", level=log_level)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat()

    print(f"\n{'=' * 60}")
    print("  FATIGUE EEG ML PIPELINE")
    print(f"  Started: {started_at}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Force:   {args.force}")
    print(f"  Max gen: {args.max_gen}")
    print(f"  Output:  {OUTPUT_DIR}")
    print(f"{'=' * 60}")

    # ── Load master list ────────────────────────────────────────────────────
    print(f"\nLoading master list: {MASTER_LIST_PATH}")
    ml = MasterList.load(MASTER_LIST_PATH, reuse_existing=True)
    ml_rows_initial = ml.row_count
    print(f"  {ml.summary()}")

    if args.dry_run:
        print("\nDRY RUN — configuration validated.")
        print(f"  25 keyword queries ready.")
        print(f"  Master list: {ml_rows_initial} rows")
        print(f"  Output dir:  {OUTPUT_DIR}")
        return

    # ── Start browser ───────────────────────────────────────────────────────
    from scopus_automation.browser import build_driver, set_download_dir
    from scopus_automation.config import ScopusConfig

    print(f"\nLoading Scopus config: {SCOPUS_CONFIG_PATH}")
    scopus_cfg = ScopusConfig.from_file(str(SCOPUS_CONFIG_PATH))

    # Initial download dir (will be overridden per-phase by each run function)
    initial_dl_dir = OUTPUT_DIR / "keyword_raw"
    initial_dl_dir.mkdir(parents=True, exist_ok=True)

    print("Starting Chrome browser...")
    driver = build_driver(scopus_cfg, download_dir=initial_dl_dir)
    set_download_dir(driver, initial_dl_dir)

    # ── Tracking state ──────────────────────────────────────────────────────
    all_new_refs: list[Reference] = []          # all new refs across all gens
    all_parent_child: list[dict] = []           # all parent-child relations
    all_citation_status: list[dict] = []        # per-paper citation status
    gen_summaries: list[dict] = []              # per-gen summary stats
    errors: list[str] = []

    try:
        # ── Phase 1: Keyword searches → Generation 0 ─────────────────────
        kw_raw_refs, kw_status = run_keyword_phase(
            driver, scopus_cfg, ml, OUTPUT_DIR,
            resume=not args.force, force=args.force,
        )

        total_kw_results = sum(s["result_count"] for s in kw_status)
        print(f"\n  Total raw keyword results: {len(kw_raw_refs)}")

        # Save keyword status
        write_keyword_status(kw_status, OUTPUT_DIR / "keyword_search_status.csv")

        # Deduplicate Gen 0 against master list
        print(f"\nDeduplicating Gen 0 ({len(kw_raw_refs)} records)...")
        dedup0 = deduplicate_references(kw_raw_refs, ml)
        gen0_new = dedup0.new_references
        print(f"  New (not in Zotero/master): {dedup0.new_count}")
        print(f"  Duplicates removed:         {dedup0.duplicate_count}")

        gen0_csv = OUTPUT_DIR / "generation_0.csv"

        if gen0_new:
            # First run: add Gen 0 to master list and write CSV
            for ref in gen0_new:
                ref.reference_role = "child"
                ml.add_or_update(ref)
                ml.mark_exported(ref)
            ml.save()
            for ref in gen0_new:
                ref.query_keyword = ref.query_keyword or "keyword_search_gen0"
            all_new_refs.extend(gen0_new)
            write_references_to_csv(gen0_new, gen0_csv)
            print(f"  Generation 0 written: {gen0_csv} ({len(gen0_new)} records)")
            gen0_for_expansion = gen0_new
        else:
            # Resume run: Gen 0 already in master list — reload from CSV for citation expansion
            gen0_for_expansion = _load_gen_csv_as_references(gen0_csv)
            if gen0_for_expansion:
                print(f"  RESUME: Generation 0 already in master list.")
                print(f"  Loaded {len(gen0_for_expansion)} Gen 0 papers from {gen0_csv} for citation expansion.")
            else:
                print("  WARNING: No Gen 0 papers found and no CSV to resume from.")

        gen_summaries.append({
            "generation": 0,
            "phase": "keyword_search",
            "total_scopus_results": total_kw_results,
            "duplicates_removed": dedup0.duplicate_count,
            "new_records": dedup0.new_count if gen0_new else len(gen0_for_expansion),
        })

        # ── Phase 2: Citation expansion Generations 1–N ───────────────────
        current_gen_papers = gen0_for_expansion
        gen_num = 0

        while gen_num < args.max_gen and current_gen_papers:
            gen_num += 1
            gen_csv = OUTPUT_DIR / f"generation_{gen_num}.csv"

            # Resume: if this generation's CSV already exists and has content, skip
            if not args.force and gen_csv.exists() and gen_csv.stat().st_size > 10:
                gen_resumed = _load_gen_csv_as_references(gen_csv)
                if gen_resumed:
                    print(f"\n\nRESUME: Generation {gen_num} already complete "
                          f"({len(gen_resumed)} records). Loading from CSV.")
                    current_gen_papers = gen_resumed
                    gen_summaries.append({
                        "generation": gen_num,
                        "phase": "citation_expansion_resumed",
                        "total_scopus_results": 0,
                        "duplicates_removed": 0,
                        "new_records": len(gen_resumed),
                    })
                    continue

            print(f"\n\nStarting Generation {gen_num} expansion "
                  f"({len(current_gen_papers)} parent papers)...")

            children_raw, cite_status, relations = run_one_generation(
                driver, scopus_cfg, ml,
                current_gen_papers, gen_num, OUTPUT_DIR,
                force=args.force,
            )

            all_citation_status.extend(cite_status)
            all_parent_child.extend(relations)

            # Save intermediate citation status (append mode per gen)
            status_path = OUTPUT_DIR / "citation_status_per_paper.csv"
            write_per_paper_status(cite_status, status_path,
                                   append=(gen_num > 1))

            total_gen_results = sum(
                s["result_count"] for s in cite_status
            )
            print(f"\n  Gen {gen_num} total citing papers found: {total_gen_results}")

            # Deduplicate against master list
            print(f"  Deduplicating {len(children_raw)} records...")
            dedup_n = deduplicate_references(children_raw, ml)
            gen_new = dedup_n.new_references
            print(f"  New: {dedup_n.new_count}   Duplicates: {dedup_n.duplicate_count}")

            # Add to master list
            for ref in gen_new:
                ml.add_or_update(ref)
                ml.mark_exported(ref)
            ml.save()

            all_new_refs.extend(gen_new)

            # Write per-generation CSV
            write_references_to_csv(gen_new, gen_csv)
            print(f"  Generation {gen_num} written: {gen_csv} ({len(gen_new)} records)")

            # Write intermediate parent-child CSV
            write_parent_child_csv(all_parent_child,
                                   OUTPUT_DIR / "parent_child_relations.csv")

            gen_summaries.append({
                "generation": gen_num,
                "phase": "citation_expansion",
                "total_scopus_results": total_gen_results,
                "duplicates_removed": dedup_n.duplicate_count,
                "new_records": dedup_n.new_count,
            })

            if not gen_new:
                print(f"\n  No new papers in Generation {gen_num}. Stopping expansion.")
                break

            current_gen_papers = gen_new

    except KeyboardInterrupt:
        print("\n\n  Interrupted by user. Saving progress...")
        errors.append("Interrupted by user.")
    except Exception as exc:
        msg = f"Fatal error: {exc}"
        print(f"\n  ERROR: {msg}")
        log.exception("Fatal error in pipeline")
        errors.append(msg)
    finally:
        try:
            driver.quit()
            print("\n  Browser closed.")
        except Exception:
            pass

    # ── Final outputs ───────────────────────────────────────────────────────
    completed_at = datetime.now().isoformat()

    print(f"\n\n{'=' * 60}")
    print("  WRITING FINAL OUTPUTS")
    print(f"{'=' * 60}")

    # Master combined CSV
    master_csv = OUTPUT_DIR / "master_all_papers.csv"
    write_references_to_csv(all_new_refs, master_csv)
    print(f"\n  Master CSV: {master_csv} ({len(all_new_refs)} records)")

    # Parent-child relations CSV
    pc_csv = OUTPUT_DIR / "parent_child_relations.csv"
    write_parent_child_csv(all_parent_child, pc_csv)
    print(f"  Parent-child CSV: {pc_csv} ({len(all_parent_child)} relations)")

    # Final RIS file
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    ris_path = OUTPUT_DIR / f"final_export_{ts}.ris"
    if all_new_refs:
        export_to_ris(all_new_refs, ris_path)
        print(f"  RIS export: {ris_path} ({len(all_new_refs)} records)")
    else:
        ris_path = Path("")
        print("  No new records to export.")

    # Pipeline log
    ml_rows_final = ml.row_count
    log_data = {
        "pipeline": "fatigue_eeg_ml",
        "started_at": started_at,
        "completed_at": completed_at,
        "master_list_path": str(MASTER_LIST_PATH),
        "master_list_rows_initial": ml_rows_initial,
        "master_list_rows_final": ml_rows_final,
        "master_list_rows_added": ml_rows_final - ml_rows_initial,
        "total_keyword_queries": len(KEYWORDS),
        "max_generations_requested": args.max_gen,
        "generations_completed": len(gen_summaries) - 1,  # -1 for gen0
        "total_new_records": len(all_new_refs),
        "total_parent_child_relations": len(all_parent_child),
        "ris_output": str(ris_path),
        "generation_summaries": gen_summaries,
        "errors": errors,
    }
    write_pipeline_log(log_data, OUTPUT_DIR / "pipeline_log.json")

    # ── Final summary ───────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("  PIPELINE COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Started:              {started_at}")
    print(f"  Completed:            {completed_at}")
    print(f"  Master list rows:     {ml_rows_initial} → {ml_rows_final} (+{ml_rows_final - ml_rows_initial})")
    print(f"\n  Generation summary:")
    for gs in gen_summaries:
        print(f"    Gen {gs['generation']:d}: "
              f"{gs['total_scopus_results']:5d} Scopus results, "
              f"{gs['duplicates_removed']:5d} duplicates, "
              f"{gs['new_records']:5d} new")
    print(f"\n  Total new records:    {len(all_new_refs)}")
    print(f"  Parent-child links:   {len(all_parent_child)}")
    if ris_path:
        print(f"\n  >> Import into Zotero:")
        print(f"     {ris_path}")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
    print()


if __name__ == "__main__":
    main()
