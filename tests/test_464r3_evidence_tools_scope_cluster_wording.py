"""scope_cluster states its positional rule and reconciles the exported slice with the midpoint count."""
import json
from tests.test_scope_cluster import _load, _merged_region


def _run(tmp_path, capsys, rec):
    module = _load()
    from Bio import SeqIO
    gbk = tmp_path / "input.gbk"; SeqIO.write(rec, gbk, "genbank")
    out = tmp_path / "out"
    assert module.main(["--gbk", str(gbk), "--category", "nucleoside", "--label", "s", "--outdir", str(out)]) == 0
    return json.loads((out / "s_nucleoside_scope.json").read_text()), capsys.readouterr()


def test_messages_do_not_assign_pathways(tmp_path, capsys):
    report, cap = _run(tmp_path, capsys, _merged_region())
    text = cap.out + cap.err
    assert "merged neighbours" not in text
    assert "genes were kept" not in text
    assert "not a pathway assignment" in text
    assert "not evidence that the gene belongs to another pathway" in report["excluded_basis"]
    assert report["export_inventory_state"] == "MATCHES_MIDPOINT_INVENTORY"
    assert report["exported_cds"] == ["nuc_A", "nuc_B"]


def test_boundary_crossing_cds_is_a_hold(tmp_path, capsys):
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    rec = _merged_region()
    f = SeqFeature(FeatureLocation(19500, 20300, strand=1), type="CDS")
    f.qualifiers.update(locus_tag=["edge_gene"], translation=["M" + "A" * 100])
    rec.features.append(f)  # midpoint 19900 is inside [0, 20000) but the CDS crosses the end
    report, cap = _run(tmp_path, capsys, rec)
    assert "edge_gene" in report["kept"]
    assert report["kept_not_exported"] == ["edge_gene"]
    assert report["export_inventory_state"] == "HOLD_EXPORT_DIFFERS_FROM_MIDPOINT_INVENTORY"
    assert "HOLD" in cap.out + cap.err


def test_help_does_not_call_the_span_true():
    module = _load()
    assert "TRUE protocluster" not in module.__doc__
    assert "true protocluster" not in (module.__doc__ or "").lower()
