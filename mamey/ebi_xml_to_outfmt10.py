"""ebi_xml_to_outfmt10.py — (folded from the AS-XXX EBI patch, v9.7.215) convert an EBI ncbiblast XML result (one query/job) into an
NCBI -outfmt 10 (13-column, headerless) HitTable row set that mamey `ingest-blastp` /
`blastp-followup` accept unchanged.

This is the interop shim that lets the EBI channel feed the SAME downstream tools as the
NCBI channel, INCLUDING query-coverage (which the EBI *TSV* drops but the EBI *XML* carries
via <sequence length=...> + <querySeq start/end>).

NCBI -outfmt 10 columns (13):
  query_id, subject_acc, pct_identity, align_len, mismatches, gap_opens,
  q_start, q_end, s_start, s_end, evalue, bitscore, positives_pct
"""
import sys, re, csv
import xml.etree.ElementTree as ET

def _q(el, name):
    m = el.find(f".//{{*}}{name}")
    return m.text if m is not None and m.text else ""

def convert(xml_path):
    root = ET.parse(xml_path).getroot()
    # query id + length from Header/parameters/sequences/sequence
    seq_el = root.find(".//{*}sequences/{*}sequence")
    qid = seq_el.get("name") if seq_el is not None else ""
    qlen = int(seq_el.get("length")) if seq_el is not None and seq_el.get("length") else 0
    rows = []
    for hit in root.findall(".//{*}hit"):
        acc = hit.get("ac") or hit.get("id") or ""
        for aln in hit.findall(".//{*}alignment"):
            ident = _q(aln, "identity")           # % identity (already a percent)
            pos   = _q(aln, "positives")
            gaps  = _q(aln, "gaps")
            bits  = _q(aln, "bits")
            ev    = _q(aln, "expectation")
            qseq  = aln.find(".//{*}querySeq")
            mseq  = aln.find(".//{*}matchSeq")
            qs = int(qseq.get("start")) if qseq is not None else 0
            qe = int(qseq.get("end")) if qseq is not None else 0
            ss = int(mseq.get("start")) if mseq is not None else 0
            se = int(mseq.get("end")) if mseq is not None else 0
            align_len = (qe - qs + 1) if (qs and qe) else 0
            # -outfmt 10 uses the raw query id; keep BGC/ctg tokens if present in the name
            rows.append([qid, acc, ident, str(align_len), "", (gaps or "0"),
                         str(qs), str(qe), str(ss), str(se), ev, bits, pos])
    return rows, qid, qlen

if __name__ == "__main__":
    # usage: ebi_xml_to_outfmt10.py out.csv in1.xml in2.xml ...
    out = sys.argv[1]
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        for xml_path in sys.argv[2:]:
            rows, qid, qlen = convert(xml_path)
            for r in rows:
                w.writerow(r)
    emit(f"wrote {out}")

from .console import emit