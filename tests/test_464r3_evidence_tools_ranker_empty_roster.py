"""An archive member with no CDS is an unresolved reference roster, and the receipt says so."""
import io
import tarfile
from tests.test_definitive_bgc_ranker_v97434 import MOD, package


def _empty_archive(path):
    text = "LOCUS       BGC0000001 500 bp DNA linear\nFEATURES             Location/Qualifiers\nORIGIN\n        1 " + "a" * 60 + "\n//\n"
    with tarfile.open(path, "w:gz") as tf:
        data = text.encode(); info = tarfile.TarInfo("mibig_gbk_4.0/BGC0000001.gbk"); info.size = len(data)
        tf.addfile(info, io.BytesIO(data))


def test_zero_cds_roster_is_not_complete(tmp_path):
    p = package(tmp_path); archive = tmp_path / "mibig.tar.gz"; _empty_archive(archive)
    receipt = MOD.analyze([p], archive, tmp_path / "out")
    assert receipt["status"] == "COMPLETE_WITH_UNRESOLVED_REFERENCES"
    assert receipt["mibig_accessions_unresolved"] == ["BGC0000001"]
    assert receipt["mibig_rosters_resolved"] == 0
    assert receipt["mibig_archive_members_read"] == 1
