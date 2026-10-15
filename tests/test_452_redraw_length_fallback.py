"""gap_directed_rescue --redraw passes --length-fallback to the gene-name loader; the default is unchanged.

A name row with no checksum and an empty aa_length binds by tag only when the column named by --length-fallback agrees
with the genome's protein within 1 aa. Synthetic SYN-972 data only.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import gap_directed_rescue as gdr  # noqa: E402
from gap_rescue_locus_map import load_gene_names  # noqa: E402

COLS = ["strain", "bgc_id", "gene", "aa_length", "db", "n_hits", "top_hit_identity", "top10_mean_identity",
        "top10_consensus_name", "consensus_share", "function_class", "function_class_ambiguous", "top_hit_def",
        "top_hit_organism", "source", "source_file", "protein_sha256", "query_aa_length", "binding_evidence"]


def _table(tmp_path, rows):
    p = tmp_path / "names.tsv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    return p


def _row(gene, qlen, name):
    return {"strain": "SYN-972", "gene": gene, "db": "nr", "n_hits": "10", "top10_mean_identity": "80.0",
            "top10_consensus_name": name, "consensus_share": "9 of 10", "function_class": "tailoring",
            "function_class_ambiguous": "no", "query_aa_length": str(qlen), "binding_evidence": "xml_query_length"}


def _run_main(monkeypatch, tmp_path, extra):
    seen = {}

    def fake_loader(paths, strain, prots=None, prefer_db=None, length_fallback=None):
        seen["length_fallback"] = length_fallback
        return {}

    monkeypatch.setattr(gdr, "load_gene_names", fake_loader)
    monkeypatch.setattr(gdr, "load_genome", lambda z, label: ({}, []))
    monkeypatch.setattr(gdr, "redraw", lambda *a, **k: None)
    monkeypatch.setattr(gdr, "assert_output_outside_bundle", lambda *a, **k: None, raising=False)
    names = _table(tmp_path, [])
    argv = ["--redraw", str(tmp_path), "--zip", str(tmp_path / "syn.zip"), "--label", "SYN-972",
            "--mibig-dir", str(tmp_path), "--out", str(tmp_path / "out"), "--gene-names", str(names)] + extra
    assert gdr.main(argv) == 0
    return seen


def test_default_passes_no_fallback(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, tmp_path, [])["length_fallback"] is None


def test_flag_reaches_the_loader(monkeypatch, tmp_path):
    seen = _run_main(monkeypatch, tmp_path, ["--length-fallback", "query_aa_length"])
    assert seen["length_fallback"] == "query_aa_length"


def test_fallback_binds_within_one_aa_only(tmp_path):
    prots = {t: {"tag": t, "aa": "M" * 300} for t in ("syn1_1", "syn1_2", "syn1_3")}
    p = _table(tmp_path, [_row("syn1_1", 300, "near name"), _row("syn1_2", 301, "within one"),
                          _row("syn1_3", 450, "another protein")])
    off = load_gene_names([p], "SYN-972", prots)
    on = load_gene_names([p], "SYN-972", prots, length_fallback="query_aa_length")
    assert not off
    assert set(on) == {"syn1_1", "syn1_2"}
