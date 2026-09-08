#!/usr/bin/env python3
"""Ingest NCBI/EBI BLASTp results (XML + HitTable CSV, or CSV-only) into the two
canonical homes, channel-safe and merge-safe.

  1. BLASTp Repository/<strain>/<BGC>/   per-BGC top10 + top-hit-per-gene CSVs
  2. strain_data/<strain>/blastp_<channel>_<date>/   per-strain rollup (channel-tagged)

DESIGN INVARIANTS (do not weaken):
  * Channels are NEVER mixed. Channel is auto-detected from the XML <db> tag and
    each channel writes to its own filenames + its own master rollup dir.
      nr           -> _top10_blastp_nr.csv / _top_hit_per_gene.csv / blastp_nr_<date>/
      swissprot    -> _top10_blastp_swissprot.csv / ...             / blastp_swissprot_<date>/
      clustered_nr -> _blastp_top10_clustered.csv                   / blastp_clustered_nr_<date>/
    A CSV whose paired XML declares a different db than --channel is REFUSED.
  * pct_identity and pct_positives are always separate columns.
  * AS-XXX (contaminated) and AS-XXX (chimeric) are hard-excluded, always.
  * Per-gene MERGE: new rows replace existing rows for the SAME gene; every other
    gene in the BGC is preserved untouched. Existing sibling genes never clobbered.
  * Identical (strain,bgc,gene) across two input files is deduped (first wins).

Query title convention (required): "<strain>__<BGC>__<gene>", e.g. AS-XXX__BGC001__ctg10_30.

USAGE
  python ingest_blastp.py                      # ingest every un-archived pair in _raw/
  python ingest_blastp.py --dry-run            # report only, write nothing
  python ingest_blastp.py --archive            # move ingested pairs to _raw/_ingested_<date>/
  python ingest_blastp.py --channel nr         # force channel (default: auto from <db>)
  python ingest_blastp.py --raw <dir> --ids A B C   # restrict to specific base IDs
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import csv, os, re, sys, glob, argparse, datetime
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
import os as _os, sys as _sys  # bundle-root path guard (see tests/test_tool_front_doors.py)
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
try:  # cohort exclusions come from the governed SSOT, never hardcoded here
    from mamey.exclusions import raw_analysis_excluded
    EXCLUDE = raw_analysis_excluded()
except Exception as _exc:  # pragma: no cover - standalone use without mamey
    raise RuntimeError(
        "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
    ) from _exc
DB_TO_CHANNEL = {"nr":"nr", "swissprot":"swissprot", "swiss-prot":"swissprot",
                 "nr_cluster_seq":"clustered_nr", "clustered_nr":"clustered_nr"}
# per-channel output naming
REPO_TOP10 = {"nr":"{bgc}_top10_blastp_nr.csv",
              "swissprot":"{bgc}_top10_blastp_swissprot.csv",
              "clustered_nr":"{bgc}_blastp_top10_clustered.csv"}
REPO_TOPHIT = {"nr":"{bgc}_top_hit_per_gene.csv",
               "swissprot":"{bgc}_swissprot_top_hit_per_gene.csv",
               "clustered_nr":"{bgc}_clustered_top_hit_per_gene.csv"}
REPO_HDR = ["strain","bgc_id","gene","aa_length","role","domains","hit_rank",
            "subject_acc","subject_organism","subject_def","pct_identity",
            "align_length","query_coverage","evalue","bitscore","pct_positives"]
ROLL_HDR = REPO_HDR + ["channel","provenance"]

def local(t): return t.rsplit('}',1)[-1]
def stem(acc): return acc.rsplit(".",1)[0] if acc else acc

def xml_db(xml_path):
    """Return declared db string (lowercased) or None."""
    try:
        for ev, el in ET.iterparse(xml_path, events=("end",)):
            if local(el.tag) == "db" and el.text:
                return el.text.strip().lower()
    except Exception:
        pass
    return None

def xml_hit_map(xml_path):
    """accession(no-version) -> (sciname, title) from the first HitDescr of each hit."""
    m = {}
    if not xml_path or not os.path.exists(xml_path): return m
    try: tree = ET.parse(xml_path)
    except Exception: return m
    for hit in tree.iter():
        if local(hit.tag) != 'Hit': continue
        for hd in hit.iter():
            if local(hd.tag) == 'HitDescr':
                acc = sci = title = None
                for ch in hd:
                    lt = local(ch.tag)
                    if lt=='accession': acc=(ch.text or '').strip()
                    elif lt=='sciname': sci=(ch.text or '').strip()
                    elif lt=='title':   title=(ch.text or '').strip()
                if acc: m[acc]=(sci or '', title or '')
                break
    return m

def load_existing(path):
    genes = OrderedDict()
    if os.path.exists(path):
        with open(path, newline='') as f:
            for row in csv.DictReader(f):
                genes.setdefault(row.get('gene',''), []).append(row)
    return genes

def discover(raw):
    ids=set()
    for p in glob.glob(os.path.join(raw,"*-Alignment-HitTable.csv")):
        ids.add(os.path.basename(p)[:-len("-Alignment-HitTable.csv")])
    for p in glob.glob(os.path.join(raw,"*-Alignment.xml")):
        ids.add(os.path.basename(p)[:-len("-Alignment.xml")])
    return sorted(ids)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(ROOT,"BLASTp Repository","_raw"))
    ap.add_argument("--repo", default=os.path.join(ROOT,"BLASTp Repository"))
    ap.add_argument("--master", default=os.path.join(ROOT,"strain_data"))
    ap.add_argument("--channel", default="auto", choices=["auto","nr","swissprot","clustered_nr"])
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--ids", nargs="*", help="restrict to these base IDs")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--archive", action="store_true", help="move ingested pairs to _raw/_ingested_<date>/")
    a = ap.parse_args()

    ids = a.ids if a.ids else discover(a.raw)
    if not ids:
        emit("no input pairs found in", a.raw); return

    # channel resolve (must be single-channel per run to keep files unmixed)
    channels_seen = set(); per_id_channel = {}
    for base in ids:
        xmlp = os.path.join(a.raw, base+"-Alignment.xml")
        db = xml_db(xmlp) if os.path.exists(xmlp) else None
        ch = DB_TO_CHANNEL.get(db) if db else None
        if a.channel != "auto":
            if ch and ch != a.channel:
                emit(f"REFUSE: {base} db='{db}' -> {ch} but --channel {a.channel}. Channels must not mix."); return
            ch = a.channel
        if not ch:
            emit(f"REFUSE: {base} has no detectable db tag; pass --channel explicitly."); return
        per_id_channel[base]=ch; channels_seen.add(ch)
    if len(channels_seen) > 1:
        emit("REFUSE: mixed channels in one run:", channels_seen, "- run one channel at a time."); return
    channel = channels_seen.pop()

    newrepo = defaultdict(lambda: OrderedDict())   # (strain,bgc)->gene->rows
    seen = {}; report=[]; ingested_ids=[]
    for base in ids:
        csvp = os.path.join(a.raw, base+"-Alignment-HitTable.csv")
        xmlp = os.path.join(a.raw, base+"-Alignment.xml")
        if not os.path.exists(csvp):
            report.append((base,"MISSING CSV",0,0)); continue
        xmap = xml_hit_map(xmlp)
        per=OrderedDict()
        with open(csvp, newline='') as f:
            for cols in csv.reader(f):
                if not cols or len(cols)<12: continue
                parts=cols[0].split("__")
                if len(parts)!=3: continue
                strain,bgc,gene=parts
                if strain in EXCLUDE: continue
                sci,title=xmap.get(stem(cols[1]),("",""))
                per.setdefault((strain,bgc,gene),[]).append(dict(
                    subject_acc=cols[1],pct_identity=cols[2],align_length=cols[3],
                    evalue=cols[10],bitscore=cols[11],
                    pct_positives=cols[12] if len(cols)>12 else "",
                    subject_organism=sci,subject_def=title))
        ng=len(per); nr=sum(len(v) for v in per.values())
        report.append((base,f"ok[{channel}]",ng,nr)); ingested_ids.append(base)
        for (strain,bgc,gene),hits in per.items():
            if (strain,bgc,gene) in seen:
                report.append((base,f"DUP of {seen[(strain,bgc,gene)]} ({strain} {bgc} {gene}) skipped",0,0)); continue
            seen[(strain,bgc,gene)]=base
            rows=[]
            for rank,h in enumerate(hits[:10],1):
                rows.append(OrderedDict([
                    ("strain",strain),("bgc_id",bgc),("gene",gene),
                    ("aa_length",h["align_length"]),("role",""),("domains",""),
                    ("hit_rank",str(rank)),("subject_acc",h["subject_acc"]),
                    ("subject_organism",h["subject_organism"]),("subject_def",h["subject_def"]),
                    ("pct_identity",h["pct_identity"]),("align_length",""),("query_coverage",""),
                    ("evalue",h["evalue"]),("bitscore",h["bitscore"]),("pct_positives",h["pct_positives"]),
                ]))
            newrepo[(strain,bgc)][gene]=rows

    # ---- report ----
    emit(f"=== INGEST channel={channel} date={a.date} dry_run={a.dry_run} ===")
    for base,st,ng,nr in report: emit(f"  {base:14s} {st:44s} genes={ng} rows={nr}")
    tot=sum(len(g) for g in newrepo.values())
    emit(f"  -> {tot} unique genes / {len(newrepo)} BGC dirs / "
          f"{len({s for s,_ in newrepo})} strains")
    if a.dry_run:
        emit("DRY RUN — nothing written."); return

    # ---- write repository per-BGC (merge) ----
    top10_t, tophit_t = REPO_TOP10[channel], REPO_TOPHIT[channel]
    for (strain,bgc),genes in sorted(newrepo.items()):
        d=os.path.join(a.repo,strain,bgc); os.makedirs(d,exist_ok=True)
        for fname,rankone in ((top10_t,False),(tophit_t,True)):
            p=os.path.join(d,fname.format(bgc=bgc)); ex=load_existing(p)
            for g,rows in genes.items(): ex[g]=[rows[0]] if rankone else rows
            with open(p,"w",newline='') as f:
                w=_SafeDictWriter(f,fieldnames=REPO_HDR); w.writeheader()
                for g,rows in ex.items():
                    for row in rows: w.writerow({k:row.get(k,"") for k in REPO_HDR})

    # ---- write master rollup (dated, additive) ----
    bystrain=defaultdict(list)
    for (strain,bgc),genes in newrepo.items():
        for g,rows in genes.items(): bystrain[strain].append((bgc,g,rows))
    for strain,items in sorted(bystrain.items()):
        outdir=os.path.join(a.master,strain,f"blastp_{channel}_{a.date}"); os.makedirs(outdir,exist_ok=True)
        items.sort(key=lambda x:(x[0],x[1]))
        p10=os.path.join(outdir,f"{strain}_{channel}_top10_{a.date}.csv")
        pth=os.path.join(outdir,f"{strain}_{channel}_top_hit_per_gene_{a.date}.csv")
        with open(p10,"w",newline='') as f10, open(pth,"w",newline='') as fth:
            w10=_SafeDictWriter(f10,fieldnames=ROLL_HDR); w10.writeheader()
            wth=_SafeDictWriter(fth,fieldnames=ROLL_HDR); wth.writeheader()
            for bgc,g,rows in items:
                for i,row in enumerate(rows):
                    out={k:row.get(k,"") for k in REPO_HDR}
                    out["align_length"]=out["aa_length"]; out["aa_length"]=""
                    out["channel"]="ncbi_nr" if channel=="nr" else channel
                    out["provenance"]=f"_raw/{seen[(strain,bgc,g)]}-Alignment-HitTable.csv"
                    w10.writerow(out)
                    if i==0: wth.writerow(out)

    # ---- ingest log ----
    logdir=os.path.join(a.repo,"_ingest_logs"); os.makedirs(logdir,exist_ok=True)
    logp=os.path.join(logdir,f"ingest_{a.date}_{channel}.md")
    with open(logp,"a") as f:
        f.write(f"\n## ingest {a.date} channel={channel} ({tot} genes, "
                f"{len(newrepo)} BGCs, {len({s for s,_ in newrepo})} strains)\n")
        for (strain,bgc),genes in sorted(newrepo.items()):
            f.write(f"- {strain} {bgc}: {' '.join(genes)}\n")
    emit(f"log -> {logp}")

    # ---- archive ----
    if a.archive:
        dest=os.path.join(a.raw,f"_ingested_{a.date}"); os.makedirs(dest,exist_ok=True)
        moved=0
        for base in ingested_ids:
            for suf in ("-Alignment.xml","-Alignment-HitTable.csv"):
                src=os.path.join(a.raw,base+suf)
                if os.path.exists(src): os.rename(src,os.path.join(dest,base+suf)); moved+=1
        emit(f"archived {moved} files -> {dest}")
    emit(f"DONE: {tot} genes ingested (channel {channel}).")

if __name__=="__main__":
    main()
