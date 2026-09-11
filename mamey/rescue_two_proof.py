"""rescue_two_proof.py — the CORE join: RG-GMCI (_4A, reference-based) × KS-clade (_4B, reference-free).

This is where the fragment-rescue channels become an adjudicable VERDICT. It emits
`{strain}_4D_two_proof_rescue.csv`: for every contig pair, whether the two orthogonal proofs AGREE.

the review lane's two-proof rule (C06), operationalized:
  * RG-GMCI logic proof present  = rggmci_confidence in {HIGH_RG_GMCI_RESCUE, MODERATE_RG_GMCI_CANDIDATE}
        AND functional_rescue_class != ACCESSORY_ONLY
        AND (functional_rescue_class == 'COMPLEMENTARY'
             OR (complementary_disjoint_refs >= 3 AND overlapping_subject_refs == 0))  # .377
  * KS-clade proof present       = the pair's two contigs co-occur in one _4B cross-contig KS_CLADE_LINK clade
  * VERDICT:
      TWO_PROOF_RESCUE   both proofs present  -> corroborated candidate (strongest; for human adjudication)
      MULTI_CHANNEL_HOLD RG-GMCI ranked HIGH/MODERATE but complementarity proof NOT met, AND KS-clade present
                         -> two HOMOLOGY channels concordant, complementarity still owed -> advisory HOLD, NOT a rescue
      RGGMCI_ONLY        logic proof only     -> tailoring/NRPS rescue KS can't see (e.g. no shared KS)
      KS_CLADE_ONLY      KS proof only, reference-DARK -> RG-GMCI never ranked the pair (surface it!)
      WEAK               neither clears its bar

MULTI_CHANNEL_HOLD (.368, Mango Tango RFC KS_PHYLO_MULTI_CHANNEL_RESCUE, ruled by BOTH lane owners 2026-08-17):
the review lane (two-proof): RG-GMCI homology + KS-clade homology is proof-1 + proof-1 (a STRONGER homology signal),
NOT proof-1 + independent proof-2. So a pair the RG-GMCI channel ranked HIGH/MODERATE but that FAILED the
complementarity (logic) proof, and which the KS channel independently groups, is exactly "two homology channels
agree these fragments are related, but the independent COMPLEMENTARY_SPLIT proof is still owed." That is a HOLD,
never a promotion: MULTI_CHANNEL_HOLD is a pure advisory SURFACER — it feeds NO score, rank, or prior, and it
does NOT promote to TWO_PROOF_RESCUE. COMPLEMENTARY_SPLIT (the `_logic_proof` gate) remains the SOLE gate for
any rescue. This verdict is engine-NEUTRAL: `_4D_two_proof_rescue.csv` is not in packaging.py::DETERMINISM_WHITELIST,
so it never moves the repro fingerprint. Amber (`_4B` owner): the KS-clade partition it reads is unchanged —
`_4B` is byte-identical, its subtype partition and pairwise-UNCLASSIFIED policy intact — so this adds no
cross-subtype bridge. AS-XXX chimera control (2026-08-17): the in-engine KS channel is 5-mer containment
single-linkage (subtype-gated, UNCLASSIFIED pairwise), NOT an "any shared ancestor UFBoot>=80" tree query, so
the naive-backbone false-positive that control warned about cannot arise here by construction.

A verdict is a CANDIDATE for adjudication, NEVER a merge or a nucleotide join. Judgment deferred; the Developer or User seals;
the review lane adjudicates. Deterministic; reads existing artifacts; never fails the core run.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os
import re

HIGH = {"HIGH_RG_GMCI_RESCUE", "MODERATE_RG_GMCI_CANDIDATE"}


def _short(contig):
    m = re.search(r"(NODE_\d+)", contig or "")
    return m.group(1) if m else (contig or "")


def _clade_index(scan):
    """map short-contig -> set of clade_ids it belongs to (from a run_pks_ks_scan result)."""
    idx = {}
    for c in scan.get("cross_contig_clades", []):
        for ct in c["contigs"]:
            idx.setdefault(_short(ct), set()).add(c["clade_id"])
    return idx


def _logic_proof(row):
    conf = (row.get("rggmci_confidence") or "").strip()
    frc = (row.get("functional_rescue_class") or "").strip()
    if conf not in HIGH:
        return False
    if frc == "ACCESSORY_ONLY":
        return False
    if frc == "COMPLEMENTARY":
        return True
    try:
        cdr = int(float(row.get("complementary_disjoint_refs") or 0))
    except ValueError:
        cdr = 0
    # AUDIT_377: the complementary_disjoint_refs fallback (for a frc that didn\'t clear
    # COMPLEMENTARY, e.g. BOTH_CORE/AMBIGUOUS) is only genuine complementarity evidence when
    # UNCONTRADICTED. cd and overlapping_subject_refs come from the SAME rggmci.py subject-tiling
    # accumulator (Phase 4) -- and that module\'s own subject_tiling_verdict computation already
    # demotes cd>=1-AND-ov>=1 to MIXED_SUBJECT_SIGNAL (never a clean COMPLEMENTARY_SPLIT) for
    # exactly this reason: a pile of co-present overlapping/paralogous subject hits means the two
    # contigs also look like duplicate copies of the SAME machinery, not solely disjoint halves of
    # one pathway. A raw cdr>=3 count that ignores that contradiction would grant this proof from
    # data the module that computed it has already flagged as ambiguous (real cohort case, .368
    # AS-XXX BGC014+BGC033: cd=6 but ov=22 -- a 22:6 paralogy-dominant signal -- subject_tiling_verdict
    # MIXED_SUBJECT_SIGNAL, yet the unfixed cdr>=3 check alone still returned True).
    try:
        ov = int(float(row.get("overlapping_subject_refs") or 0))
    except ValueError:
        ov = 0
    return cdr >= 3 and ov == 0


def two_proof_join(rggmci_4a_csv, ks_scan):
    """Return (rows, summary). rows = list of dicts for _4D. ks_scan = run_pks_ks_scan result."""
    cidx = _clade_index(ks_scan)
    rows = []
    counts = {"TWO_PROOF_RESCUE": 0, "MULTI_CHANNEL_HOLD": 0, "RGGMCI_ONLY": 0, "KS_CLADE_ONLY": 0, "WEAK": 0}
    seen_pairs = set()
    # 1) walk RG-GMCI ranked pairs
    if rggmci_4a_csv and os.path.exists(rggmci_4a_csv):
        with open(rggmci_4a_csv, newline="") as fh:
            for row in csv.DictReader(fh):
                ca, cb = _short(row.get("contig_a")), _short(row.get("contig_b"))
                seen_pairs.add(frozenset((ca, cb)))
                logic = _logic_proof(row)
                conf = (row.get("rggmci_confidence") or "").strip()
                shared = cidx.get(ca, set()) & cidx.get(cb, set())
                ks = bool(shared)
                if logic and ks:
                    v = "TWO_PROOF_RESCUE"
                elif logic:
                    v = "RGGMCI_ONLY"
                elif ks and conf in HIGH:
                    # .368: RG-GMCI ranked this pair HIGH/MODERATE but the complementarity (logic) proof did
                    # NOT clear, and the KS channel independently groups it -> two homology channels concordant,
                    # complementarity still owed. Advisory HOLD, never a rescue (surfacer only). This is the
                    # subset previously mislabeled KS_CLADE_ONLY even though RG-GMCI DID rank the pair.
                    v = "MULTI_CHANNEL_HOLD"
                elif ks:
                    v = "KS_CLADE_ONLY"
                else:
                    v = "WEAK"
                counts[v] += 1
                rows.append({
                    "contig_a": ca, "contig_b": cb, "verdict": v,
                    "rggmci_confidence": (row.get("rggmci_confidence") or "").strip(),
                    "rggmci_score": (row.get("rggmci_score") or "").strip(),
                    "functional_rescue_class": (row.get("functional_rescue_class") or "").strip(),
                    "ks_clade_id": ";".join(sorted(shared)) if shared else "",
                    "bgc_a": (row.get("bgc_a") or "").strip(), "bgc_b": (row.get("bgc_b") or "").strip(),
                })
    # 2) KS-clade links RG-GMCI never ranked (reference-dark) -> KS_CLADE_ONLY
    for c in ks_scan.get("cross_contig_clades", []):
        conts = [_short(x) for x in c["contigs"]]
        for i in range(len(conts)):
            for j in range(i + 1, len(conts)):
                fp = frozenset((conts[i], conts[j]))
                if fp in seen_pairs:
                    continue
                seen_pairs.add(fp)
                counts["KS_CLADE_ONLY"] += 1
                rows.append({
                    "contig_a": conts[i], "contig_b": conts[j], "verdict": "KS_CLADE_ONLY",
                    "rggmci_confidence": "", "rggmci_score": "", "functional_rescue_class": "",
                    "ks_clade_id": c["clade_id"], "bgc_a": "", "bgc_b": "",
                })
    summary = (f"two-proof rescue: {counts['TWO_PROOF_RESCUE']} TWO_PROOF, "
               f"{counts['MULTI_CHANNEL_HOLD']} MULTI_CHANNEL_HOLD (2 homology channels, complementarity owed), "
               f"{counts['KS_CLADE_ONLY']} KS-only (reference-dark), {counts['RGGMCI_ONLY']} RGGMCI-only. "
               f"Candidates for adjudication — not merges. Judgment deferred.")
    return rows, summary, counts


TWO_PROOF_LOGIC_VERSION = "2"  # .368: +MULTI_CHANNEL_HOLD advisory verdict (surfacer-only). bump on gate change.
_INTERP = {
    "TWO_PROOF_RESCUE": "complementary two-proof candidate (RG-GMCI logic + KS-clade homology)",
    "MULTI_CHANNEL_HOLD": ("two homology channels concordant (RG-GMCI HIGH/MODERATE + KS-clade), complementarity "
                           "proof NOT met — advisory HOLD, NOT a rescue; COMPLEMENTARY_SPLIT still required"),
    "KS_CLADE_ONLY": "reference-dark KS-clade link (surface for adjudication)",
    "RGGMCI_ONLY": "logic-only rescue (no shared KS clade)",
    "WEAK": "below both bars",
}


def write_4d_csv(rows, out_path, strain_id=""):
    cols = ["strain", "contig_a", "contig_b", "verdict", "interpretation", "rggmci_confidence", "rggmci_score",
            "functional_rescue_class", "ks_clade_id", "bgc_a", "bgc_b", "two_proof_logic_version", "claim_note"]
    note = ("two-proof candidate for adjudication; homology-guided linkage, NOT a merge or nucleotide join; "
            "the review lane adjudicates; judgment deferred")
    order = {"TWO_PROOF_RESCUE": 0, "MULTI_CHANNEL_HOLD": 1, "KS_CLADE_ONLY": 2, "RGGMCI_ONLY": 3, "WEAK": 4}
    # AUDIT_374: write to a sibling .tmp then os.replace into place, so a crash mid-write
    # (this is a real production-invoked deliverable write from cli.py::_write_package(), called
    # inside a bare try/except that swallows the exception) never leaves _4D_two_proof_rescue.csv
    # truncated-but-present on disk with no signal that anything went wrong. Self-contained (no
    # cross-module import) because this file also runs standalone (see __main__ below), where a
    # relative `.packaging` import would fail.
    out_path = str(out_path)
    tmp = out_path + ".tmp"
    try:
        with open(tmp, "w", newline="") as fh:
            w = _SafeDictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in sorted(rows, key=lambda x: order.get(x["verdict"], 9)):
                r2 = dict(r); r2["strain"] = strain_id; r2["claim_note"] = note
                r2["interpretation"] = _INTERP.get((r2.get("verdict") or "").strip(), "")
                r2["two_proof_logic_version"] = TWO_PROOF_LOGIC_VERSION
                w.writerow(r2)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, out_path)
    return out_path


if __name__ == "__main__":  # standalone: python rescue_two_proof.py <_4A.csv> <zip> [strain]
    import sys, json
    from pks_ks_scan import run_pks_ks_scan
    a4, zp = sys.argv[1], sys.argv[2]
    sid = sys.argv[3] if len(sys.argv) > 3 else "?"
    scan = run_pks_ks_scan(zp)
    rows, summary, counts = two_proof_join(a4, scan)
    emit(summary, json.dumps(counts, indent=2), sep="\n")
    for r in rows:
        if r["verdict"] in ("TWO_PROOF_RESCUE", "KS_CLADE_ONLY"):
            emit(r["verdict"], r["contig_a"], r["contig_b"], r["rggmci_confidence"],
                  r["functional_rescue_class"], r["ks_clade_id"])
