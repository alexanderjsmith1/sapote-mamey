#!/usr/bin/env python3
"""cluster_discovery — candidate assembly lookup from marker-protein similarities.

An injectable BLAST/IPG service maps homolog proteins to candidate assemblies.
This lookup does not establish cluster presence or physical linkage. Review
candidate identities before any separately authorized downstream download or
analysis. No --verify option is implemented.

Incomplete search, result parsing or assembly resolution raises DiscoveryFailure;
the CLI returns 2 without writing a completed candidate table. Partial rows are
incomplete evidence. A completed empty result does not establish biological absence.
"""
import argparse, csv, io, json, sys, time, urllib.parse, urllib.request
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path


# ----------------------------------------------------------------- network (injectable/mockable)
class Net:
    """Thin wrapper over the NCBI URL APIs. Replace in tests with a fake."""
    BLAST = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
    EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, timeout=90, poll=20):
        self.timeout = timeout; self.poll = poll

    def _get(self, url, data=None):
        req = urllib.request.Request(url, data=data)
        return urllib.request.urlopen(req, timeout=self.timeout).read().decode()

    def blast_put(self, seq, entrez, evalue, hitlist):
        params = {"CMD": "Put", "PROGRAM": "blastp", "DATABASE": "nr",
                  "QUERY": seq, "HITLIST_SIZE": str(hitlist), "EXPECT": str(evalue)}
        if entrez:
            params["ENTREZ_QUERY"] = entrez
        html = self._get(self.BLAST, urllib.parse.urlencode(params).encode())
        import re
        m = re.search(r"RID = (\S+)", html)
        return m.group(1) if m else None

    def blast_ready(self, rid):
        import re
        html = self._get(self.BLAST + "?" + urllib.parse.urlencode(
            {"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"}))
        m = re.search(r"Status=(\w+)", html)
        return (m.group(1) if m else "UNKNOWN")

    def blast_hits(self, rid):
        txt = self._get(self.BLAST + "?" + urllib.parse.urlencode(
            {"CMD": "Get", "RID": rid, "FORMAT_TYPE": "Text", "DESCRIPTIONS": "150", "ALIGNMENTS": "0"}))
        return txt

    def ipg(self, acc):
        return self._get(self.EUTILS + "/efetch.fcgi?" + urllib.parse.urlencode(
            {"db": "protein", "id": acc, "rettype": "ipg", "retmode": "text"}))


# ----------------------------------------------------------------- parsing helpers
def parse_blast_hits(text):
    """Parse the 'Sequences producing significant alignments' block -> [(acc, identity_pct)]."""
    import re
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if "Sequences producing" in l), None)
    if start is None:
        return []
    out = []
    for l in lines[start + 1:]:
        if l.startswith(">") or (not l.strip() and out):
            break
        # trailing columns: ... score  evalue  ident%   accession(sometimes)
        m = re.search(r"\b([A-Z]{2,}_?\d+\.\d)\b", l)  # accession
        pid = re.search(r"(\d+)%\s*$", l.strip())
        if m and pid:
            out.append((m.group(1), int(pid.group(1))))
    return out


def parse_ipg(text):
    """IPG table -> [(assembly, organism, strain)] with GCF/GCA assemblies only."""
    rows = [l.split("\t") for l in text.strip().split("\n") if l.strip()]
    if len(rows) < 2:
        return []
    hdr = rows[0]
    def idx(name): return hdr.index(name) if name in hdr else None
    ai, oi, si = idx("Assembly"), idx("Organism"), idx("Strain")
    out = []
    seen = set()
    for r in rows[1:]:
        if ai is not None and len(r) > ai and r[ai].startswith(("GCF_", "GCA_")):
            key = r[ai]
            if key in seen:
                continue
            seen.add(key)
            out.append((r[ai],
                        r[oi] if oi is not None and len(r) > oi else "",
                        r[si] if si is not None and len(r) > si else ""))
    return out


# ----------------------------------------------------------------- pipeline
class DiscoveryFailure(RuntimeError):
    """An incomplete interaction must not become completed empty evidence."""
    def __init__(self, status, message, *, rid=None, partial_rows=()):
        super().__init__(f"{status}: {message}")
        self.status = status
        self.rid = rid
        self.partial_rows = list(partial_rows)


def discover(marker_seq, net, entrez="Streptomyces[Organism]", evalue=1e-40,
             hitlist=100, min_identity=0, max_strains=50, log=print):
    rid = net.blast_put(marker_seq, entrez, evalue, hitlist)
    if not rid:
        raise DiscoveryFailure("SUBMISSION_FAILED", "BLAST submission failed (no RID)")
    log(f"[cluster_discovery] BLAST RID {rid}; polling...")
    for _ in range(60):
        st = net.blast_ready(rid)
        if st == "READY":
            break
        if st == "FAILED" or st == "UNKNOWN":
            raise DiscoveryFailure("SEARCH_FAILED", f"BLAST status {st}", rid=rid)
        time.sleep(net.poll)
    else:
        raise DiscoveryFailure("TIMEOUT", "no READY state in 60 polls", rid=rid)
    response = net.blast_hits(rid)
    hits = parse_blast_hits(response)
    import re
    no_hits = any(re.fullmatch(r"\s*\*+\s*No hits found\s*\*+\s*", line)
                  for line in response.splitlines())
    if (not hits and not no_hits) or (hits and no_hits):
        raise DiscoveryFailure("RESULT_PARSE_UNVERIFIED", "no parsed hits or recognized no-hit response", rid=rid)
    hits = [(a, p) for a, p in hits if p >= min_identity]
    log(f"[cluster_discovery] {len(hits)} marker homolog(s) >= {min_identity}% identity")
    # map each hit protein -> assemblies (IPG); keep best marker identity per assembly
    strains = {}   # assembly -> (organism, strain, best_identity, protein_acc)
    unresolved = []
    for acc, pid in hits:
        try:
            response = net.ipg(acc)
            header = response.splitlines()[0].split("\t") if response.splitlines() else []
            if "Assembly" not in header:
                raise ValueError("IPG response has no Assembly column")
            resolved = parse_ipg(response)
            if not resolved:
                raise ValueError("IPG response resolved no admitted assembly")
            for asm, org, strain in resolved:
                if asm not in strains or pid > strains[asm][2]:
                    strains[asm] = (org, strain, pid, acc)
        except Exception as e:
            unresolved.append(acc)
            log(f"[cluster_discovery]  IPG {acc} skipped: {str(e)[:60]}")
        if len(strains) >= max_strains * 3:
            break
        time.sleep(0.4)
    ranked = sorted(({"assembly": a, "organism": o, "strain": s,
                      "marker_identity_pct": p, "marker_protein": prot}
                     for a, (o, s, p, prot) in strains.items()),
                    key=lambda r: -r["marker_identity_pct"])[:max_strains]
    log(f"[cluster_discovery] {len(ranked)} candidate strain(s)/assembly(ies)")
    if unresolved:
        raise DiscoveryFailure("PARTIAL" if ranked else "ASSEMBLY_UNRESOLVED",
                               "unresolved protein(s): " + ", ".join(unresolved),
                               rid=rid, partial_rows=ranked)
    return ranked


def write_table(ranked, outdir, marker_name="marker"):
    op = Path(outdir); op.mkdir(parents=True, exist_ok=True)
    p = op / "candidate_strains.csv"
    with open(p, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=["assembly", "organism", "strain",
                                           "marker_identity_pct", "marker_protein"])
        w.writeheader()
        w.writerows(ranked)
    # datasets download command for convenience
    accs = " ".join(r["assembly"] for r in ranked if r["assembly"].startswith("GCF_"))[:4000]
    (op / "download_genomes.sh").write_text(
        "#!/bin/sh\n# fetch candidate genomes (requires NCBI 'datasets' CLI)\n"
        f"datasets download genome accession {accs} --include genome\n")
    return str(p)


# ----------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Discover strains carrying a BGC from a marker gene.")
    ap.add_argument("--marker", required=True, help="marker protein FASTA (1 sequence, e.g. nikJ)")
    ap.add_argument("--entrez", default="Streptomyces[Organism]", help="Entrez organism filter")
    ap.add_argument("--evalue", type=float, default=1e-40)
    ap.add_argument("--min-identity", type=float, default=0, help="min %% identity to keep a hit")
    ap.add_argument("--max-strains", type=int, default=50)
    ap.add_argument("--outdir", default="cluster_discovery_out")
    a = ap.parse_args(argv)
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    rec = next(SeqIO.parse(a.marker, "fasta"))
    try:
        ranked = discover(str(rec.seq), Net(), entrez=a.entrez, evalue=a.evalue,
                          min_identity=a.min_identity, max_strains=a.max_strains)
    except DiscoveryFailure as exc:
        print(f"[cluster_discovery] {exc}; no completed candidate table written", file=sys.stderr)
        return 2
    p = write_table(ranked, a.outdir, marker_name=rec.id)
    print(f'[cluster_discovery] wrote {p} ({len(ranked)} strains) + download_genomes.sh', '[cluster_discovery] next: run download_genomes.sh, then extract clusters and compare with cluster_gene_compare.py', sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
