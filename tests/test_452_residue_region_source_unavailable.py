"""A pair whose region GenBank file is missing from the ZIP, or holds no protein, is held, not called THIN.

Before, region_proteins skipped a wanted region it could not resolve, and the pair was then classified from the
other side alone: zero residues placed read as THIN_RESIDUES under an overall state of RAN.
"""
import zipfile
from types import SimpleNamespace

from mamey import residue_tiling as rt

AA = "M" + "ACDEFGHIKLMNPQRSTVWY" * 25   # 501 aa


def _gbk(name, translation=True):
    lines = [f"LOCUS       {name:<16}{3000:>12} bp    DNA     linear   UNK 01-JAN-1980",
             "FEATURES             Location/Qualifiers", "     CDS             1..1503",
             f'                     /locus_tag="{name}_1"']
    if translation:
        lines.append(f'                     /translation="{AA}"')
    return "\n".join(lines + ["ORIGIN", "//"]) + "\n"


def _setup(tmp_path, monkeypatch):
    z = tmp_path / "genome.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("ctgA.region001.gbk", _gbk("ctgA"))
        zf.writestr("ctgC.region001.gbk", _gbk("ctgC"))
        zf.writestr("ctgD.region001.gbk", _gbk("ctgD", translation=False))
    bgcs = [SimpleNamespace(bgc_id=f"R{c}", contig=f"ctg{c}", region_number=1, source_gbk=f"ctg{c}.region001.gbk")
            for c in "ACD"] + [SimpleNamespace(bgc_id="RB", contig="ctgB", region_number=1, source_gbk="")]
    db = tmp_path / "mibig.dmnd"
    db.write_text("x")
    searched = []

    def fake_diamond(_binary, _db, query, _out, _threads):
        names = [line[1:] for line in query.read_text().splitlines() if line.startswith(">")]
        searched.extend(n.split("|", 1)[0] for n in names)
        span = {"RA": (1, 400), "RC": (401, 800)}
        return [(n, "BGC0000001|1", 60.0, 1, 400, *span[n.split("|", 1)[0]], 500.0)
                for n in names if n.split("|", 1)[0] in span]

    monkeypatch.setattr(rt, "find_diamond", lambda explicit=None: "/bin/true")
    monkeypatch.setattr(rt, "_run_diamond", fake_diamond)
    refs = {"reference_records": [{"db_kind": "knownclusterblast", "bgc_id": b.bgc_id, "ref": "BGC0000001"}
                                  for b in bgcs]}
    return z, bgcs, db, refs, searched


def _pair(a, b):
    return {"bgc_a": a, "bgc_b": b, "acceptance_gate": "ST-PARALOG_no_complementarity_proof"}


def test_missing_or_empty_region_source_is_held(tmp_path, monkeypatch):
    z, bgcs, db, refs, searched = _setup(tmp_path, monkeypatch)
    result = {"ranked_pairs": [_pair("RA", "RB"), _pair("RA", "RD"), _pair("RA", "RC")]}
    rt.add_residue_tiling(result, z, bgcs, refs, db)
    missing, empty, resolved = result["ranked_pairs"]
    assert missing["residue_tiling"] == "REGION_SOURCE_UNAVAILABLE"
    assert empty["residue_tiling"] == "REGION_SOURCE_UNAVAILABLE"
    assert missing["residue_references_tested"] == "" and missing["residues_b"] == ""
    status = result["residue_tiling_status"]
    assert status["state"] == "RAN" and status["pairs_tested"] == 1
    assert status["regions_requested"] == 4
    assert status["regions_source_unavailable"] == ["RB", "RD"] and status["pairs_source_unavailable"] == 2
    assert sorted(set(searched)) == ["RA", "RC"]


def test_a_resolved_pair_is_classified_as_before(tmp_path, monkeypatch):
    z, bgcs, db, refs, _searched = _setup(tmp_path, monkeypatch)
    result = {"ranked_pairs": [_pair("RA", "RC")]}
    rt.add_residue_tiling(result, z, bgcs, refs, db)
    pair = result["ranked_pairs"][0]
    assert pair["residue_tiling"] == "COMPLEMENTARY_RESIDUES"
    assert pair["residues_a"] == pair["residues_b"] == 400 and pair["residue_overlap"] == 0.0
    assert result["residue_tiling_status"]["pairs_tested"] == 1
