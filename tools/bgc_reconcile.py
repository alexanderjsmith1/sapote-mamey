#!/usr/bin/env python3
"""bgc_reconcile.py — pre-authoring cross-channel evidence reconciliation ledger.

The missing step between `mamey emit-modeb-template` (which seeds a BGC's facts) and a
human/Sapote authoring §4 (independent homology) and §8 (KCB corroboration). The engine
already computes every contradiction signal an author needs — but they live scattered
across the triage board (Class_Conf, Misanchor_Flag, Two_Pathway_Flag, Two_Model_Flag,
Concordance, Primary_metab_flag, Boundary, KCB_top/KCB_score) plus the reclass
domain-discrepancy pass. Nothing pulls them into one place, so each card re-does the
reconciliation by hand and the "read the front page first, reconcile the channels"
discipline (Sapote_Mamey_ROADMAP.md) is a rule to remember rather than a rendered artifact.
This tool renders it: per BGC, the channels present, the reconciled class call, an explicit
CONTRADICTIONS-TO-RESOLVE checklist, and the claim ceiling. Each contradiction also carries a
runnable NEXT-ACTION naming the real resolution tool — OVER_MERGE → tools/scope_cluster.py,
CLASS_DISCREPANCY → mamey hmm-adjudicate, KCB_NOT_IDENTITY → fetch_reference_cluster +
cluster_gene_compare, KCB_TIER_UNVERIFIED → mamey kcb-frontpage — with the region GBK path
resolved when --strain-dir is supplied, so the ledger is self-navigating.

WHAT IT IS FOR (honest scope): a REVIEW LEDGER, not a verdict engine. It does not decide the
product class, run BLASTp, or overturn antiSMASH. It surfaces where the channels already in
the package disagree and states what must be resolved (and how) before a claim is authored.
The three online/offline homology channels (BLASTp / HMM) are named as required author steps,
never fabricated here.

CLOSING THE LOOP (--verify-card): after authoring, re-run with --verify-card <card.md> --bgc <ID>
to check the card acknowledges every BLOCK contradiction the ledger raised for that BGC. This
catches the failure the generic Mode B gates cannot see — a structurally-clean card that silently
ignores an OVER_MERGE / CLASS_DISCREPANCY flag. It detects silent omission, not semantic
correctness; a human still confirms the resolution is right.

CLAIM DISCIPLINE (hard):
  - Every finding is a REVIEW PROMPT, never a reclassification verdict and never a phenotype.
  - Capacity language only ("machinery consistent with", never "produces").
  - KCB / BLASTp = similarity, not identity. A KCB hit is a lead to check, not a verdict.
  - When supplied, bioactivity metadata provides strain-level context, never per-BGC content without governed linkage.
  - BGCs cited by node·region; provenance tagged [store-backed] (sealed-package artifacts).

REUSES (does not reinvent):
  - tools/reclass_check.analyze()             — domain-vs-label class discrepancy
  - tools/reclass_discriminating_domains.json — the curated discriminating-domain map
  - mamey.kcb_frontpage._corroboration_tier() — KCB similarity+gene-count → tier (when a raw
                                                antiSMASH dir is supplied via --strain-dir)
  - tools/claim_safety_linter.lint_claim_safety() — self-lint of emitted narrative

Store-backed inputs (all already in a sealed Mamey package):
  <package>/*_4_triage_board.csv
  <package>/*gene_by_gene_all_bgcs.csv     (via reclass)
Optional:
  --strain-dir <raw antiSMASH dir>         to compute the KCB corroboration tier in-line

No network. Deterministic.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, os, csv, glob, json, argparse, re
from pathlib import Path


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))  # bundle root, for `import mamey`
from _wbio import atomic_write_text

# ── reused logic ────────────────────────────────────────────────────────────
try:
    from reclass_check import analyze as _reclass_analyze
except Exception:  # pragma: no cover - reclass always ships alongside
    _reclass_analyze = None
try:
    from claim_safety_linter import lint_claim_safety as _lint
except Exception:  # pragma: no cover
    _lint = None
try:
    from mamey.kcb_frontpage import _corroboration_tier as _kcb_tier
except Exception:  # pragma: no cover - optional; only used with --strain-dir
    _kcb_tier = None


def _find(pkg, suffix):
    m = glob.glob(f"{pkg}/*{suffix}")
    return m[0] if m else None


def _rows(path):
    if not path:
        return []
    return list(csv.DictReader(open(path, encoding="utf-8", errors="replace")))


def _load_over_merge(pkg):
    """Aggregate *_predicted_polymers.csv per region into the antiSMASH-native over-merge signal.

    Returns {region_number:int -> {n_protoclusters:int, kinds:str, flag:bool}}. A region is
    flagged when ANY of its protocluster rows carries over_merge_flag starting 'YES'. This is
    antiSMASH's own 'region = >=2 BGCs' call (neighbouring / chemical_hybrid candidate kinds) —
    computed by the engine but not carried on the triage board, so authors never see it.
    """
    p = _find(pkg, "predicted_polymers.csv")
    if not p:
        return {}
    agg = {}
    for row in _rows(p):
        try:
            rn = int(float(row.get("region_number", "") or 0))
        except (ValueError, TypeError):
            continue
        flag = (row.get("over_merge_flag", "") or "").strip().upper().startswith("YES")
        try:
            npc = int(float(row.get("n_protoclusters", "") or 0))
        except (ValueError, TypeError):
            npc = 0
        kind = (row.get("candidate_kind", "") or "").strip()
        cur = agg.setdefault(rn, {"n_protoclusters": 0, "kinds": set(), "flag": False})
        cur["flag"] = cur["flag"] or flag
        cur["n_protoclusters"] = max(cur["n_protoclusters"], npc)
        for k in kind.split("|"):
            if k and k != "single":
                cur["kinds"].add(k)
    return {rn: {"n_protoclusters": v["n_protoclusters"],
                 "kinds": ", ".join(sorted(v["kinds"])) or "neighbouring",
                 "flag": v["flag"]} for rn, v in agg.items()}


def _locator(r):
    node = r.get("Node_ID", "") or r.get("Contig", "")
    reg = (r.get("antiSMASH_Region", "") or "").replace("region", "r")
    return f"{r.get('BGC_ID', '?')} ({node} · {reg})"


def _f(r, key):
    return (r.get(key, "") or "").strip()


def _norm_compound(s):
    """Normalize a KCB compound name for joining frontpage hits to triage KCB_top.

    Handles the triage 'BGC0000116.5 | nystatin-like ... | known 78%' layout (drop the
    MIBiG accession + similarity metadata, keep the compound) and returns a 14-char
    alphanumeric key tolerant of trailing-suffix / truncation differences.
    """
    if not s:
        return ""
    import re as _re
    parts = [p.strip() for p in str(s).split("|")]
    cand = ""
    for p in parts:
        pl = p.lower()
        if pl.startswith("bgc0") or "%" in p or pl.startswith("known") or pl.startswith("similar"):
            continue
        if p:
            cand = p
            break
    if not cand:
        cand = parts[0] if parts else str(s)
    return _re.sub(r"[^a-z0-9]", "", cand.lower())[:14]


# ── contradiction detectors ─────────────────────────────────────────────────
# Each returns a dict {code, severity, channel, evidence, section, resolve} or None.
# severity: BLOCK (must resolve before any class/identity claim) | WATCH (constrains wording).

def _c_class_conf(r):
    conf = _f(r, "Class_Conf").upper()
    if conf in ("LOW",):
        return dict(
            code="LOW_CLASS_CONFIDENCE", severity="BLOCK", channel="antiSMASH arch",
            evidence=f"Class_Conf={conf}",
            section="§1/§6",
            resolve="Do not assert a single product class. Frame the class as capacity / "
                    "unresolved and lead with the architecture, not the antiSMASH product label.",
        )
    return None


def _c_reclass(finding):
    # finding: {kind, cls, present}
    kind = finding["kind"]
    cls = finding["cls"]
    present = ", ".join(finding.get("present", [])) or "(none)"
    if kind == "undeclared_strong":
        return dict(
            code="CLASS_DISCREPANCY:undeclared", severity="BLOCK", channel="domain vs label",
            evidence=f"discriminating domains for '{cls}' present ({present}) but not in antiSMASH label",
            section="§1/§6",
            resolve=f"Resolve whether this is a '{cls}' capacity the label missed before naming a "
                    f"product class; domain presence is a similarity-level signal, not a reclass verdict.",
        )
    if kind == "label_unsupported":
        return dict(
            code="CLASS_DISCREPANCY:label_unsupported", severity="BLOCK", channel="domain vs label",
            evidence=f"antiSMASH label '{cls}' lacks its own diagnostic domain (found: {present})",
            section="§1/§6",
            resolve=f"The '{cls}' label is not corroborated by its discriminating domain — do not "
                    f"carry the label into the class call without an independent check.",
        )
    if kind == "thiopeptide_upgrade":
        return dict(
            code="CLASS_DISCREPANCY:thiopeptide", severity="WATCH", channel="domain vs label",
            evidence=f"azole-RiPP label + thiopeptide RRE ({present})",
            section="§6",
            resolve="Consider the thiopeptide refinement of the RiPP call; state as capacity.",
        )
    return None


def _c_kcb(r, kcb_tier):
    anchor = _f(r, "KCB_top") or _f(r, "KCB_clusterblast")
    score = _f(r, "KCB_score")
    if not anchor:
        return None  # KCB-dark: handled by claim ceiling, not a contradiction
    tier = (kcb_tier or "").upper()
    if tier in ("STRONG",):
        return None  # a STRONG anchor is a checkable lead, not a contradiction
    if tier in ("COINCIDENTAL", "LARGE_GENERIC"):
        return dict(
            code=f"KCB_NOT_IDENTITY:{tier}", severity="BLOCK", channel="KCB front page",
            evidence=f"anchor '{anchor}' (sim {score or '?'}%) graded {tier}",
            section="§8",
            resolve="This anchor must NOT be read as compound identity in §8 — a high similarity "
                    "with few matching genes is a coincidental/generic hit. State the tier explicitly.",
        )
    # tier unknown (no --strain-dir): force the front-page read rather than guess.
    return dict(
        code="KCB_TIER_UNVERIFIED", severity="WATCH", channel="KCB front page",
        evidence=f"anchor '{anchor}' (sim {score or '?'}%), corroboration tier not computed",
        section="§8",
        resolve="Run `mamey kcb-frontpage <strain_dir> --region <r>` and read the tier "
                "(STRONG / COINCIDENTAL / LARGE_GENERIC) before writing §8; do not equate score with identity.",
    )


def _c_two_pathway(r):
    v = _f(r, "Two_Pathway_Flag")
    if v:
        return dict(
            code="TWO_PATHWAY", severity="BLOCK", channel="gene-level",
            evidence=v, section="§2/§6",
            resolve="The region encodes >1 pathway — do not attribute one product to the whole "
                    "region; split the backbone claim by pathway block.",
        )
    return None


def _c_two_model(r):
    v = _f(r, "Two_Model_Flag")
    if v:
        sev = "BLOCK" if "KCB_DISCONNECT" in v or v.startswith("TWO_MODEL_STRONG") else "WATCH"
        return dict(
            code="TWO_MODEL", severity=sev, channel="decomposition",
            evidence=v, section="§2",
            resolve="antiSMASH may have over-merged two clusters — reconcile the region boundary "
                    "before any assembled-backbone or product claim.",
        )
    return None


def _c_misanchor(r):
    v = _f(r, "Misanchor_Flag")
    if v and v.upper() not in ("", "NONE", "OK", "FALSE", "0"):
        return dict(
            code="MISANCHOR", severity="BLOCK", channel="anchor QC",
            evidence=f"Misanchor_Flag={v}", section="§1/§28",
            resolve="The region anchor may be misplaced — verify every locus_tag cited against the "
                    "region GBK before authoring (guards against PHANTOM_LOCUS fabrication).",
        )
    return None


def _c_boundary(r):
    b = _f(r, "Boundary")
    if b in ("Edge", "Full-contig", "FC", "full-contig"):
        return dict(
            code="TRUNCATED_NO_STRUCTURE", severity="WATCH", channel="assembly",
            evidence=f"Boundary={b}", section="§2/§7",
            resolve="Cluster is truncated / on a contig edge — restrict claims to capacity only: no "
                    "assembled-polymer, mass, or structural claim. Recommend long-read finishing.",
        )
    return None


def _c_primary_metab(r):
    v = _f(r, "Primary_metab_flag")
    if v and v.upper() not in ("", "NONE", "FALSE", "0", "NO"):
        return dict(
            code="PRIMARY_METABOLISM", severity="WATCH", channel="primary-metab guard",
            evidence=f"Primary_metab_flag={v}", section="§6/§17",
            resolve="May be primary metabolism (e.g. SUF operon, geosmin) rather than a specialised-"
                    "metabolite lead — do not rank as an antimicrobial lead without corroboration.",
        )
    return None


def _c_concordance(r):
    v = _f(r, "Concordance")
    if v and v.upper() in ("LOW", "DISCORDANT", "FAIL"):
        return dict(
            code="LOW_CONCORDANCE", severity="WATCH", channel="fragment concordance",
            evidence=f"Concordance={v}", section="§2",
            resolve="Observed fragments disagree with the reference panel — treat RG-GMCI grouping "
                    "as provisional and flag the reconstruction as reconstructed, not store-backed.",
        )
    return None


def _region_gbk(strain_dir, record, region_no):
    """Resolve the antiSMASH region GBK path for scope_cluster/hmm-adjudicate commands.

    Returns a real path if strain_dir is given and the file exists, else a '<region_gbk>'
    placeholder so the emitted command is honest about what the author must supply.
    """
    import glob as _glob
    if strain_dir and record and region_no:
        cand = f"{strain_dir}/{record}.region{int(region_no):03d}.gbk"
        if os.path.exists(cand):
            return cand
        hits = _glob.glob(f"{strain_dir}/*region{int(region_no):03d}.gbk")
        if hits:
            return hits[0]
    return "<region_gbk>"


def _attach_actions(cx, r, strain_dir):
    """Set c['action'] = a runnable command per contradiction code, naming the REAL tool.

    Turns the ledger from 'here is the conflict' into 'here is the conflict AND the command
    that resolves it'. Region-GBK-consuming actions resolve the real path when strain_dir is
    supplied. The over-merge action points at tools/scope_cluster.py (the antiSMASH-boundary
    splitter, v9.7.303), the correct action for an OVER_MERGE / TWO_MODEL / TWO_PATHWAY region.
    """
    record = (r.get("Contig", "") or r.get("Node_ID", "") or "").strip()
    reg_raw = (r.get("antiSMASH_Region", "") or "").replace("region", "")
    try:
        reg_no = int(float(reg_raw)) if reg_raw else 0
    except (ValueError, TypeError):
        reg_no = 0
    gbk = _region_gbk(strain_dir, record, reg_no)
    products = _f(r, "Products")
    cats = " | ".join(p.strip() for p in re.split(r"[;,]", products) if p.strip()) or "<target-class>"
    kcb = _norm_compound(r.get("KCB_top", ""))
    for c in cx:
        code = c["code"]
        if code == "OVER_MERGE" or code.startswith("TWO_"):
            c["action"] = (f"python tools/scope_cluster.py --gbk {gbk} "
                           f"--category <{cats}> --outdir scoped/   # split, then one card per protocluster")
        elif code.startswith("KCB_TIER_UNVERIFIED"):
            c["action"] = (f"python -m mamey kcb-frontpage {strain_dir or '<strain_dir>'} "
                           f"--region r{reg_no}   # read STRONG / COINCIDENTAL / LARGE_GENERIC")
        elif code.startswith("KCB_NOT_IDENTITY"):
            c["action"] = ("python tools/fetch_reference_cluster.py --db anchored.db "
                           f"--acc <MIBiG>:{kcb or 'anchor'} --outdir refs/  &&  "
                           f"python tools/cluster_gene_compare.py {gbk} refs/*.gbk   # shared-gene overlap, not %")
        elif code.startswith("CLASS_DISCREPANCY"):
            c["action"] = (f"python -m mamey hmm-adjudicate {gbk} --locus <locus_tag>"
                           "   # settle label vs domain on the HMM signature")
        elif code == "MISANCHOR":
            c["action"] = (f"grep -c CDS {gbk}   # verify every cited locus_tag exists in the region GBK")
        else:
            c["action"] = None
    return cx


def _c_over_merge(r, over_merge_map):
    """antiSMASH's own 'this region is >=2 BGCs' signal (from predicted_polymers.csv)."""
    try:
        rn = int(float((r.get("antiSMASH_Region", "") or "").replace("region", "") or 0))
    except (ValueError, TypeError):
        return None
    om = over_merge_map.get(rn)
    if not om or not om.get("flag"):
        return None
    npc = om["n_protoclusters"]
    return dict(
        code="OVER_MERGE", severity="BLOCK", channel="antiSMASH protoclusters",
        evidence=f"region carries {npc} protoclusters (kind: {om['kinds']})",
        section="§2/§6",
        resolve=f"antiSMASH's own '>=2 BGCs' signal — this region is {npc} authoring units, not one. "
                f"Split into the constituent protoclusters before ANY product/backbone claim; do not "
                f"author a single composite Mode B card over the merged region.",
    )


# ── claim ceiling ────────────────────────────────────────────────────────────
def _claim_ceiling(r, kcb_tier):
    ceil = [
        "Capacity language only — 'biosynthetic machinery consistent with', never 'produces'.",
        "When supplied, bioactivity metadata provides strain-level context; never a per-BGC phenotype.",
    ]
    b = _f(r, "Boundary")
    if b in ("Edge", "Full-contig", "FC", "full-contig"):
        ceil.append(f"Boundary={b}: no assembled-polymer / mass / structural claim (cluster truncated).")
    anchor = _f(r, "KCB_top") or _f(r, "KCB_clusterblast")
    if not anchor:
        ceil.append("KCB-dark: no known-metabolite anchor — product identity is not established.")
    else:
        tier = (kcb_tier or "UNVERIFIED").upper()
        ceil.append(f"KCB anchor '{anchor}' — similarity-level (tier {tier}), not identity.")
    nov = _f(r, "Novelty_auto")
    if nov:
        ceil.append(f"Novelty_auto={nov} is an automated prompt, not a novelty verdict.")
    return ceil


# ── core (pure) ──────────────────────────────────────────────────────────────
def reconcile(pkg, bgc=None, strain_dir=None, cmap=None):
    """Return (ledger, summary). Pure; no printing.

    ledger: list of per-BGC dicts:
      {bgc_id, locator, label, arch, boundary, ab, af, kcb_tier,
       contradictions:[{code,severity,channel,evidence,section,resolve}],
       claim_ceiling:[...], n_block, n_watch}
    summary: {n_bgc, n_with_block, n_with_watch, codes:{code:count}, error?}
    """
    tb = _find(pkg, "4_triage_board.csv")
    if not tb:
        return [], {"error": "no *_4_triage_board.csv in package", "n_bgc": 0}

    over_merge_map = _load_over_merge(pkg)

    # reclass findings, keyed by bgc_id
    reclass_by_bgc = {}
    if _reclass_analyze is not None and cmap is not None:
        try:
            findings, _ = _reclass_analyze(pkg, cmap)
            reclass_by_bgc = {f["bgc_id"]: f["findings"] for f in findings}
        except Exception:
            reclass_by_bgc = {}

    # optional KCB tier per region (needs a raw antiSMASH dir + gene count).
    # The frontpage keys regions in antiSMASH r{rec}c{cand} notation while the triage board
    # uses Mamey's sequential region label — they do NOT map by index. Join on compound name,
    # which is stable across both (verified on Ae150A-Ps1: r1c1/region007 both = nystatin-like).
    kcb_tier_by_region = {}
    kcb_tier_by_compound = {}
    if strain_dir and _kcb_tier is not None:
        try:
            from mamey.kcb_frontpage import read_frontpage
            for h in read_frontpage(strain_dir):
                reg = str(h.get("region", ""))
                tier = h.get("tier", "")
                if reg:
                    kcb_tier_by_region[reg] = tier
                comp = _norm_compound(h.get("compound", ""))
                if comp:
                    kcb_tier_by_compound[comp] = tier
        except Exception:
            kcb_tier_by_region, kcb_tier_by_compound = {}, {}

    rows = _rows(tb)
    ledger, codes = [], {}
    n_block = n_watch = 0
    for r in sorted(rows, key=lambda x: int(float(x.get("Rank") or 9999))):
        bid = r.get("BGC_ID", "")
        if bgc and bid != bgc:
            continue
        # v9.7.371 fix: was .replace("region", "region") -- a literal no-op (replacing "region"
        # with itself changes nothing), making this line's `reg` identical to the raw
        # antiSMASH_Region value and the very next kcb_tier_by_region.get(reg, ...) lookup on line
        # below an exact duplicate of the raw-value fallback lookup 2 lines later. Every sibling
        # use of this same antiSMASH_Region field in this file (_locator(), the OVER_MERGE region
        # number, _c_over_merge()) strips the "region" prefix via .replace("region", "") to get the
        # bare numeric region label -- the shape kcb_tier_by_region's keys are built in (read_frontpage()
        # region values, stripped the same way). Reproduced live: a raw "region007" value only matches
        # a plausible {"007": tier} lookup dict after stripping, never before.
        reg = (r.get("antiSMASH_Region", "") or "").replace("region", "")
        kcb_compound = _norm_compound(r.get("KCB_top", ""))
        kcb_tier = (kcb_tier_by_compound.get(kcb_compound, "")
                    or kcb_tier_by_region.get(reg, "")
                    or kcb_tier_by_region.get((r.get("antiSMASH_Region", "") or ""), ""))

        cx = []
        cx.append(_c_class_conf(r))
        for finding in reclass_by_bgc.get(bid, []):
            cx.append(_c_reclass(finding))
        cx.append(_c_kcb(r, kcb_tier))
        cx.append(_c_two_pathway(r))
        cx.append(_c_two_model(r))
        cx.append(_c_over_merge(r, over_merge_map))
        cx.append(_c_misanchor(r))
        cx.append(_c_boundary(r))
        cx.append(_c_primary_metab(r))
        cx.append(_c_concordance(r))
        cx = [c for c in cx if c]
        cx = _attach_actions(cx, r, strain_dir)

        nb = sum(1 for c in cx if c["severity"] == "BLOCK")
        nw = sum(1 for c in cx if c["severity"] == "WATCH")
        n_block += 1 if nb else 0
        n_watch += 1 if (nw and not nb) else 0
        for c in cx:
            codes[c["code"]] = codes.get(c["code"], 0) + 1

        ledger.append(dict(
            bgc_id=bid, locator=_locator(r), label=_f(r, "Products"),
            arch=_f(r, "Arch"), boundary=_f(r, "Boundary"),
            ab=_f(r, "AB_auto"), af=_f(r, "AF_auto"),
            kcb_anchor=_f(r, "KCB_top") or _f(r, "KCB_clusterblast"),
            kcb_tier=kcb_tier or "UNVERIFIED",
            contradictions=cx, claim_ceiling=_claim_ceiling(r, kcb_tier),
            n_block=nb, n_watch=nw,
        ))

    summary = dict(n_bgc=len(ledger), n_with_block=n_block, n_with_watch=n_watch, codes=codes)
    return ledger, summary


# ── render ───────────────────────────────────────────────────────────────────
def render_md(ledger, summary, pkg):
    L = []
    strain = os.path.basename(os.path.dirname(os.path.abspath(pkg))) or os.path.basename(pkg)
    L.append(f"# Evidence reconciliation ledger — {strain}")
    L.append("")
    L.append("*Pre-authoring read. Store-backed [triage_board + gene_by_gene, curated reclass map]. "
             "Every item is a REVIEW PROMPT, not a verdict: capacity-level, KCB/BLASTp = similarity "
             "not identity, and supplied bioactivity metadata provides context only. Resolve BLOCK items before authoring §4/§8.*")
    L.append("")
    if summary.get("error"):
        L.append(f"> **cannot reconcile:** {summary['error']}")
        return "\n".join(L)
    L.append(f"**{summary['n_bgc']} BGC(s)** · "
             f"{summary['n_with_block']} with BLOCK contradiction(s) · "
             f"{summary['n_with_watch']} WATCH-only.")
    if summary["codes"]:
        L.append("")
        L.append("Contradiction codes: " + ", ".join(
            f"`{k}`×{v}" for k, v in sorted(summary["codes"].items())))
    L.append("")
    for e in ledger:
        flag = "🛑 BLOCK" if e["n_block"] else ("⚠️ WATCH" if e["n_watch"] else "✅ clear")
        L.append(f"## {e['locator']} — {flag}")
        L.append("")
        L.append(f"- antiSMASH label: `{e['label'] or '(none)'}` · Arch `{e['arch'] or '?'}` · "
                 f"Boundary `{e['boundary'] or '?'}` · AB/AF `{e['ab'] or '-'}/{e['af'] or '-'}`")
        L.append(f"- KCB anchor: {('`'+e['kcb_anchor']+'` (tier '+e['kcb_tier']+')') if e['kcb_anchor'] else 'KCB-dark'}")
        L.append("")
        if e["contradictions"]:
            L.append("**Contradictions to resolve:**")
            L.append("")
            for c in e["contradictions"]:
                mark = "🛑" if c["severity"] == "BLOCK" else "⚠️"
                L.append(f"- {mark} **{c['code']}** ({c['channel']}, {c['section']}) — {c['evidence']}")
                L.append(f"    - → {c['resolve']}")
                if c.get("action"):
                    L.append(f"    - ▶ `{c['action']}`")
            L.append("")
        else:
            L.append("**Contradictions to resolve:** none — channels agree at the store-backed level.")
            L.append("")
        L.append("**Claim ceiling:**")
        for cc in e["claim_ceiling"]:
            L.append(f"- {cc}")
        L.append("")
    return "\n".join(L)


def _self_lint(text):
    """Fail loudly if the tool ever emits an overclaim in its own narrative."""
    if _lint is None:
        return []
    # lint only the human-facing 'resolve'/ceiling prose lines, not code tokens
    return _lint(text)


# ── post-authoring loop closure: did the card address the BGC's own contradictions? ──
# Acknowledgment signals per contradiction code. Presence = the author engaged the flag;
# ABSENCE on a BLOCK contradiction is the high-value catch (a card that silently ignores an
# over-merge / class discrepancy while passing the generic Mode B gates). This detects SILENT
# OMISSION, not semantic correctness — a human still confirms the resolution is right.
_ACK_SIGNALS = {
    "OVER_MERGE": [r"protocluster", r"over[- ]?merge", r"scope_cluster", r"scoped",
                   r"split", r"separate cluster", r"distinct cluster", r"candidate cluster",
                   r"region (?:encodes|contains|merges|spans)"],
    "TWO_PATHWAY": [r"two[- ]?pathway", r"protocluster", r"separate (?:pathway|cluster)",
                    r"discrete (?:assembly line|pathway)", r"split"],
    "TWO_MODEL": [r"two[- ]?model", r"over[- ]?merge", r"protocluster", r"boundary", r"split"],
    "KCB_NOT_IDENTITY": [r"large[_ ]generic", r"coincidental", r"generic hit",
                         r"similarity, not identity", r"not (?:the same|identity)",
                         r"shared[- ]gene", r"few (?:shared |matching )?genes"],
    "CLASS_DISCREPANCY": [r"discrepan", r"reclass", r"discriminating domain", r"hmm[- ]?adjudicat",
                          r"undeclared", r"label (?:is )?not (?:supported|corroborated)"],
    "MISANCHOR": [r"misanchor", r"anchor", r"verified (?:the )?loc", r"locus_tag.{0,40}(?:verif|confirm)"],
    "PRIMARY_METABOLISM": [r"primary metabol", r"housekeeping", r"not a specialised",
                           r"not a specialized", r"SUF operon", r"primary-metabol"],
    "LOW_CLASS_CONFIDENCE": [r"low[- ]confidence", r"capacity", r"unresolved",
                             r"architecture[- ]led", r"class call is (?:low|uncertain)"],
    "TRUNCATED_NO_STRUCTURE": [r"truncat", r"edge", r"long[- ]read", r"no assembled",
                               r"fragment", r"incomplete"],
    "LOW_CONCORDANCE": [r"concordan", r"reconstruct", r"provisional", r"RG-?GMCI"],
}


def _ack_found(code, card_lc):
    for prefix, pats in _ACK_SIGNALS.items():
        if code.startswith(prefix):
            return any(re.search(p, card_lc) for p in pats)
    return None  # unknown code → cannot judge


def verify_card(pkg, bgc, card_md, strain_dir=None, cmap=None):
    """Cross-check an authored Mode B card against ITS BGC's reconcile contradictions.

    Returns (report, summary). For every contradiction reconcile raised for this BGC, report
    whether the card carries an acknowledgment signal for that code. BLOCK contradictions with no
    signal are ERRORs (the card silently ignored a flag the generic gates don't know about).
    """
    ledger, _ = reconcile(pkg, bgc=bgc, strain_dir=strain_dir, cmap=cmap)
    if not ledger:
        return [], {"error": f"BGC {bgc} not found in package", "bgc": bgc}
    entry = ledger[0]
    card_lc = (card_md or "").lower()
    report = []
    n_unaddressed_block = 0
    for c in entry["contradictions"]:
        ack = _ack_found(c["code"], card_lc)
        addressed = bool(ack)
        if c["severity"] == "BLOCK" and not addressed:
            n_unaddressed_block += 1
        report.append(dict(code=c["code"], severity=c["severity"],
                           evidence=c["evidence"], addressed=addressed,
                           status=("ADDRESSED" if addressed else "UNADDRESSED")))
    summary = dict(bgc=bgc, locator=entry["locator"], n_contradictions=len(report),
                   n_unaddressed_block=n_unaddressed_block)
    return report, summary


def render_verify_md(report, summary):
    L = [f"# Card verification vs reconcile ledger — {summary.get('bgc','?')}"]
    if summary.get("error"):
        return f"{L[0]}\n\n> {summary['error']}"
    L.append("")
    L.append(f"*{summary['locator']} — checks the authored card acknowledges every BLOCK "
             "contradiction reconcile raised. Detects SILENT OMISSION; a human confirms the "
             "resolution is correct. Signal absent on a BLOCK = the card ignored a flag.*")
    L.append("")
    verdict = "🛑 INCOMPLETE" if summary["n_unaddressed_block"] else "✅ all BLOCK flags addressed"
    L.append(f"**{summary['n_contradictions']} contradiction(s)** · "
             f"{summary['n_unaddressed_block']} BLOCK unaddressed → {verdict}")
    L.append("")
    for r in report:
        mark = "✅" if r["addressed"] else ("🛑" if r["severity"] == "BLOCK" else "⚠️")
        L.append(f"- {mark} **{r['code']}** ({r['severity']}) — {r['status']} — {r['evidence']}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Pre-authoring cross-channel evidence reconciliation ledger.")
    ap.add_argument("--package", required=True, help="sealed Mamey package directory")
    ap.add_argument("--bgc", default=None, help="single BGC id (default: all)")
    ap.add_argument("--strain-dir", default=None,
                    help="optional raw antiSMASH dir (regions.js) to compute the KCB corroboration tier")
    ap.add_argument("--map", default=os.path.join(_HERE, "reclass_discriminating_domains.json"),
                    help="curated discriminating-domain map (default: bundled)")
    ap.add_argument("--verify-card", default=None, metavar="CARD.md",
                    help="post-authoring: check an authored Mode B card addresses its BGC's BLOCK "
                         "contradictions (requires --bgc). Exit 1 if any BLOCK is unaddressed.")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--out", default=None, help="write to path instead of stdout")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any BGC has a BLOCK contradiction (pre-authoring gate)")
    a = ap.parse_args()

    cmap = None
    try:
        cmap = _read_json(a.map, encoding="utf-8")
    except Exception as e:
        emit(f"# warning: reclass map unavailable ({e}); class-discrepancy channel disabled",
              file=sys.stderr)

    # ── verify-card mode (post-authoring loop closure) ──
    if a.verify_card:
        if not a.bgc:
            ap.error("--verify-card requires --bgc")
        card_md = Path(a.verify_card).read_text(encoding="utf-8", errors="replace")
        report, vsummary = verify_card(a.package, a.bgc, card_md,
                                       strain_dir=a.strain_dir, cmap=cmap)
        out = (json.dumps({"summary": vsummary, "report": report}, indent=2)
               if a.json else render_verify_md(report, vsummary))
        if a.out:
            atomic_write_text(a.out, out); emit(f"wrote {a.out}")
        else:
            emit(out)
        if vsummary.get("error") or vsummary.get("n_unaddressed_block", 0) > 0:
            sys.exit(1)
        return

    ledger, summary = reconcile(a.package, bgc=a.bgc, strain_dir=a.strain_dir, cmap=cmap)

    if a.json:
        payload = json.dumps({"summary": summary, "ledger": ledger}, indent=2)
        out = payload
    else:
        out = render_md(ledger, summary, a.package)
        problems = _self_lint(out)
        if problems:
            emit("# INTERNAL claim-safety self-lint tripped (this is a bug in bgc_reconcile):",
                  file=sys.stderr)
            for p in problems:
                emit(f"#   {p}", file=sys.stderr)

    if a.out:
        atomic_write_text(a.out, out)
        emit(f"wrote {a.out}")
    else:
        emit(out)

    if a.strict and summary.get("n_with_block", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
