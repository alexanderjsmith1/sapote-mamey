#!/usr/bin/env python3
"""build_domain_matrix.py — cross-strain antiSMASH-HMM domain census (v9.7.221).

Formalises the PATCHCHAT cross-strain domain-census work order. Reads the per-gene
`sec_met_domains` column (antiSMASH pre-computed HMMER domain calls, banked in every sealed Mamey
package — no add-on, no external HMMER re-run) across a cohort and emits a domain x strain matrix,
per-Mbp density, a functional rollup, and a core/accessory/strain-private split.

CLAIM SAFETY (mandatory banner, same standing as KCB): antiSMASH domain calls are HMMER PROFILE /
SIMILARITY matches, NOT verified function. Raw counts scale with genome size and assembly
fragmentation, so **per-Mbp density is the cross-strain-comparable metric**; strains with many
Edge/Full-contig BGCs carry a fragmentation caveat, and a single-strain domain is a CANDIDATE
(possible assembly/annotation artifact) until confirmed.

The domain->function vocabulary is SINGLE-SOURCED from `mamey.mamey_markers.MAMEY_MARKERS` (each
Marker's regex Target + its `category`), so it never drifts from the engine's own marker set.

Source-agnostic by design: `--domtblout-dir` lets a future Release-2 offline-pyHMMER
(`scanner_pfam_150.hmm`) domtblout be folded in as a second, higher-recall domain source.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, json, os, re, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open


def _vocab():
    """Compiled (regex, category) list from MAMEY_MARKERS — the single source of domain->function truth."""
    from mamey.mamey_markers import MAMEY_MARKERS
    out = []
    for mk in MAMEY_MARKERS:
        for tg in mk.targets:
            if getattr(tg, "type", "") == "regex" and getattr(tg, "value", ""):
                try:
                    out.append((re.compile(tg.value, re.IGNORECASE), mk.category))
                except re.error:
                    continue
    return out


def _categorize(token, vocab):
    for rx, cat in vocab:
        if rx.search(token):
            return cat
    return None


def _split_domains(cell):
    """antiSMASH sec_met_domains cell -> individual domain tokens (';'/','/space-joined)."""
    return [t.strip() for t in re.split(r"[;,]| {2,}", cell or "") if t.strip()]


def load_strain(pkg):
    man = os.path.join(pkg, "manifest.json")
    gbg = glob.glob(os.path.join(pkg, "*_gene_by_gene_all_bgcs.csv"))
    if not (os.path.isfile(man) and gbg):
        return None
    with open(man, encoding="utf-8") as fh:
        m = json.load(fh)
    sid = m.get("strain_id") or m.get("strain") or os.path.basename(os.path.dirname(pkg))
    asm = m.get("assembly", {}) or {}
    gbp = asm.get("genome_bp") or m.get("genome_bp") or 0
    mbp = round(gbp / 1e6, 3) if gbp else None
    tier = asm.get("assembly_tier") or (m.get("bgc_counts", {}) or {}).get("assembly_tier") or "?"
    dom = Counter()
    genes = 0
    with open(gbg[0], encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            genes += 1
            for tok in _split_domains(row.get("sec_met_domains")):
                dom[tok] += 1
    return {"strain": sid, "mbp": mbp, "tier": tier, "genes": genes, "domains": dom}


def build(cohort_dirs, vocab):
    strains = []
    for d in cohort_dirs:
        # accept a cohort dir (many package subdirs) or a single package dir
        pkgs = ([d] if os.path.isfile(os.path.join(d, "manifest.json"))
                else [p for p in glob.glob(os.path.join(d, "*", "package")) + glob.glob(os.path.join(d, "*"))
                      if os.path.isdir(p)])
        for p in pkgs:
            s = load_strain(p)
            if s:
                strains.append(s)
    strains.sort(key=lambda s: s["strain"])
    all_domains = sorted({d for s in strains for d in s["domains"]})
    n = len(strains)
    # core / accessory / private by presence
    presence = {d: sum(1 for s in strains if d in s["domains"]) for d in all_domains}
    core = [d for d in all_domains if presence[d] == n and n > 0]
    private = [d for d in all_domains if presence[d] == 1]
    accessory = [d for d in all_domains if 1 < presence[d] < n]
    return strains, all_domains, {"core": core, "accessory": accessory, "private": private, "presence": presence}


BANNER = (
    "antiSMASH pre-computed HMMER domain calls = SIMILARITY / profile match, NOT verified function "
    "(same standing as KCB). Per-Mbp density is the cross-strain-comparable metric (raw counts scale "
    "with genome size and assembly fragmentation). A single-strain (private) domain is a CANDIDATE — "
    "possibly an assembly/annotation artifact — until confirmed. Vocabulary single-sourced from "
    "mamey.mamey_markers.MAMEY_MARKERS."
)


def write_outputs(strains, all_domains, split, vocab, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    names = [s["strain"] for s in strains]
    # counts matrix
    with atomic_open(os.path.join(out_dir, "domain_matrix_counts.csv"), "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh); w.writerow(["domain", "function", *names, "n_strains_present"])
        for d in all_domains:
            w.writerow([d, _categorize(d, vocab) or "", *[s["domains"].get(d, 0) for s in strains], split["presence"][d]])
    # density matrix (per Mbp)
    with atomic_open(os.path.join(out_dir, "domain_matrix_density_per_mbp.csv"), "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh); w.writerow(["domain", "function", *names])
        for d in all_domains:
            w.writerow([d, _categorize(d, vocab) or "",
                        *[round(s["domains"].get(d, 0) / s["mbp"], 3) if s["mbp"] else "" for s in strains]])
    # functional rollup (category x strain, density)
    cats = sorted({_categorize(d, vocab) for d in all_domains if _categorize(d, vocab)})
    with atomic_open(os.path.join(out_dir, "domain_functional_rollup.csv"), "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh); w.writerow(["function", *names])
        for cat in cats:
            row = []
            for s in strains:
                cnt = sum(v for dd, v in s["domains"].items() if _categorize(dd, vocab) == cat)
                row.append(round(cnt / s["mbp"], 3) if s["mbp"] else "")
            w.writerow([cat, *row])
    # markdown summary
    with atomic_open(os.path.join(out_dir, "Domain_Matrix.md"), "w", encoding="utf-8") as fh:
        fh.write("# Cross-strain antiSMASH-HMM domain census\n\n")
        fh.write(f"> **Claim safety.** {BANNER}\n\n")
        fh.write(f"- Cohort: **{len(strains)} strains** ({', '.join(names)})\n")
        fh.write(f"- Distinct antiSMASH domain tokens: **{len(all_domains)}**\n")
        fh.write(f"- **Core** (all {len(strains)}): **{len(split['core'])}** · "
                 f"**Accessory**: **{len(split['accessory'])}** · **Strain-private**: **{len(split['private'])}**\n\n")
        fh.write("Outputs: `domain_matrix_counts.csv`, `domain_matrix_density_per_mbp.csv`, "
                 "`domain_functional_rollup.csv` (function x strain, per-Mbp).\n")
    return {"n_strains": len(strains), "n_domains": len(all_domains),
            "core": len(split["core"]), "accessory": len(split["accessory"]), "private": len(split["private"])}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cross-strain antiSMASH-HMM domain census (density-normalised).")
    ap.add_argument("--cohort-dir", nargs="+", required=True, help="cohort dir(s) of sealed packages, or package dirs")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--domtblout-dir", default=None,
                    help="(Release-2 hook) offline-pyHMMER domtblout dir — second higher-recall source; not required")
    a = ap.parse_args(argv)
    vocab = _vocab()
    strains, all_domains, split = build(a.cohort_dir, vocab)
    if not strains:
        emit("no sealed packages with *_gene_by_gene_all_bgcs.csv found", file=sys.stderr)
        return 1
    summary = write_outputs(strains, all_domains, split, vocab, a.out_dir)
    emit(f"domain census: {summary['n_strains']} strains, {summary['n_domains']} domains "
          f"(core {summary['core']} / accessory {summary['accessory']} / private {summary['private']}) -> {a.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
