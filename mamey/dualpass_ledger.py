"""dualpass_ledger.py — cross-model reproducibility tooling (roadmap #8).

FREEZE-SAFE ADDITIVE TOOLING. Merges two independently-derived CLAIMS_LEDGER.tsv files
(e.g. Claude's vs Codex's pass over the same task) into a divergence table, after
normalising each ledger's free-text ``value`` to a canonical enum (``data/claims_vocab.json``)
so the merge shows REAL agreement instead of lexical noise. Emits a DIVERGENCE table with
AGREE / DISAGREE / *_ONLY labels + a deterministic auto-adjudication column.

Touches NO scan/scorer/tier/gate — it operates on two ledger files and writes new files.
Class-level; reconcile/render only; judgment deferred. Proven on the 2026-07-29 dual-pass:
macrolide pks_category 430/430 AGREE; RiPP subclass 0->367 AGREE after enum.
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
import json
import os
import re
import sys
import collections
from pathlib import Path
from typing import Any, Callable

# whole-strain excludes + claim-ceiling forbidden assertion types (same policy as the reference impl).
# SSOT: raw-data module -> raw_analysis_excluded() = {AS-XXX, AS-XXX}. See OFFICIAL_DATA/EXCLUSIONS.md.
from .exclusions import raw_analysis_excluded
EXCLUDE_STRAINS = raw_analysis_excluded()
FORBIDDEN_ASSERTIONS = {"product_identity", "ani", "organism", "species", "measured_activity"}
KEY = ("task", "strain", "bgc_id", "locus_tag", "assertion_type")


# ---- vocabulary ------------------------------------------------------------------------------------
def _vocab_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "claims_vocab.json"


def load_vocab(path: str | os.PathLike | None = None) -> dict[str, Any]:
    p = Path(path) if path else _vocab_path()
    return json.loads(Path(p).read_text(encoding="utf-8")).get("assertion_types", {})


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def normalize_value(assertion_type: str, value: str, vocab: dict[str, Any]) -> str:
    """Canonicalise a ledger value for one assertion type via claims_vocab.json ordered rules, plus
    the two compound tests the JSON can't express as a single substring (documented `_note_special`)."""
    # v9.7.371 fix: claims_vocab.json keys are lowercase; normalize the lookup so a differently-
    # cased assertion_type (LLM-authored free text) doesn't silently skip canonicalization.
    # v9.7.374 fix: the v9.7.371 fix only normalized the vocab *lookup* key (line below) — the two
    # compound special-case comparisons further down still compared against the raw, un-lowered
    # `assertion_type` parameter, so a differently-cased value (e.g. "Ripp_Subclass"/"Lead_Flag")
    # silently skipped both compound tests and fell through to the plain JSON substring rules,
    # which for lead_flag has no negation guard at all — "not a lead" canonicalized to "lead".
    # Reuse the SAME lowered/stripped value for the lookup and the compound tests below.
    atype = (assertion_type or "").strip().lower()
    spec = vocab.get(atype)
    if not spec:
        return value
    s = (value or "").lower().strip()
    # compound special cases (kept in code, flagged in the JSON _note_special) -----------------------
    if atype == "ripp_subclass":
        if ("azol" in s and "ripp" in s) or re.search(r"\blap\b", s):
            return "thiopeptide_azole"
    if atype == "lead_flag":
        # negation gates everything: "not a lead" must never hit the substring "lead" rule below
        if "not" in s:
            return "not_lead"
        if "lead" in s:
            return "lead"
    # ordered substring rules -------------------------------------------------------------------------
    for sub, canon in spec.get("rules", []):
        if sub in s:
            return canon
    # default -----------------------------------------------------------------------------------------
    default = spec.get("default", "passthrough")
    if default == "slugify":
        return _slugify(s)
    return value  # passthrough


def normalize_ledger(path: str | os.PathLike, vocab: dict[str, Any] | None = None) -> str:
    """Write a *_norm.tsv copy of a ledger with `value` canonicalised. Originals untouched."""
    vocab = vocab if vocab is not None else load_vocab()
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if not rows:
        return str(path)
    for d in rows:
        d["value"] = normalize_value(d.get("assertion_type", ""), d.get("value", ""), vocab)
    out = str(path).replace(".tsv", "_norm.tsv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        for d in rows:
            w.writerow(d)
    return out


# ---- merge ------------------------------------------------------------------------------------------
def _load(path: str | os.PathLike | None) -> dict[tuple, dict]:
    if not path or not os.path.exists(path):
        return {}
    out: dict[tuple, dict] = {}
    with open(path, encoding="utf-8") as fh:
        for d in csv.DictReader(fh, delimiter="\t"):
            # v9.7.371 fix: normalize the two case-sensitive-risk fields BEFORE building the join
            # key. strain/assertion_type are LLM-authored free text (two independent passes, e.g.
            # Claude vs Codex, over the same task) -- a differently-cased value on either side
            # both fragments the join (a real match reads as CLAUDE_ONLY/CODEX_ONLY instead of
            # AGREE/DISAGREE) AND, more seriously, can silently bypass the FORBIDDEN_ASSERTIONS
            # claim-ceiling guard below ("Organism" vs "organism" never matches the lowercase
            # forbidden-set membership check).
            if "strain" in d:
                d["strain"] = (d.get("strain") or "").strip().upper()
            if "assertion_type" in d:
                d["assertion_type"] = (d.get("assertion_type") or "").strip().lower()
            out[tuple(d.get(c, "").strip() for c in KEY)] = d
    return out


def _has_denominator(evidence: str) -> bool:
    e = (evidence or "").lower()
    return any(t in e for t in ("/", " of ", "over", "coverage", "denom", "n="))


def _auto_rule(k, cl, cx, miscalls: set[tuple[str, str]]) -> str:
    task, strain, bgc_id, locus, atype = k
    if strain in EXCLUDE_STRAINS:
        return "VOID:excluded-strain"
    if atype in FORBIDDEN_ASSERTIONS:
        return "REJECT:claim-ceiling(identity/ANI/organism/activity out of bounds)"
    if atype in ("novelty", "reference_dark_priority") and (strain, bgc_id) in miscalls:
        return "RULE:miscall-beats-novelty -> MISCALL_NON_SM_EXCLUDED"
    if atype.startswith("nr"):
        cle = (cl or {}).get("evidence", "").lower()
        cxe = (cx or {}).get("evidence", "").lower()
        if "_clustered" in cle or "clusterednr" in cle:
            return "RULE:claude nr-claim cites ClusteredNR (downgrade; ClusteredNR!=nr)"
        if "_clustered" in cxe or "clusterednr" in cxe:
            return "RULE:codex nr-claim cites ClusteredNR (downgrade; ClusteredNR!=nr)"
    for side in (cl, cx):
        if side and "%" in side.get("value", "") and not _has_denominator(side.get("evidence", "")):
            return "ESCALATE:metric missing denominator"
    return ""


def _load_miscalls(miscall_file: str | os.PathLike | None) -> set[tuple[str, str]]:
    subs: set[tuple[str, str]] = set()
    if miscall_file and os.path.exists(miscall_file):
        with open(miscall_file, encoding="utf-8") as fh:
            for d in csv.DictReader(fh, delimiter="\t"):
                s = d.get("strain", "").strip()
                b = d.get("bgc_id", "").strip()
                if s and b:
                    subs.add((s, b))
    return subs


def merge(claude_path, codex_path, out_dir=None, normalize=True, miscall_file=None) -> dict[str, Any]:
    """Merge two ledgers into DIVERGENCE.tsv. If normalize, canonicalise both first via claims_vocab."""
    vocab = load_vocab()
    cl_p, cx_p = str(claude_path), str(codex_path)
    if normalize:
        cl_p = normalize_ledger(cl_p, vocab)
        cx_p = normalize_ledger(cx_p, vocab)
    claude, codex = _load(cl_p), _load(cx_p)
    outd = os.path.abspath(out_dir or os.path.dirname(str(claude_path)) or ".")
    os.makedirs(outd, exist_ok=True)
    miscalls = _load_miscalls(miscall_file)

    rows = []
    counts: collections.Counter = collections.Counter()
    for k in sorted(set(claude) | set(codex)):
        cl, cx = claude.get(k), codex.get(k)
        if cl and cx:
            status = "AGREE" if cl.get("value", "").strip() == cx.get("value", "").strip() else "DISAGREE"
        else:
            status = "CLAUDE_ONLY" if cl else "CODEX_ONLY"
        rule = _auto_rule(k, cl, cx, miscalls)
        counts[status] += 1
        if rule:
            counts["auto_resolved"] += 1
        rows.append({
            "task": k[0], "strain": k[1], "bgc_id": k[2], "locus_tag": k[3], "assertion_type": k[4],
            "claude_value": (cl or {}).get("value", ""), "codex_value": (cx or {}).get("value", ""),
            "claude_evidence": (cl or {}).get("evidence", ""), "codex_evidence": (cx or {}).get("evidence", ""),
            "claude_conf": (cl or {}).get("confidence", ""), "codex_conf": (cx or {}).get("confidence", ""),
            "status": status, "auto_resolution": rule,
            "needs_discussion": "yes" if (status in ("DISAGREE", "CLAUDE_ONLY", "CODEX_ONLY") and not rule) else "no",
        })
    out = os.path.join(outd, "DIVERGENCE.tsv")
    cols = ["task", "strain", "bgc_id", "locus_tag", "assertion_type", "claude_value", "codex_value",
            "claude_evidence", "codex_evidence", "claude_conf", "codex_conf", "status",
            "auto_resolution", "needs_discussion"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        fh.write("# Dual-pass divergence (freeze-safe additive tooling). Reconciliation only; no scoring; "
                 "judgment deferred. Values canonicalised via claims_vocab.json when --normalize.\n")
        w = _SafeDictWriter(fh, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return {"status": "ok", "claims": len(rows), "AGREE": counts.get("AGREE", 0),
            "DISAGREE": counts.get("DISAGREE", 0), "CLAUDE_ONLY": counts.get("CLAUDE_ONLY", 0),
            "CODEX_ONLY": counts.get("CODEX_ONLY", 0), "auto_resolved": counts.get("auto_resolved", 0),
            "needs_discussion": sum(1 for r in rows if r["needs_discussion"] == "yes"), "out": out}


def dualpass_command(args) -> int:
    # v9.7.409 (AUDIT_cli_edgecases): existence guard before normalize_ledger's open(path). A
    # mistyped ledger path used to crash with a raw FileNotFoundError; refuse cleanly instead.
    for _label, _p in (("claude", args.claude), ("codex", args.codex)):
        if not Path(_p).is_file():
            emit(f"ERROR: dualpass {_label} ledger not found: {_p}", file=sys.stderr)
            return 1
    res = merge(args.claude, args.codex, getattr(args, "out", None),
                normalize=not getattr(args, "no_normalize", False),
                miscall_file=getattr(args, "miscalls", None))
    emit(f"dualpass: {res['claims']} claims | AGREE {res['AGREE']} DISAGREE {res['DISAGREE']} CLAUDE_ONLY {res['CLAUDE_ONLY']} CODEX_ONLY {res['CODEX_ONLY']}", f"  auto-resolved by rule: {res['auto_resolved']} | need discussion: {res['needs_discussion']}", sep="\n")
    emit("  ->", res["out"])
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Merge two engine CLAIMS_LEDGER.tsv into a divergence table")
    ap.add_argument("claude", help="Claude ledger .tsv")
    ap.add_argument("codex", help="Codex ledger .tsv")
    ap.add_argument("--out", default=None, help="output dir (default: alongside the Claude ledger)")
    ap.add_argument("--no-normalize", action="store_true", help="skip claims_vocab canonicalisation")
    ap.add_argument("--miscalls", default=None, help="optional miscall registry TSV (strain,bgc_id)")
    a = ap.parse_args()
    raise SystemExit(dualpass_command(a))
