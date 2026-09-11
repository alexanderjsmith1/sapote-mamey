#!/usr/bin/env python3
"""tailoring_extract.py — tailoring-enzyme extraction for domain trees (VGP-399, card 2/3).

DESIGN-CRITICAL distinction vs mamey/ks_phylogeny.py: module-core domains are aSDomain features
(sub-CDS spans with their own /translation). Tailoring enzymes are WHOLE-CDS calls carried as
/sec_met_domain tags on the CDS feature. So this is a SECOND extraction mechanism — CDS translation
by exact tag — not a new entry in DEFAULT_CLASSES. (Bolting tailoring names onto the aSDomain parser
would silently extract nothing: the same failure shape as the pre-ship "pks" bug documented at
ks_phylogeny.py:48. Exact-tag matching is enforced here for the same reason.)

Families are data-driven: mamey/data/tailoring_families.json maps family -> exact sec_met_domain
tags (every tag verified present in this project's real region GBKs, 2026-09-01 survey). Adding a
family is data, not code.

Guards inherited from the module-core lane:
  * STRAIN-INTERNAL ONLY for strain-internal trees (same filename gate as ks_phylogeny, fail-closed).
  * Claim-safety: family membership = CAPACITY context (a halogenase-family CDS is capacity to
    halogenate, never evidence a product IS halogenated — diagnostic-gene-capacity-not-identity).
    Deterministic extraction; no score, no linkage, no activity claim; judgment deferred.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "tailoring_families.json"

_NODE_RE = re.compile(r"(NODE_\d+)")
_STRAIN_RE = re.compile(r"^((?:[A-Z]{2,4})[-_]\d{1,6})", re.I)
_REGION_RE = re.compile(r"(region\d+)", re.I)
_FEATURE_HDR = re.compile(r"^ {5}(\S+)\s")
_QUAL = re.compile(r'^ {21}/([A-Za-z_]+)=(.*)$')
# '/sec_met_domain="Trp_halogenase (E-value: 1.1e-100, bitscore: ...)"' -> tag + evalue
_SECMET = re.compile(r'^\s*([A-Za-z0-9_.-]+)\s*(?:\(E-value:\s*([0-9.eE+-]+))?')


class TailoringExtractError(ValueError):
    """Typed refusal; message starts with a stable CODE token."""


def load_registry(path: Path | str | None = None) -> dict:
    p = Path(path) if path else _REGISTRY_PATH
    if not p.exists():
        raise TailoringExtractError(f"REGISTRY_MISSING: {p}")
    reg = json.loads(p.read_text(encoding="utf-8"))
    reg.pop("_comment", None)
    for fam, ent in reg.items():
        if not isinstance(ent.get("tags"), list) or not ent["tags"]:
            raise TailoringExtractError(f"REGISTRY_INVALID: family {fam!r} has no tags list")
        lw = ent.get("length_window", [0, 10**6])
        if not (isinstance(lw, list) and len(lw) == 2 and lw[0] < lw[1]):
            raise TailoringExtractError(f"REGISTRY_INVALID: family {fam!r} malformed length_window {lw}")
    return reg


def _strain_from_name(name: str):
    m = _STRAIN_RE.match(name)
    return m.group(1).upper().replace("_", "-") if m else None


def _parse_gbk_cds(text: str, node: str, region: str) -> list[dict]:
    """Regex parse of CDS feature blocks: locus_tag, whole-CDS /translation, and every
    /sec_met_domain tag (+ its E-value) on that CDS. Same block-walk as ks_phylogeny's aSDomain
    parser, keyed on the CDS feature instead."""
    out: list[dict] = []
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        m = _FEATURE_HDR.match(lines[i])
        if not m or m.group(1) != "CDS":
            i += 1
            continue
        quals: dict[str, list[str]] = {}
        cur_key, cur_val = None, []
        i += 1
        while i < n and not _FEATURE_HDR.match(lines[i]):
            qm = _QUAL.match(lines[i])
            if qm:
                if cur_key:
                    quals.setdefault(cur_key, []).append("".join(cur_val).strip('"'))
                cur_key, cur_val = qm.group(1), [qm.group(2)]
            elif cur_key:
                cur_val.append(lines[i].strip())
            i += 1
        if cur_key:
            quals.setdefault(cur_key, []).append("".join(cur_val).strip('"'))
        secmet = []
        for raw in quals.get("sec_met_domain", []):
            sm = _SECMET.match(raw)
            if sm:
                secmet.append((sm.group(1), sm.group(2) or ""))
        out.append({
            "locus_tag": (quals.get("locus_tag") or [""])[0],
            "translation": re.sub(r"\s+", "", (quals.get("translation") or [""])[0]),
            "sec_met": secmet,
            "node": node,
            "region": region,
        })
    return out


def extract_tailoring_enzymes(gbk_dir: Path | str,
                              families: Iterable[str],
                              registry: dict | None = None,
                              require_single_strain: bool = True) -> dict:
    """Extract whole-CDS tailoring enzymes by EXACT sec_met_domain tag from region GBKs.

    Returns {strain, enzymes, family_counts, claim_safety}. Each enzyme dict carries the
    gene-level-guard receipt: locus_tag, matched_tag, evalue, node, region, family."""
    registry = registry or load_registry()
    families = tuple(families)
    unknown = [f for f in families if f not in registry]
    if unknown:
        raise TailoringExtractError(
            f"UNKNOWN_FAMILY: {unknown} — known families: {sorted(registry)}")
    tag2fam = {}
    for fam in families:
        for tag in registry[fam]["tags"]:
            tag2fam[tag] = fam            # EXACT tag -> family (never substring)
    gbk_dir = Path(gbk_dir)
    gbks = sorted(gbk_dir.glob("*.gbk"))
    if not gbks:
        raise TailoringExtractError(f"NO_GBKS: no .gbk files in {gbk_dir}")
    named = {p.name: _strain_from_name(p.name) for p in gbks}
    if require_single_strain:
        unrecognized = sorted(name for name, s in named.items() if not s)
        if unrecognized:
            raise TailoringExtractError(
                f"STRAIN-INTERNAL ONLY: could not determine a strain id from filename(s) "
                f"{unrecognized} in {gbk_dir} (fail-closed, per ks_phylogeny v9.7.374 gate).")
        strains = set(named.values())
        if len(strains) > 1:
            raise TailoringExtractError(
                f"STRAIN-INTERNAL ONLY: multiple strains in {gbk_dir}: {sorted(strains)}")
    enzymes: list[dict] = []
    for p in gbks:
        nm = _NODE_RE.search(p.name)
        node = nm.group(1) if nm else "NODE_?"
        rm = _REGION_RE.search(p.name)
        region = rm.group(1) if rm else "region001"
        for cds in _parse_gbk_cds(p.read_text(encoding="utf-8", errors="replace"), node, region):
            if not cds["translation"]:
                continue
            for tag, ev in cds["sec_met"]:
                fam = tag2fam.get(tag)   # exact match only
                if fam:
                    enzymes.append({
                        "family": fam, "matched_tag": tag, "evalue": ev,
                        "locus_tag": cds["locus_tag"], "translation": cds["translation"],
                        "node": node, "region": region,
                        "strain": named.get(p.name) or "UNKNOWN",
                        "domain_id": "",   # whole-CDS: no sub-domain id
                    })
                    break                # one family membership per CDS (first matching tag)
    return {
        "strain": (next(iter(set(named.values()))) if require_single_strain else "MULTI"),
        "enzymes": enzymes,
        "family_counts": dict(Counter(e["family"] for e in enzymes)),
        "claim_safety": [
            "CAPACITY, NOT IDENTITY: a tailoring-family CDS is capacity for that chemistry class — "
            "never evidence the product carries the modification.",
            "Exact sec_met_domain tag matching only (substring matching = the ks_phylogeny 'pks' bug).",
            "Deterministic extraction; homology substrate only; no linkage/activity/novelty claim; "
            "judgment deferred.",
        ],
    }
