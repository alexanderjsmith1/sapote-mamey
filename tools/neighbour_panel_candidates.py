#!/usr/bin/env python3
"""Build one isolate's genome-neighbourhood candidate panel from three evidence sources.

Sources (all read from local files; this tool makes no network call):
  1. 16S genome hits  -- an NCBI web blastn of the isolate's 16S against core_nt, saved as
     tabular text (12 columns: qseqid sseqid pident length mismatch gapopen qstart qend sstart send
     evalue bitscore). Only hits on a sequence that belongs to a complete or chromosome-level
     assembly resolve to a genome; the rest go to the issues table.
  2. NCBI genome table -- `datasets summary genome taxon <taxon> --assembly-level complete,chromosome`
     (assemblies) and the same with `--report sequence` (sequence -> assembly), plus
     `datasets summary genome taxon <taxon> --from-type` (type-material assemblies, any level).
  3. TYGS -- the job's digital DDH table (comp_type, query_genome, subject_genome, digital_ddh_d4 ...).
     The top --tygs-top type strains by d4 for this isolate are resolved to type-material assemblies
     by organism name.

Output: PANEL_TREE.tsv (one row per assembly; `why` lists every source that put it there) and
PANEL_ISSUES.tsv (hits or type strains that did not resolve). The isolate itself and any accession in
--exclude are never added. RefSeq (GCF) is preferred over its paired GenBank (GCA) accession.

Claim safety: panel membership is comparator selection, not a species or genus call. A 16S identity
and a dDDH value are relatedness measurements.

Usage:
  neighbour_panel_candidates.py --isolate ISOLATE_001 --blast ISOLATE_001.tsv \
      --assemblies assemblies.jsonl --sequences sequences.jsonl --type-assemblies type_assemblies.jsonl \
      --tygs tygs_digital_ddh.tsv [--top-16s 100] [--tygs-top 10] [--min-align 600] \
      [--exclude own_genomes.txt] --out-dir PANEL/ISOLATE_001
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console import emit  # noqa: E402
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

PANEL_COLUMNS = ["ncbi_accession", "source", "best_16S_identity", "blast_hits", "organism", "strain",
                 "ncbi_type_material", "tygs_type_strain", "tygs_d4", "assembly_level", "why"]
ISSUE_COLUMNS = ["source", "item", "detail"]
CLAIM_CEILING = ("Panel membership is comparator selection only; 16S identity and dDDH are relatedness "
                 "measurements, not species or genus calls.")


def _norm_acc(acc: str) -> str:
    acc = acc.split("|")[-2] if acc.count("|") >= 2 else acc
    return acc.strip()


def read_blast(path: str, min_align: int):
    """Per subject sequence: best identity and bitscore over alignments of at least min_align bp."""
    best = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 12 or line.startswith("#"):
                continue
            try:
                pid, alen, bits = float(f[2]), int(f[3]), float(f[11])
            except ValueError:
                continue
            if alen < min_align:
                continue
            s = _norm_acc(f[1])
            if s not in best or bits > best[s][1]:
                best[s] = (pid, bits)
    return best


def _iter_jsonl(path):
    if not path:
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _norm_designation(x: str) -> str:
    return re.sub(r"[^a-z0-9]", "", x.lower())


def _designations(org, r):
    """All strain designations NCBI records for an assembly: the strain name plus BioSample strain and culture_collection
    entries (split on , ; =). Normalised; tokens shorter than 5 characters are dropped as too ambiguous."""
    bs = {a.get("name"): a.get("value", "") for a in ((r.get("assembly_info") or {}).get("biosample") or {}).get("attributes", [])}
    raw = [(org.get("infraspecific_names") or {}).get("strain", "")] + re.split(r"[,;=]", bs.get("culture_collection", "")) + re.split(r"[,;=]", bs.get("strain", ""))
    return sorted({_norm_designation(t.replace(":", " ")) for t in raw if len(_norm_designation(t)) >= 5})


def load_assemblies(paths):
    """accession -> summary fields, for assembly summary JSON lines (several files allowed)."""
    out = {}
    for p in paths:
        for r in _iter_jsonl(p):
            acc = r.get("accession")
            if not acc:
                continue
            org = r.get("organism", {})
            out[acc] = {
                "organism": org.get("organism_name", ""),
                "strain": (org.get("infraspecific_names") or {}).get("strain", ""),
                "type": (r.get("type_material") or {}).get("type_display_text", ""),
                "level": (r.get("assembly_info") or {}).get("assembly_level", ""),
                "status": (r.get("assembly_info") or {}).get("assembly_status", ""),
                "paired": r.get("paired_accession", ""),
                "biosample": ((r.get("assembly_info") or {}).get("biosample") or {}).get("accession", ""),
                "designations": _designations(org, r),
            }
    return out


def load_sequence_map(paths):
    """sequence accession (GenBank or RefSeq, with and without version) -> set of assembly accessions."""
    m = {}
    for r in (rec for p in paths for rec in _iter_jsonl(p)):
        asm = r.get("assembly_accession")
        for key in ("genbank_accession", "refseq_accession"):
            acc = r.get(key)
            if acc and asm:
                for k in (acc, acc.split(".")[0]):
                    m.setdefault(k, set()).add(asm)
    return m


def strain_keys(info: dict):
    """Keys that identify one physical strain: its BioSample, and organism + strain designation (normalised).
    Two assemblies sharing either key are the same strain sequenced or deposited twice."""
    keys = set()
    if info.get("biosample"):
        keys.add("bs:" + info["biosample"])
    st = re.sub(r"[^a-z0-9]", "", info.get("strain", "").lower())
    sp = " ".join(info.get("organism", "").lower().split()[:2])
    if st and sp:
        keys.add("st:" + sp + ":" + st)
    return keys


def prefer_refseq(accs, assemblies):
    """One accession per assembly pair: GCF if present, else GCA."""
    accs = sorted(accs)
    gcf = [a for a in accs if a.startswith("GCF_")]
    return gcf[0] if gcf else accs[0]


ITAL = re.compile(r"<I>([^<]+)</I>", re.I)


def parse_tygs_subject(cell: str):
    """TYGS subject cell -> (species, strain). Two formats occur:
    HTML  '<I>Streptomyces</I> <I>sulphureus</I> <a ...>DSM 40104</a>'  (bee job table)
    plain 'Streptomyces sampsonii NBRC 13083'                           (moss/attine job table)
    A subspecies ('X y subsp. z') is kept in the species. Returns ('', '') when no binomial can be read."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", cell)).replace('"', " ")
    words = text.split()
    if len(words) < 2 or not re.match(r"^[A-Z][a-z]+$", words[0]) or not re.match(r"^[a-z][a-z-]+$", words[1]):
        return "", ""
    n = 2
    if len(words) >= 4 and words[2] in ("subsp.", "pv.", "var."):
        n = 4
    return " ".join(words[:n]), " ".join(words[n:]).strip()


def read_tygs(paths, isolate: str, top: int):
    rows = []
    want = isolate.lower()
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                if (r.get("comp_type") or "").strip() != "U vs. T":
                    continue
                q = re.sub(r"<[^>]+>|'|\"|\.fna|\.fasta|\s", "", r.get("query_genome", "")).lower()
                if q != want:
                    continue
                try:
                    d4 = float(r.get("digital_ddh_d4", ""))
                except ValueError:
                    continue
                sp, st = parse_tygs_subject(r.get("subject_genome", ""))
                rows.append((d4, sp or ("UNPARSED: " + r.get("subject_genome", "")), st))
    rows.sort(key=lambda x: -x[0])
    seen, out = set(), []
    if top <= 0:
        return out
    for d4, sp, st in rows:
        if (sp, st) in seen:
            continue
        if len(out) >= top and d4 < out[-1][0]:
            break   # rows tied with the last kept d4 are returned too; build() logs those past the cap instead of adding them
        seen.add((sp, st))
        out.append((d4, sp, st))
    return out


def resolve_type_strain(species: str, strain: str, type_asm: dict):
    """Returns (accession, how). First, a type-material assembly of exactly this species (organism name equals the species, or the
    species plus a subspecies or strain), preferring a strain-designation match, then GCF. If none exists under that name, a
    type-material assembly whose recorded strain designations include this TYGS strain designation (with or without a trailing type
    'T'): NCBI may file the same strain under a newer or synonym name. An empty species never resolves."""
    sp = species.lower().strip()
    if not sp or len(sp.split()) < 2:
        return None, ""
    cands = [a for a, v in type_asm.items()
             if v["type"] and v["status"] in ("current", "") and (v["organism"].lower() == sp or v["organism"].lower().startswith(sp + " "))]
    tok = _norm_designation(strain)
    if cands:
        def score(a):
            v = type_asm[a]
            s = _norm_designation(v["strain"])
            return (bool(tok) and bool(s) and (s in tok or tok in s), a.startswith("GCF_"), a)
        return max(cands, key=score), "species name"
    keys = {k for k in (tok, re.sub(r"t$", "", tok)) if len(k) >= 5}
    if not keys:
        return None, ""
    by_des = [a for a, v in type_asm.items() if v["type"] and v["status"] in ("current", "") and keys & set(v.get("designations", []))]
    if not by_des:
        return None, ""
    best = max(by_des, key=lambda a: (a.startswith("GCF_"), a))
    return best, f"strain designation (NCBI name: {type_asm[best]['organism']} {type_asm[best]['strain']})"


def build(args):
    exclude = set()
    if args.exclude:
        with open(args.exclude, encoding="utf-8") as fh:
            exclude = {l.strip() for l in fh if l.strip()}
    asm = load_assemblies([args.assemblies] + list(args.type_assemblies or []))
    type_asm = load_assemblies(args.type_assemblies or []) if args.type_assemblies else {}
    seqmap = load_sequence_map(args.sequences)

    panel, issues, taken = {}, [], {}

    def add(acc, why, **kw):
        """Add or merge one assembly; returns False when it is excluded or duplicates a strain already in the panel."""
        if acc in exclude or acc.split(".")[0] in exclude:
            return False
        if acc not in panel:
            dup = next((taken[k] for k in strain_keys(asm.get(acc, {})) if k in taken), None)
            if dup:
                issues.append(("duplicate_strain", acc, f"same strain as {dup} (shared BioSample or organism + strain); kept {dup}"))
                return False
            for k in strain_keys(asm.get(acc, {})):
                taken[k] = acc
        row = panel.setdefault(acc, {c: "" for c in PANEL_COLUMNS})
        row["ncbi_accession"] = acc
        info = asm.get(acc, {})
        row["organism"] = row["organism"] or info.get("organism", "")
        row["strain"] = row["strain"] or info.get("strain", "")
        row["ncbi_type_material"] = row["ncbi_type_material"] or info.get("type", "")
        row["assembly_level"] = row["assembly_level"] or info.get("level", "")
        for k, v in kw.items():
            if v == "":
                continue
            if not row.get(k):
                row[k] = v
            elif k in ("tygs_type_strain", "tygs_d4") and v not in row[k].split("; "):
                row[k] += "; " + v   # two TYGS designations of one type strain resolving to the same assembly: keep both
        row["why"] = ";".join(sorted(set(filter(None, row["why"].split(";") + [why]))))
        row["source"] = row["why"].split(";")[0]
        return True

    # 1. 16S genome hits, ranked by best identity then bitscore
    hits = read_blast(args.blast, args.min_align) if args.blast else {}
    by_asm = {}
    for s, (pid, bits) in hits.items():
        asms = seqmap.get(s) or seqmap.get(s.split(".")[0])
        if not asms:
            continue
        acc = prefer_refseq(asms, asm)
        if acc in exclude or acc.split(".")[0] in exclude or any(a in exclude for a in asms):
            continue  # excluded before ranking, so it never takes a --top-16s slot
        cur = by_asm.get(acc)
        if cur is None or (pid, bits) > (cur[0], cur[1]):
            by_asm[acc] = (pid, bits, s)
    n_unresolved = sum(1 for s in hits if not (seqmap.get(s) or seqmap.get(s.split(".")[0])))
    if n_unresolved:
        issues.append(("16S_blast", f"{n_unresolved} subject sequences",
                       "no complete/chromosome assembly in the index (16S gene records, partial genes or "
                       "draft genomes); not genome hits"))
    ranked = sorted(by_asm.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]))
    n_added = 0
    for acc, (pid, bits, s) in ranked:   # duplicates of a strain already kept do not use a --top-16s slot
        if n_added >= args.top_16s:
            break
        if add(acc, "16S_genome_hit", best_16S_identity=f"{pid:.2f}", blast_hits=s):
            n_added += 1

    # 2. TYGS closest type strains
    if args.tygs:
        for rank, (d4, sp, st) in enumerate(read_tygs(args.tygs, args.isolate, args.tygs_top), 1):
            if rank > args.tygs_top:
                issues.append(("TYGS", f"{sp} {st}".strip(), f"d4={d4}; tied with the last of the top {args.tygs_top} at this d4 "
                               "but past the --tygs-top cap; not added"))
                continue
            acc, how = resolve_type_strain(sp, st, type_asm)
            if not acc:
                issues.append(("TYGS", f"{sp} {st}".strip(), f"d4={d4}; no type-material assembly by that name or strain designation"))
                continue
            if how != "species name":
                issues.append(("TYGS_resolved_by_designation", f"{sp} {st}".strip(), f"d4={d4}; {acc} by {how}"))
            if not add(acc, "TYGS_type_strain", tygs_type_strain=f"{sp} {st}".strip(), tygs_d4=f"{d4:.1f}"):
                issues.append(("TYGS", f"{sp} {st}".strip(), f"d4={d4}; resolved to {acc} but not added (excluded, or a second "
                               "deposit of a strain already in the panel; see the duplicate_strain line)"))

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "PANEL_TREE.tsv"), "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=PANEL_COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in sorted(panel.values(), key=lambda r: (r["source"], r["ncbi_accession"])):
            w.writerow(row)
    with open(os.path.join(args.out_dir, "PANEL_ISSUES.tsv"), "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(ISSUE_COLUMNS)
        w.writerows(issues)
    n16 = sum(1 for r in panel.values() if "16S_genome_hit" in r["why"])
    nty = sum(1 for r in panel.values() if "TYGS_type_strain" in r["why"])
    emit(f"{args.isolate}: {len(panel)} genomes ({n16} from 16S genome hits, {nty} TYGS type strains); "
         f"{len(issues)} issue rows")
    emit(CLAIM_CEILING)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--isolate", required=True)
    ap.add_argument("--blast", help="NCBI blastn tabular text for the isolate's 16S")
    ap.add_argument("--assemblies", required=True, help="datasets assembly summary JSON lines")
    ap.add_argument("--sequences", required=True, nargs="+", help="datasets --report sequence JSON lines (one or more)")
    ap.add_argument("--type-assemblies", nargs="*", help="datasets --from-type summary JSON lines")
    ap.add_argument("--tygs", nargs="*", help="TYGS digital DDH table(s)")
    ap.add_argument("--top-16s", type=int, default=100)
    ap.add_argument("--tygs-top", type=int, default=10)
    ap.add_argument("--min-align", type=int, default=600, help="minimum 16S alignment length in bp (default 600)")
    ap.add_argument("--exclude", help="file of accessions never to add (e.g. the isolate's own records)")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    if args.top_16s < 0 or args.tygs_top < 0:
        ap.error("--top-16s and --tygs-top must be >= 0")
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
