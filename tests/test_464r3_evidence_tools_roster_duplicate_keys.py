"""Swiss-Prot enrichment and coordinate backfill hold repeated join keys instead of last-row-wins."""
import importlib
import io
import json
import sys
import zipfile
from pathlib import Path

DT = Path(__file__).resolve().parents[1] / "deliverable_tools"


def _load(name, monkeypatch, root):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(root))
    monkeypatch.syspath_prepend(str(DT))
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def _roster(root, genes):
    rd = root / "sapote_deliverables" / "roster_v2"; rd.mkdir(parents=True)
    path = rd / "EXAMPLE_roster_v2.json"
    path.write_text(json.dumps({"bgcs": [{"bgc_id": "BGC001", "genes": genes}]}))
    return path


def test_duplicate_swissprot_rank1_rows_are_held(tmp_path, monkeypatch):
    m = _load("enrich_swissprot", monkeypatch, tmp_path)
    rp = _roster(tmp_path, [{"locus_tag": "g1", "channels": {}}])
    sp = tmp_path / "Local Blastp RESULTS (SwissProt)" / "EXAMPLE" / "BGC001"; sp.mkdir(parents=True)
    head = "bgc_id,gene,hit_rank,pct_identity,subject_def,subject_organism,subject_acc,query_coverage\n"
    (sp / "a_top10_local.csv").write_text(head + "BGC001,g1,1,90,first,o,P1,99\n")
    (sp / "b_top10_local.csv").write_text(head + "BGC001,g1,1,40,second,o,P2,50\n")
    msg = m.enrich("EXAMPLE")
    roster = json.loads(rp.read_text())
    assert "swissprot" not in roster["bgcs"][0]["genes"][0]["channels"]
    assert roster["join_holds"]["swissprot"][0]["hold"] == "DUPLICATE_SWISSPROT_RANK1_KEY"
    assert "held" in msg


def test_duplicate_antismash_locus_tag_is_held(tmp_path, monkeypatch):
    m = _load("backfill_coords_from_antismash", monkeypatch, tmp_path)
    rp = _roster(tmp_path, [{"locus_tag": "ctg1_1", "start": None, "channels": {}}])
    feats = [{"type": "CDS", "location": "[0:90](+)", "qualifiers": {"locus_tag": ["ctg1_1"], "translation": ["M" * 30]}},
             {"type": "CDS", "location": "[500:590](-)", "qualifiers": {"locus_tag": ["ctg1_1"], "translation": ["M" * 30]}}]
    zdir = tmp_path / "strain_data" / "EXAMPLE" / "antiSMASH"; zdir.mkdir(parents=True)
    with zipfile.ZipFile(zdir / "EXAMPLE.zip", "w") as z:
        z.writestr("EXAMPLE.json", json.dumps({"records": [{"features": feats}]}))
    msg = m.backfill("EXAMPLE")
    roster = json.loads(rp.read_text())
    assert roster["bgcs"][0]["genes"][0]["start"] is None
    assert roster["join_holds"]["antismash_coords"] == [{"locus_tag": "ctg1_1", "hold": "DUPLICATE_ANTISMASH_LOCUS_TAG"}]
    assert "held" in msg
