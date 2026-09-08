#!/usr/bin/env python3
"""build_mibig_index.py — auto-extract a provenance-tagged architecture-signature INDEX from a
MIBiG 4.0 JSON dump (+ protein FASTA for a size proxy).

This is a SEPARATE reference space from the curated reference_bgc_library.json. It is bulk
auto-extracted, NOT hand-curated: no architecture_signature here carries an adjudicated
expected_marker_set or a hard_scan_verdict. Every entry is tagged provenance="MIBiG-4.0-auto"
and carries MIBiG's own quality/completeness/status so downstream scoring stays claim-calibrated.

Deterministic extraction only. Honest blanks (null) where a field is not present in the dump:
  - pks_ks / nrps_a / nrps_c : counted from biosynthesis.modules[].{ks,a,c}_domain; null if the
    entry has no modules block (most entries).
  - size_kb : proxy = max protein end-coordinate in the FASTA for that accession; null if absent.
  - markers : ALWAYS [] — MIBiG GBK/antiSMASH domains are not in this dump, so no T43 marker can
    be asserted. Not inferred. (T43 markers remain an antiSMASH-domain product.)
  - domain_of_life : "unknown" — the dump's taxonomy carries only {name, ncbiTaxId}; no lineage
    offline. likely_eukaryote is a coarse genus heuristic ONLY (false by default), never a claim.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, os, glob, re, collections, datetime
import sys as _sys


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_dump_json, atomic_write_text

# coarse fungal/eukaryote genus heuristic — a convenience flag, NOT a taxonomic determination.
EUK_GENERA = {
    "Aspergillus","Penicillium","Fusarium","Alternaria","Trichoderma","Emericella","Acremonium",
    "Beauveria","Metarhizium","Talaromyces","Colletotrichum","Magnaporthe","Cladosporium","Botrytis",
    "Stachybotrys","Chaetomium","Xylaria","Hypoxylon","Saccharomyces","Claviceps","Cordyceps",
    "Epichloe","Phoma","Pestalotiopsis","Monascus","Ustilago","Neosartorya","Hypocrea","Calcarisporium",
    "Pochonia","Tolypocladium","Sordaria","Phomopsis","Diaporthe","Bipolaris","Cochliobolus","Daldinia",
}

def _classes(b):
    out=[]
    for c in (b.get("classes") or []):
        out.append(c.get("class") if isinstance(c,dict) else c)
    return [c for c in out if c]

def _domain_counts(b):
    """Return (pks_ks, nrps_a, nrps_c) or (None,None,None) when there is no modules block."""
    mods=b.get("modules")
    if not mods: return (None,None,None)
    ks=a=c=0
    for m in mods:
        if not isinstance(m,dict): continue
        t=(m.get("type") or "")
        if t.startswith("pks") and m.get("ks_domain"): ks+=1
        if t.startswith("nrps"):
            if m.get("a_domain"): a+=1
            if m.get("c_domain"): c+=1
    return (ks,a,c)

def _compounds(e):
    out=[]
    for c in (e.get("compounds") or []):
        if isinstance(c,dict):
            nm=c.get("name") or c.get("compound")
            if nm: out.append(nm)
        elif isinstance(c,str):
            out.append(c)
    return out

def _fasta_sizes(fasta):
    """accession (BGC#### w/o version) -> max protein end-coordinate, as a kb size proxy."""
    if not fasta or not os.path.exists(fasta): return {}
    size=collections.defaultdict(int)
    hdr=re.compile(r"^>([^.|>]+)[^|]*\|[^|]*\|(\d+)-(\d+)\|")
    with open(fasta) as fh:
        for line in fh:
            if line[0] != ">": continue
            m=hdr.match(line)
            if not m: continue
            acc=m.group(1); end=int(m.group(3))
            if end>size[acc]: size[acc]=end
    return size


_KS=re.compile(r'/aSDomain="PKS_KS"'); _A=re.compile(r'/aSDomain="AMP-binding"'); _C=re.compile(r'/aSDomain="Condensation"')
_LOC=re.compile(r'^LOCUS\s+\S+\s+(\d+)\s+bp', re.M)
_ORG=re.compile(r'ORGANISM\s+.*?\n((?:\s{2,}\S.*\n)+)')

def _parse_gbk(path):
    try: txt=open(path, encoding="utf-8", errors="replace").read()
    except Exception: return None
    m=_LOC.search(txt); size_kb=round(int(m.group(1))/1000,1) if m else None
    om=_ORG.search(txt); lin=" ".join(l.strip() for l in om.group(1).splitlines()) if om else ""
    dom=(lin.split(";")[0].strip().split() or ["unknown"])[0] if lin else "unknown"
    ks=len(_KS.findall(txt)); a=len(_A.findall(txt)); c=len(_C.findall(txt))
    hal = "halogenase" in txt.lower()
    return {"size_kb": size_kb or None, "pks_ks": ks, "nrps_a": a, "nrps_c": c,
            "domain_of_life": dom, "candidate_markers_esignal": (["halogenase[E-signal]"] if hal else [])}

def _gbk_index(gbk_dir):
    out={}
    if not gbk_dir: return out
    for g in glob.glob(os.path.join(gbk_dir,"**","*.gbk"),recursive=True):
        acc=os.path.splitext(os.path.basename(g))[0].split(".")[0]
        d=_parse_gbk(g)
        if d: out[acc]=d
    return out

def build(json_dir, fasta, out, taxids_out, gbk_dir=None):
    sizes=_fasta_sizes(fasta)
    gbk=_gbk_index(gbk_dir)
    files=sorted(glob.glob(os.path.join(json_dir,"**","*.json"),recursive=True))
    entries=[]; taxids=set(); cov=collections.Counter()
    for f in files:
        try: e=_read_json(f)
        except Exception: continue
        acc=e.get("accession") or os.path.splitext(os.path.basename(f))[0]
        b=e.get("biosynthesis",{}) or {}
        classes=_classes(b)
        jks,ja,jc=_domain_counts(b)
        gb=gbk.get(acc)
        tax=e.get("taxonomy",{}) or {}
        name=tax.get("name") or ""; taxid=tax.get("ncbiTaxId")
        if taxid: taxids.add(taxid)
        genus=(name.split() or [""])[0]
        # prefer GBK aSDomain counts (cover 2,636) over JSON modules (667); honest blanks otherwise
        if gb:
            ks = gb["pks_ks"]; a = gb["nrps_a"]; c = gb["nrps_c"]
            size_kb = gb["size_kb"] if gb["size_kb"] else (round(sizes.get(acc,0)/1000,1) or None)
            dom_life = gb["domain_of_life"]; cand_mk = gb["candidate_markers_esignal"]
            counts_src = "gbk_asdomain"
        else:
            ks,a,c = jks,ja,jc
            size_kb = round(sizes.get(acc,0)/1000,1) or None
            dom_life = "unknown"; cand_mk = []
            counts_src = "json_modules" if jks is not None else None
        has_mod = ks is not None
        cov["class"]+=bool(classes); cov["size"]+=bool(size_kb); cov["modules"]+=bool(has_mod)
        entries.append({
            "accession": acc,
            "compounds": _compounds(e),
            "architecture_signature": {
                "region": ";".join(sorted(set(classes))),
                "pks_ks": ks, "nrps_c": c, "nrps_a": a,
                "markers": [],                  # not assertable without antiSMASH domains
                "size_kb": size_kb, "size_kb_is_proxy": (gb is None and bool(size_kb)),
            },
            "subclasses": sorted({(x.get("subclass") if isinstance(x,dict) else None) for x in (b.get("classes") or []) if isinstance(x,dict) and x.get("subclass")}),
            "expected_marker_set": [],          # no curated adjudication for auto entries
            "marker_divergence_note": "NOT_CURATED_AUTO",
            "taxonomy": {"name": name, "ncbiTaxId": taxid,
                         "domain_of_life": dom_life,
                         "likely_eukaryote": genus in EUK_GENERA},
            "candidate_markers_esignal": cand_mk,
            "domain_counts_source": counts_src,
            "mibig_quality": e.get("quality"),
            "mibig_completeness": e.get("completeness"),
            "mibig_status": e.get("status"),
            "provenance": "MIBiG-4.0-auto",
            "signature_completeness": "modules+size" if (has_mod and size_kb) else ("modules" if has_mod else ("size" if size_kb else "class-only")),
        })
    idx={"schema_version":"mibig-index-0.1","provenance":"MIBiG-4.0-auto",
         "generated":datetime.date.today().isoformat(),
         "note":"Bulk auto-extracted reference space; SEPARATE from the curated reference_bgc_library.json. "
                "Partial signatures by design (honest blanks). markers always [] (no antiSMASH domains in dump). "
                "domain_of_life unknown offline; filter to Bacteria downstream via the taxid sidecar.",
         "n":len(entries),"entries":entries}
    atomic_dump_json(idx, out, indent=1)
    if taxids_out:
        atomic_write_text(taxids_out, "".join(f"{t}\n" for t in sorted(taxids)))
    return idx, cov

def main(argv=None):
    ap=argparse.ArgumentParser(description="Build a provenance-tagged MIBiG 4.0 architecture-signature index.")
    ap.add_argument("--json-dir",required=True); ap.add_argument("--fasta",default=None)
    ap.add_argument("--out",default="mibig_reference_index.json")
    ap.add_argument("--taxids-out",default=None)
    ap.add_argument("--gbk-dir",default=None)
    ap.add_argument("--bacterial-out",default=None)
    a=ap.parse_args(argv)
    idx,cov=build(a.json_dir,a.fasta,a.out,a.taxids_out,a.gbk_dir)
    n=idx["n"]
    emit(f"  wrote {n} entries -> {a.out}")
    bact=[e for e in idx["entries"] if e["taxonomy"]["domain_of_life"]=="Bacteria"]
    emit(f"  coverage: class {cov['class']}/{n} · size {cov['size']}/{n} · domain-counts {cov['modules']}/{n} · Bacteria {len(bact)}")
    if a.bacterial_out:
        import copy; bidx=dict(idx); bidx["entries"]=bact; bidx["n"]=len(bact); bidx["filter"]="domain_of_life==Bacteria (GBK lineage)"
        atomic_dump_json(bidx, a.bacterial_out, indent=1); emit(f"  wrote {len(bact)} bacterial entries -> {a.bacterial_out}")
    return 0

if __name__=="__main__": raise SystemExit(main())
