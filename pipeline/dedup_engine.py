"""7-rule deduplication engine for References against a MasterList."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import Reference, DeduplicationResult
from .master_list import (
    _fp_doi,
    _fp_eid,
    _fp_scopus_id,
    _fp_pmid,
    _fp_isbn,
    _fp_title_year,
    _fp_title_author,
)

if TYPE_CHECKING:
    from .master_list import MasterList

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Priority-ordered fingerprint builders (Rule 1..7)
# ---------------------------------------------------------------------------

_RULE_BUILDERS = [
    ("doi",          lambda r: [_fp_doi(r.doi)]),
    ("eid",          lambda r: [_fp_eid(r.scopus_eid)]),
    ("scopus_id",    lambda r: [_fp_scopus_id(r.scopus_id)]),
    ("pmid",         lambda r: [_fp_pmid(r.pmid)]),
    ("isbn",         lambda r: [_fp_isbn(r.isbn)]),
    ("title_year",   lambda r: [_fp_title_year(r.title, r.year)]),
    ("title_author", lambda r: [
        _fp_title_author(r.title, r.authors[0] if r.authors else "")
    ]),
]


def deduplicate_references(
    references: list[Reference],
    master_list: "MasterList",
) -> DeduplicationResult:
    """Check each reference against the master list and against each other.

    Deduplication rules (priority order):
      1. DOI exact match
      2. Scopus EID exact match
      3. Scopus ID exact match
      4. PMID exact match
      5. ISBN exact match
      6. Normalised title + year
      7. Normalised title + first author last name

    A reference is considered a duplicate if ANY rule matches.
    The first matching rule is logged for diagnostics.
    """
    result = DeduplicationResult(total_input=len(references))

    # Fingerprints from the master list (already built on load)
    ml_cache = master_list._get_cache()

    # Fingerprints seen within this batch (to catch cross-reference duplicates)
    batch_seen: dict[str, int] = {}  # fingerprint → index in result.new_references

    for ref in references:
        matched_fp = ""
        matched_rule = ""
        duplicate_of = ""

        for rule_name, fp_fn in _RULE_BUILDERS:
            fps = [f for f in fp_fn(ref) if f]
            for fp in fps:
                if fp in ml_cache:
                    matched_fp = fp
                    matched_rule = rule_name
                    duplicate_of = "master_list"
                    break
                if fp in batch_seen:
                    matched_fp = fp
                    matched_rule = rule_name
                    duplicate_of = f"batch[{batch_seen[fp]}]"
                    break
            if matched_fp:
                break

        if matched_fp:
            result.duplicates.append({
                "title": ref.title[:80],
                "year": ref.year,
                "doi": ref.doi,
                "scopus_eid": ref.scopus_eid,
                "matched_rule": matched_rule,
                "matched_fingerprint": matched_fp,
                "duplicate_of": duplicate_of,
            })
            log.debug(
                "DUPLICATE [%s] '%s' — %s matched: %s",
                matched_rule, ref.title[:60], duplicate_of, matched_fp,
            )
        else:
            # Register all fingerprints in batch_seen
            for _, fp_fn in _RULE_BUILDERS:
                for fp in [f for f in fp_fn(ref) if f]:
                    if fp not in batch_seen:
                        batch_seen[fp] = len(result.new_references)

            result.new_references.append(ref)

    result.new_count = len(result.new_references)
    result.duplicate_count = len(result.duplicates)

    log.info(
        "Deduplication: %d total → %d new, %d duplicates.",
        result.total_input, result.new_count, result.duplicate_count,
    )
    return result
