#!/usr/bin/env python3
"""split_cards.py — QC-fixer/generator for deterministic per-protocluster Mode B SPLIT
``*_FULL.md`` cards (graduated into the engine as a first-class deliverable tool,
v9.7.349x candidate; formerly ``_OVERMERGE_MODULE/fix_split_full_cards.py``).

When an over-merged region is split into its component protoclusters, one deterministic
per-protocluster Mode B ``*_FULL.md`` card is emitted for each. This tool patches the
deterministic base of those cards ONLY (it never touches Codex/Sapote judgment verdict
blocks). All injected text is wrapped in ``<!-- QCFIX:NAME START --> ... END -->`` markers
and is idempotent: existing QCFIX blocks are stripped before re-injection, so re-runs
converge to a fixed point.

Defect classes handled:
  D1  localized BLASTp (nr top-hit) + localized MIBiG evidence replaces the stale
      "no MIBiG / no BLASTp overlay / reference-dark" claim (claim-safe).
  D2  ensure a "## §28" evidence provenance ledger section exists.
  D3  soften §27 self-resistance calls that rest only on generic peptidase/transporter
      domains (no dedicated immunity/target-modification).
  D4  fix Edge-vs-Interior boundary label from the region GBK /contig_edge.
  D5  flag class-prose mismatch (T2PKS/T3PKS/HR-T2PKS product carrying generic modular
      NRPS/PKS prose).

CLAIM SAFETY: every injected block restates that similarity is not identity, subject
organisms are not strain-level taxonomy, capacity is not production, and computational
protocluster boundaries are not biological-pathway proof. Judgment deferred.

Usage:
  python split_cards.py [--dry-run] [--only SUBSTR] [--limit N]
                        [--base DIR] [--blastp-repo DIR] [--manifest TSV]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import csv, os, re, argparse, sys, zipfile  # noqa: F401 (zipfile used in load_region_gbk)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _widget_paths import ROOT_DEFAULT, master_dir, blastp_repo, module_dir  # noqa: E402

MODEB_DIR = "mode_b_codex_judged_2026-07-31"

# ---- classification vocab -------------------------------------------------
AROMATIC_PKS = {"T2PKS", "HR-T2PKS", "T3PKS"}
GENERIC_RESIST_DOM = re.compile(
    r"Peptidase_|ABC[_ -]|ABC-2|transport|permease|MFS|efflux|Peptidase$", re.I)

MARKER_RE = re.compile(
    r"\n?<!-- QCFIX:[A-Z0-9-]+ START -->.*?<!-- QCFIX:[A-Z0-9-]+ END -->\n?",
    re.S)
HEADER_RE = re.compile(
    r"parent:\s*(\S+)\s+(\S+)\s+\(([^)]+?)\s+(region\d+)\)\s*\|\s*"
    r"protocluster\s+(\d+)/(\d+)\s*\|\s*product:\s*([^|]+?)\s*(?:\||-->)")


class Fixer:
    """Holds resolved paths + a per-run GBK cache; runs the QC fixer over cards."""

    def __init__(self, base, blastp_repo_dir):
        self.base = base
        self.brepo = blastp_repo_dir
        self._gbk_cache = {}

    def load_region_gbk(self, strain, contig, region):
        key = (strain, contig, region)
        if key in self._gbk_cache:
            return self._gbk_cache[key]
        protos = []
        zpath = os.path.join(self.base, strain, "antiSMASH", f"{strain}.zip")
        member = f"{contig}.{region}.gbk"
        try:
            with zipfile.ZipFile(zpath) as z:
                names = {os.path.basename(n): n for n in z.namelist()}
                if member not in names:
                    self._gbk_cache[key] = protos
                    return protos
                text = z.read(names[member]).decode("utf-8", "replace")
        except (OSError, KeyError, zipfile.BadZipFile):
            self._gbk_cache[key] = protos
            return protos
        lines = text.splitlines()
        cur = None
        for ln in lines:
            m = re.match(r"^     protocluster\s+(\S+)", ln)
            if m:
                if cur:
                    protos.append(cur)
                cur = {"span": m.group(1), "contig_edge": None,
                       "product": None, "number": None}
                continue
            if cur is not None:
                if re.match(r"^     [A-Za-z_]+\s+\S", ln) and not ln.startswith("                     "):
                    protos.append(cur)
                    cur = None
                    continue
                e = re.search(r'/contig_edge="(\w+)"', ln)
                if e:
                    cur["contig_edge"] = e.group(1)
                p = re.search(r'/product="([^"]+)"', ln)
                if p and cur["product"] is None:
                    cur["product"] = p.group(1)
                n = re.search(r'/protocluster_number="(\d+)"', ln)
                if n:
                    cur["number"] = n.group(1)
        if cur:
            protos.append(cur)
        self._gbk_cache[key] = protos
        return protos

    def process_card(self, path, stats, dry=False):
        return process_card(self, path, stats, dry=dry)


def read_csv_rows(path):
    if not os.path.isfile(path):
        return None
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def parse_gene_table(text):
    genes = {}
    order = []
    for ln in text.splitlines():
        m = re.match(r"^\|\s*`(ctg[\w.]+_\d+)`\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", ln)
        if m:
            gid = m.group(1)
            genes[gid] = {
                "coords": m.group(2).strip(),
                "kind": m.group(3).strip(),
                "domains": m.group(4).strip(),
                "desc": m.group(5).strip(),
            }
            order.append(gid)
    return genes, order


def italic(org):
    org = (org or "").strip()
    return f"*{org}*" if org else "unknown organism"


def fmt_blastp_line(r):
    gid = r.get("gene", "")
    dfn = (r.get("subject_def") or "").strip()
    dfn = re.sub(r"\s*\[[^\]]*\]\s*$", "", dfn)
    org = r.get("subject_organism", "")
    acc = r.get("subject_acc", "")
    pid = r.get("pct_identity", "")
    al = r.get("align_length", "")
    try:
        pid_s = f"~{float(pid):.0f}%"
    except (ValueError, TypeError):
        pid_s = f"{pid}%"
    return (f"- `{gid}` → {dfn or 'hypothetical protein'} — top nr match "
            f"{acc} ({italic(org)}); {pid_s} database similarity over {al} aa.")


def process_card(fx, path, stats, dry=False):
    base, brepo = fx.base, fx.brepo
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    orig = text
    text = MARKER_RE.sub("\n", text)
    text = re.sub(r"\n## §28 Evidence provenance ledger[ \t]*\n+(?=## §|---|\Z)",
                  "\n", text)

    hm = HEADER_RE.search(text)
    if not hm:
        stats["parse_fail"] += 1
        return None
    strain, bgc, contig, region, k, N, product = hm.groups()
    product = product.strip()
    k = k.strip()

    genes, gene_order = parse_gene_table(text)
    loci = set(genes)

    fixed = []

    # ---- D4 boundary --------------------------------------------------------
    boundary_note = None
    protos = fx.load_region_gbk(strain, contig, region)
    pc = None
    for p in protos:
        if p.get("number") == k:
            pc = p
            break
    if pc is None and protos:
        idx = int(k) - 1
        if 0 <= idx < len(protos):
            pc = protos[idx]
    if pc and pc.get("contig_edge") == "True":
        if re.search(r"Interior \(single isolated protocluster\)", text):
            boundary_note = (
                "<!-- QCFIX:BOUNDARY START -->\n"
                f"> **Boundary correction (QC):** antiSMASH marks this protocluster "
                f"**Edge / contig-truncated** (region GBK `{contig}.{region}.gbk`, "
                f"protocluster {k}, `/contig_edge=\"True\"` — it reaches a contig terminus). "
                "The templated “Interior (single isolated protocluster)” label above is "
                "**superseded**: treat the captured gene inventory as a **lower bound / one-sided "
                "(edge-truncated) locus**, not a complete cluster. Boundary is computational; "
                "judgment deferred.\n"
                "<!-- QCFIX:BOUNDARY END -->")
            fixed.append("D4_boundary")

    # ---- D1 localized evidence ---------------------------------------------
    blastp_path = os.path.join(brepo, strain, bgc, f"{bgc}_top_hit_per_gene.csv")
    blastp_rows = read_csv_rows(blastp_path) or []
    blastp_local = [r for r in blastp_rows if r.get("gene") in loci]

    recon_name = f"{strain}_{bgc}_EVIDENCE_RECONCILIATION.csv"
    recon_path = os.path.join(base, strain, MODEB_DIR, recon_name)
    recon_rows = read_csv_rows(recon_path) or []
    mibig_local = [r for r in recon_rows
                   if r.get("locus_tag") in loci and (r.get("mibig_compound") or "").strip()]

    have_blastp = bool(blastp_local)
    have_mibig = bool(mibig_local)

    ev_note = None
    if have_blastp or have_mibig:
        def sortkey(r):
            gid = r.get("gene", "")
            kind = genes.get(gid, {}).get("kind", "")
            core = 0 if kind.startswith("biosynthetic") else 1
            try:
                bs = -float(r.get("bitscore") or 0)
            except (ValueError, TypeError):
                bs = 0
            return (core, bs)
        bl_sorted = sorted(blastp_local, key=sortkey)
        cap = 18
        bl_show = bl_sorted[:cap]
        bl_lines = "\n".join(fmt_blastp_line(r) for r in bl_show)
        if len(bl_sorted) > cap:
            bl_lines += f"\n- … +{len(bl_sorted)-cap} further localized nr top hits (see source file)."

        comp = {}
        for r in mibig_local:
            comp.setdefault(r.get("mibig_compound").strip(), []).append(r.get("locus_tag"))
        mibig_str = "; ".join(
            f"{c} at {len(v)} loci ({', '.join(sorted(v)[:8])}{'…' if len(v)>8 else ''})"
            for c, v in sorted(comp.items(), key=lambda kv: -len(kv[1])))

        parts = ["<!-- QCFIX:LOCALIZED-EVIDENCE START -->",
                 "> **Localized independent evidence (QC correction).** The templated "
                 "“reference-dark / no dominant MIBiG family / no BLASTp overlay” statements above "
                 "are **superseded for this protocluster** — localized evidence exists for its assigned "
                 f"genes. Similarity is not identity; subject organisms are **not** {strain}-strain taxonomy; "
                 "capacity is not production; judgment deferred."]
        if have_mibig:
            parts.append(f"\n**Localized MIBiG family anchors** ({len(mibig_local)} gene rows): "
                         f"{mibig_str}. Class-level family similarity only (source: "
                         f"`{recon_name}`).")
        if have_blastp:
            parts.append(f"\n**Localized independent BLASTp (NCBI nr top hit)** "
                         f"— {len(blastp_local)} of {len(loci)} assigned genes carry an nr top hit "
                         f"(source: `BLASTp Repository/{strain}/{bgc}/{bgc}_top_hit_per_gene.csv`; "
                         f"query coverage not reported in this export → coverage HOLD):\n"
                         f"{bl_lines}")
        parts.append("<!-- QCFIX:LOCALIZED-EVIDENCE END -->")
        ev_note = "\n".join(parts)
        fixed.append("D1_localized_evidence")

    # ---- D2 / §28 ledger ----------------------------------------------------
    n_core = sum(1 for g in loci if genes.get(g, {}).get("kind", "").startswith("biosynthetic"))
    n_dom = sum(1 for g in loci if genes.get(g, {}).get("domains", ""))
    mibig_bullet = (
        f"**MIBiG per-gene (localized)** — {len(mibig_local)} gene rows across this "
        f"protocluster carry a MIBiG family anchor (source `{recon_name}`); localized family "
        f"similarity, not product identity."
        if have_mibig else
        "**MIBiG per-gene (localized)** — HOLD: no MIBiG family localized to this "
        "protocluster's genes above the convergence floor.")
    blastp_bullet = (
        f"**Independent BLASTp (NCBI nr top-hit, localized)** — {len(blastp_local)} of "
        f"{len(loci)} assigned genes carry an nr top hit (source "
        f"`BLASTp Repository/{strain}/{bgc}/{bgc}_top_hit_per_gene.csv`); database similarity, "
        f"query-coverage HOLD (not in export)."
        if have_blastp else
        f"**Independent BLASTp (NCBI nr top-hit)** — HOLD: no BLASTp Repository top-hit file "
        f"localized to this BGC ({bgc}); independent nr channel not wired for this protocluster.")
    sec28 = (
        "<!-- QCFIX:SEC28 START -->\n"
        "## §28 Evidence provenance ledger\n\n"
        f"Per-channel provenance for this protocluster's **{len(loci)} assigned genes** "
        "(localized to the loci in the gene table above). Similarity is not identity; subject "
        "organisms are not strain-level taxonomy; capacity is not production; computational "
        "protocluster boundaries are not biological-pathway proof; judgment deferred.\n\n"
        f"- **antiSMASH domain grammar** — {n_core} biosynthetic-core / {n_dom} domain-annotated "
        f"CDS from the region GBK (`{contig}.{region}.gbk`). Class-capacity evidence only.\n"
        f"- {mibig_bullet}\n"
        f"- {blastp_bullet}\n"
        "- **ClusterBlast / neighbourhood** — synteny/neighbourhood context only; see the parent "
        "union card.\n"
        "- **Swiss-Prot / ClusteredNR / direct-online nr / EBI** — separate channels; see the "
        f"co-located `{recon_name}` where present, otherwise channel HOLD.\n"
        "<!-- QCFIX:SEC28 END -->")
    has_native_28 = re.search(r"^## §28\b", text, re.M)

    # ---- D3 self-resistance softening --------------------------------------
    sr_note = None
    m27 = re.search(r"## §27[^\n]*\n(.*?)(?=\n## §|\n---|\Z)", text, re.S)
    if m27 and "target-based/efflux candidates" in m27.group(1):
        cited = re.findall(r"`(ctg[\w.]+_\d+)`", m27.group(1))
        doms = [genes.get(g, {}).get("domains", "") for g in cited]
        generic_only = doms and all(
            d and GENERIC_RESIST_DOM.search(d) for d in doms)
        if generic_only:
            dom_list = ", ".join(sorted({d for d in doms if d}))
            gene_list = ", ".join(f"`{g}`" for g in cited)
            sr_note = (
                "<!-- QCFIX:SELFRESIST START -->\n"
                f"> **Self-resistance correction (QC):** the candidate(s) above ({gene_list}; "
                f"domain(s) **{dom_list}**) are **generic peptidase/transporter-family** proteins, "
                "not a dedicated resistance, target-modification, or producer-immunity determinant. "
                "Co-location in a BGC does not make a housekeeping peptidase or transporter a "
                "self-resistance gene. **No dedicated immunity/target-modification gene was captured "
                "in this protocluster**; self-protection cannot be established from this evidence.\n"
                "<!-- QCFIX:SELFRESIST END -->")
            fixed.append("D3_selfresist")

    # ---- D5 class-prose mismatch -------------------------------------------
    class_note = None
    if product in AROMATIC_PKS and re.search(r"NRPS", text):
        kind = "type-III (chalcone/stilbene-synthase-like) PKS" if product == "T3PKS" \
               else "aromatic type-II polyketide synthase"
        detail = ("a single KS_alpha / KS_beta(CLF) / ACP minimal iterative aromatic PKS with "
                  "cyclase/aromatase tailoring") if product != "T3PKS" else \
                 ("a stand-alone type-III ketosynthase acting iteratively on CoA thioesters")
        class_note = (
            "<!-- QCFIX:CLASSPROSE START -->\n"
            f"> **Class correction (QC):** antiSMASH calls this protocluster **{product}** — "
            f"{detail}, **not** a modular NRPS/PKS assembly line. Disregard the templated "
            "“NRPS/PKS core”, “A-domain / KS-substrate”, and “large NRPS/PKS” phrasing above "
            "and in §4/§16/§17: there are no NRPS adenylation (A) domains or modular extension "
            f"modules to profile. The class-appropriate next step is KS/CLF and cyclase/aromatase "
            "analysis (chain length + cyclization/aromatization pattern), not A-domain substrate "
            "prediction. Class-level capacity only; judgment deferred.\n"
            "<!-- QCFIX:CLASSPROSE END -->")
        fixed.append("D5_classprose")

    # ---- assemble: insert blocks at section boundaries ----------------------
    def append_to_section(txt, secnum, block):
        pat = re.compile(rf"(## §{secnum}\b[^\n]*\n.*?)(?=\n## §|\n---|\Z)", re.S)
        m = pat.search(txt)
        if not m:
            return txt, False
        seg = m.group(1).rstrip("\n")
        return txt[:m.start()] + seg + "\n\n" + block + "\n" + txt[m.end():], True

    if boundary_note:
        text, _ = append_to_section(text, 3, boundary_note)
    if ev_note:
        text, _ = append_to_section(text, 4, ev_note)
    if class_note:
        text, ok = append_to_section(text, 5, class_note)
        if not ok:
            text, _ = append_to_section(text, 4, class_note)
    if sr_note:
        text, _ = append_to_section(text, 27, sr_note)

    if not has_native_28:
        m29 = re.search(r"\n## §29\b", text)
        insert_at = m29.start() if m29 else None
        if insert_at is None:
            mtr = re.search(r"\n---\n", text)
            insert_at = mtr.start() if mtr else len(text)
        text = text[:insert_at] + "\n\n" + sec28 + "\n" + text[insert_at:]
        fixed.append("D2_sec28")

    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text.endswith("\n"):
        text += "\n"

    for f in fixed:
        stats[f] += 1
    if text != orig:
        stats["cards_changed"] += 1
        if not dry:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
    return fixed


def run_fixer(manifest, base, blastp_repo_dir, dry=False, only=None, limit=0):
    """Run the QC fixer over every card in the manifest. Returns a stats dict.

    manifest        : SPLIT_FULL_CARDS_MANIFEST.tsv (last tab-column = card path rel to base).
    base            : strain_data root (resolves cards + region GBK zips + recon CSVs).
    blastp_repo_dir : BLASTp Repository root.
    """
    fx = Fixer(base, blastp_repo_dir)
    with open(manifest, encoding="utf-8") as fh:
        rows = [ln.rstrip("\r\n") for ln in fh][1:]
    stats = {k: 0 for k in ["cards_processed", "cards_changed", "parse_fail",
                            "D1_localized_evidence", "D2_sec28", "D3_selfresist",
                            "D4_boundary", "D5_classprose", "missing"]}
    n = 0
    for ln in rows:
        if not ln.strip():
            continue
        rel = ln.split("\t")[-1]
        if only and only not in rel:
            continue
        path = os.path.join(base, rel)
        if not os.path.isfile(path):
            stats["missing"] += 1
            continue
        process_card(fx, path, stats, dry=dry)
        n += 1
        if limit and n >= limit:
            break
    stats["cards_processed"] = n
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="substring filter on card path")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--base", default=None, help="strain_data root")
    ap.add_argument("--blastp-repo", default=None, help="BLASTp Repository root")
    ap.add_argument("--manifest", default=None,
                    help="SPLIT_FULL_CARDS_MANIFEST.tsv (default: in _OVERMERGE_MODULE)")
    args = ap.parse_args()

    base = args.base or master_dir()
    brepo = args.blastp_repo or blastp_repo()
    manifest = args.manifest or os.path.join(
        module_dir("_OVERMERGE_MODULE"), "SPLIT_FULL_CARDS_MANIFEST.tsv")

    stats = run_fixer(manifest, base, brepo, dry=args.dry_run,
                      only=args.only, limit=args.limit)

    emit("\n=== SUMMARY ===", f"cards processed:        {stats['cards_processed']}", f"cards changed:          {stats['cards_changed']}", f"D1 localized evidence:  {stats['D1_localized_evidence']}", f"D2 §28 ledger added:    {stats['D2_sec28']}", f"D3 self-resist softened:{stats['D3_selfresist']}", f"D4 boundary corrected:  {stats['D4_boundary']}", f"D5 class-prose flagged: {stats['D5_classprose']}", f"header parse failures:  {stats['parse_fail']}", f"missing cards:          {stats['missing']}", sep="\n")


if __name__ == "__main__":
    main()
