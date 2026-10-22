"""tools/gap_rescue_gene_table.py: gene_table.tsv gives each strain protein's contig, start, end and strand.

Locus write-ups need gene coordinates (a region span, the distance between two genes). The table had none, so they were
copied from other documents. Coordinates come from the genome records the run read: 1-based start, inclusive end, the
full contig name, strand + or − (as the genes-in-the-window table). A split row lists both pieces joined by " + ", as
its CDS cell does; its strand reads "piece 1 +; piece 2 −", because the CSV guard quotes a cell that starts with +.
A not-found row, or a table written without the genome's proteins, leaves them blank. Positions are bound by locus tag,
never by the run's own protein id (q000001...), which shifts when a replay reads a re-annotated zip. A tag that is
missing, held by two CDS, or whose protein length or contig disagrees with the saved run gets blank cells and a
POSITION_HOLD note; another gene's position is never borrowed. The drawn table keeps its nine columns. Synthetic data
only.
"""
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_rescue_gene_table as gt  # noqa: E402
from tests.test_450_gap_rescue_fresh_split_families import fresh_saved_split  # noqa: E402,F401

C1, C2 = "NODE_1_length_9000_cov_10.012345", "NODE_2_length_8000_cov_9.5"
CORE = f"SYNTHETIC / {C1} / region001 / BGC001"
PROTS = {   # as gap_directed_rescue.load_genome returns them: 0-based start, end exclusive, strand 1 / -1
    "q000001": {"tag": "gene_a", "contig": C1, "start": 999, "end": 1900, "strand": 1, "family": "KS", "aa": "M" * 300},
    "q000002": {"tag": "gene_b", "contig": C2, "start": 99, "end": 700, "strand": -1, "family": "", "aa": "M" * 200},
    "q000003": {"tag": "gene_c", "contig": C2, "start": 4999, "end": 5600, "strand": -1, "family": "", "aa": "M" * 300},
}


def _row(n, name, status, tag="", pid="", contig=""):
    return dict(reference_gene=str(n), name=name, status=status, reference_len_aa="300", best_len_aa="300" if tag else "",
                best_locus=tag, best_protein=pid, best_identity_pct="60" if tag else "", reciprocal_best="True",
                best_contig=contig, best_region_identity=CORE if status == "PRESENT_IN_CORE" else "",
                partner_verdict="SUPPORTED" if status.startswith("MISSING_FOUND") else "")


ROWS = [_row(1, "ref_a", "PRESENT_IN_CORE", "gene_a", "q000001", C1),
        _row(2, "ref_b", "MISSING_FOUND_CLEAR", "gene_c", "q000003", C2),
        _row(3, "ref_c", "MISSING_NOT_FOUND"),
        _row(4, "ref_d", "MISSING_NOT_FOUND")]
SPLIT = dict(reference_gene="4", name="ref_d", status="SPLIT_ACROSS_CONTIG_ENDS", split_call="CLEAR",
             piece1_locus="gene_a", piece2_locus="gene_b", piece1_region_identity=CORE,
             piece2_region_identity=f"SYNTHETIC / {C2} (no antiSMASH region)",
             piece1_identity_pct="70", piece2_identity_pct="65")


def _write(tmp_path, monkeypatch, rows=ROWS, **kw):
    drawn = {}
    monkeypatch.setattr(gt, "reference_annotations", lambda reference: {})
    monkeypatch.setattr(gt, "_draw", lambda table, *a, **k: drawn.setdefault("table", table) and False)
    monkeypatch.setattr(gt, "pair_with_map", lambda out: [])
    gt.write_gene_table(tmp_path, rows, [SPLIT], CORE, "SYNTHETIC", Path("BGC_REF.gbk"), {},
                        known_tags={"gene_a", "gene_b", "gene_c"}, **kw)
    with (tmp_path / "gene_table.tsv").open(newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return reader.fieldnames, {r["Reference gene"]: r for r in reader}, drawn


def test_position_columns_follow_the_display_columns():
    assert gt.POSITION_COLS == ["Contig", "Start", "End", "Strand", "Position note"]


def test_found_rows_carry_contig_start_end_and_strand(tmp_path, monkeypatch):
    head, rows, _ = _write(tmp_path, monkeypatch, prots=PROTS)
    assert head == gt.COLS + gt.POSITION_COLS
    pos = lambda r: [rows[r][k] for k in gt.POSITION_COLS]
    assert pos("ref_a") == [C1, "1000", "1900", "+", ""]      # core gene
    assert pos("ref_b") == [C2, "5000", "5600", "−", ""]      # found on another contig
    assert pos("ref_c") == ["", "", "", "", ""]               # not found: no position
    assert pos("ref_d") == [f"{C1} + {C2}", "1000 + 100", "1900 + 700", "piece 1 +; piece 2 −", ""]   # split
    assert rows["ref_d"]["CDS"] == "gene_a + gene_b"


def _shifted():
    """The same genome re-annotated: a new CDS (gene_x) first, so every run-local protein id moves by one."""
    shifted = {"q000001": {"tag": "gene_x", "contig": C1, "start": 0, "end": 300, "strand": 1, "family": "",
                           "aa": "M" * 100}}
    for i, p in enumerate(PROTS.values(), 2):
        shifted[f"q{i:06d}"] = dict(p)
    return shifted


def test_a_shifted_protein_id_never_lends_its_position(tmp_path, monkeypatch):
    _, rows, _ = _write(tmp_path, monkeypatch, prots=_shifted())   # saved rows still say gene_a = q000001
    assert [rows["ref_a"][k] for k in gt.POSITION_COLS] == [C1, "1000", "1900", "+", ""]
    assert [rows["ref_b"][k] for k in gt.POSITION_COLS] == [C2, "5000", "5600", "−", ""]


def _held(tmp_path, monkeypatch, prots, rows=ROWS):
    _, out, _ = _write(tmp_path, monkeypatch, rows=rows, prots=prots)
    r = out["ref_a"]
    assert [r[k] for k in gt.POSITION_COLS[:4]] == ["", "", "", ""]
    assert r["Position note"].startswith("POSITION_HOLD")
    return r["Position note"]


def test_a_length_disagreement_is_held(tmp_path, monkeypatch):
    prots = {k: dict(v) for k, v in PROTS.items()}
    prots["q000001"]["aa"] = "M" * 301
    note = _held(tmp_path, monkeypatch, prots)
    assert "301" in note and "300" in note


def test_a_contig_disagreement_is_held(tmp_path, monkeypatch):
    prots = {k: dict(v) for k, v in PROTS.items()}
    prots["q000001"]["contig"] = C2
    assert "contig" in _held(tmp_path, monkeypatch, prots)


def test_a_missing_or_repeated_tag_is_held(tmp_path, monkeypatch):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    gone = {k: v for k, v in PROTS.items() if v["tag"] != "gene_a"}
    assert "gene_a" in _held(tmp_path / "a", monkeypatch, gone)
    twice = {**PROTS, "q000009": dict(PROTS["q000001"], start=5000, end=5900)}
    assert "2 CDS" in _held(tmp_path / "b", monkeypatch, twice)


def test_without_the_genome_proteins_the_columns_are_blank(tmp_path, monkeypatch):
    head, rows, _ = _write(tmp_path, monkeypatch)
    assert head == gt.COLS + gt.POSITION_COLS
    assert all(r[k] == "" for r in rows.values() for k in gt.POSITION_COLS)


def test_display_cells_are_unchanged_by_positions(tmp_path, monkeypatch):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    _, with_pos, drawn = _write(tmp_path / "a", monkeypatch, prots=PROTS)
    _, without, _ = _write(tmp_path / "b", monkeypatch)
    assert {n: {k: r[k] for k in gt.COLS} for n, r in with_pos.items()} == \
        {n: {k: r[k] for k in gt.COLS} for n, r in without.items()}
    assert all(set(gt.POSITION_COLS) <= set(r) for r in drawn["table"])   # the rows carry positions ...
    assert all(len(gt._display_cells(r)) == len(gt.COLS) for r in drawn["table"])   # ... the drawing shows nine cells


def test_fresh_run_writes_positions(fresh_saved_split, monkeypatch):
    f = fresh_saved_split
    monkeypatch.setattr(f.gdr, "draw_locus_map", lambda *args, **kwargs: None)
    f.gdr.analyse_region("SYNTHETIC", f.prots, f.regions, f.core, f.reference, "Explicit reference", "saved fixture",
                         f.out, hits=f.hits, threads=3, sensitivity="sensitive", mibig_db=f.db, pfam=f.pfam,
                         figure=True, write_proteins=False, anchor="r_split", gene_table=True)
    with (f.out / "gene_table.tsv").open(newline="") as fh:
        row = next(csv.DictReader(fh, delimiter="\t"))
    assert row["CDS"] == "saved_piece_a + saved_piece_b"
    assert row["Contig"] == "NODE_1_length_900_cov_1 + NODE_2_length_900_cov_1"
    assert row["Start"] == "1 + 1" and row["End"] == "900 + 900"
    assert row["Strand"] == ""   # the fixture proteins carry no strand: blank, never guessed


def test_a_split_piece_on_another_contig_is_held(tmp_path, monkeypatch):
    """Audit F02: the split row checks each piece's saved contig, as the ordinary row does; no coordinates are lent from
    the contig the tag now sits on."""
    prots = {k: dict(v) for k, v in PROTS.items()}
    prots["q000001"]["contig"] = "NODE_3_length_9000_cov_2"
    _, rows, _ = _write(tmp_path, monkeypatch, prots=prots)
    split = rows["ref_d"]
    assert split["Contig"] == "" and split["Start"] == "" and split["End"] == ""
    assert "piece 1: POSITION_HOLD" in split["Position note"] and "contig" in split["Position note"]
