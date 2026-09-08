"""Tests for cluster_discovery (v9.7.300) — network-free via an injected fake Net."""
import importlib.util, tempfile
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cluster_discovery.py"


def _load():
    spec = importlib.util.spec_from_file_location("cd", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


# --- realistic fixtures (shape mirrors NCBI output) ---
BLAST_TEXT = """
Some header lines
Sequences producing significant alignments:                      (Bits)  Value

WP_384927240.1 B12-binding domain-containing radical SAM prote...  735     0.0    79%
WP_411146105.1 B12-binding domain-containing radical SAM prote...  733     0.0    78%
MCM3806929.1 radical SAM protein [Streptomyces malaysiensis]       720     0.0    55%

>WP_384927240.1 details follow...
"""

IPG_TEXT = "\t".join(["Id", "Source", "Nucleotide Accession", "Start", "Stop", "Strand",
                      "Protein", "Protein Name", "Organism", "Strain", "Assembly"]) + "\n" + \
    "\t".join(["1", "RefSeq", "NZ_X.1", "1", "900", "+", "WP_384927240.1", "radical SAM",
               "Streptomyces sp. NPDC059092", "NPDC059092", "GCF_042756365.1"]) + "\n"


class FakeNet:
    def blast_put(self, seq, entrez, evalue, hitlist): return "RID_TEST"
    def blast_ready(self, rid): return "READY"
    def blast_hits(self, rid): return BLAST_TEXT
    def ipg(self, acc): return IPG_TEXT


def test_parse_blast_hits():
    m = _load()
    hits = m.parse_blast_hits(BLAST_TEXT)
    accs = {a for a, _ in hits}
    assert "WP_384927240.1" in accs and "MCM3806929.1" in accs
    ident = dict(hits)
    assert ident["WP_384927240.1"] == 79


def test_parse_ipg():
    m = _load()
    rows = m.parse_ipg(IPG_TEXT)
    assert rows and rows[0][0] == "GCF_042756365.1"
    assert "NPDC059092" in rows[0][1]


def test_discover_end_to_end_mocked():
    m = _load()
    ranked = m.discover("MSEQ", FakeNet(), min_identity=60, max_strains=10, log=lambda *a: None)
    # 79% and 55% hits; min_identity 60 keeps only the 79% one
    assert len(ranked) == 1
    assert ranked[0]["assembly"] == "GCF_042756365.1"
    assert ranked[0]["marker_identity_pct"] == 79


def test_write_table(tmp_path):
    m = _load()
    ranked = m.discover("MSEQ", FakeNet(), min_identity=0, max_strains=10, log=lambda *a: None)
    p = m.write_table(ranked, str(tmp_path))
    assert Path(p).exists()
    assert (tmp_path / "download_genomes.sh").exists()
    assert "GCF_042756365.1" in (tmp_path / "download_genomes.sh").read_text()
