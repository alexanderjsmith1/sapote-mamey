"""phylo_autopilot plan: a header-only record is 'empty_record', not 'rrna'; a missing folder exits 2;
files without a recognised FASTA suffix are listed, not silently left out."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("ap_464r3", ROOT / "tools" / "phylo_autopilot.py")
AP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AP)


def test_header_only_record_is_held(tmp_path):
    f = tmp_path / "h.fasta"
    f.write_text(">q1\n")
    assert AP.classify_input(str(f)) == "empty_record"
    g = tmp_path / "mixed.fasta"
    g.write_text(">q1\n" + "ACGT" * 350 + "\n>q2\n")
    assert AP.classify_input(str(g)) == "empty_record"


def test_missing_folder_exits_2(tmp_path, capsys):
    assert AP.main(["plan", str(tmp_path / "nope")]) == 2
    assert "not a readable folder" in capsys.readouterr().err


def test_unrecognised_suffix_is_listed(tmp_path, capsys):
    (tmp_path / "a.fasta").write_text(">q\n" + "ACGT" * 350 + "\n")
    (tmp_path / "b.txt").write_text(">q\n" + "ACGT" * 350 + "\n")
    assert AP.main(["plan", str(tmp_path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["rrna"] == [str(tmp_path / "a.fasta")]
    assert out["not_classified_suffix"] == [str(tmp_path / "b.txt")]


def test_no_routed_query_points_to_the_routing_table(tmp_path, capsys, monkeypatch):
    q = tmp_path / "q.fasta"
    q.write_text(">q1\n" + "ACGT" * 350 + "\n")
    db = tmp_path / "db" / "16S"
    db.parent.mkdir()
    monkeypatch.setattr(AP._p16, "refseq_16s_blastdb", lambda value: value)
    monkeypatch.setattr(AP, "assign_genus", lambda *a, **k: {})
    rc = AP.main(["run-16s", "--query", str(q), "--db", str(db), "--group", "nocardia",
                  "--outdir", str(tmp_path / "out"), "--dry-run"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "no queries routed to group 'nocardia'" in err and "routing_table.tsv" in err
