"""fetch_mibig_reference: MIBiG public-repo reference fetcher. Hermetic — no network.

Tests the accession canonicalisation and the extraction against a SYNTHETIC tarball built in
a tempdir (same member layout as MIBiG: mibig_gbk_<ver>/<ACC>.gbk). The live download +
region001-vs-BGC0000116 comparison is verified on real data in the session.
"""
import io
import tarfile
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("fetch_mibig_reference", ROOT / "tools" / "fetch_mibig_reference.py")
fm = importlib.util.module_from_spec(_s)
_s.loader.exec_module(fm)


def test_canonical_acc_strips_kcb_rank_suffix():
    # KCB_top hands 'BGC0000116.5 | nystatin-like ...'; the MIBiG file is BGC0000116.gbk
    assert fm.canonical_acc("BGC0000116.5 | nystatin-like Pseudonocardia polyene A1") == "BGC0000116"
    assert fm.canonical_acc("BGC0000877") == "BGC0000877"
    assert fm.canonical_acc("BGC0000877:polyoxin") == "BGC0000877"
    assert fm.canonical_acc("no accession here") is None
    assert fm.canonical_acc("") is None


def _synthetic_tarball(path, version, entries):
    """entries: {acc: gbk_bytes} → tar.gz with members mibig_gbk_<version>/<acc>.gbk."""
    with tarfile.open(path, "w:gz") as tf:
        for acc, data in entries.items():
            info = tarfile.TarInfo(f"mibig_gbk_{version}/{acc}.gbk")
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


def test_extract_from_tarball_writes_label_gbk():
    with tempfile.TemporaryDirectory() as tmp:
        tar = Path(tmp) / "mibig_gbk_9.9.tar.gz"
        _synthetic_tarball(tar, "9.9", {
            "BGC0000116": b"LOCUS BGC0000116\n//\n",
            "BGC0000877": b"LOCUS BGC0000877\n//\n",
        })
        outdir = Path(tmp) / "out"
        written, missing = fm._extract_from_tarball(
            str(tar), ["BGC0000116.5:nystatin", "BGC0000877:polyoxin"], version="9.9", outdir=str(outdir))
        assert missing == []
        names = {lab for _, lab, _ in written}
        assert names == {"nystatin", "polyoxin"}
        assert (outdir / "nystatin.gbk").read_bytes().startswith(b"LOCUS BGC0000116")


def test_extract_reports_missing_accession():
    with tempfile.TemporaryDirectory() as tmp:
        tar = Path(tmp) / "mibig_gbk_9.9.tar.gz"
        _synthetic_tarball(tar, "9.9", {"BGC0000116": b"LOCUS x\n//\n"})
        written, missing = fm._extract_from_tarball(
            str(tar), ["BGC9999999:nope"], version="9.9", outdir=str(Path(tmp) / "o"))
        assert written == []
        assert "BGC9999999" in missing


def test_extract_flags_unparseable_spec():
    with tempfile.TemporaryDirectory() as tmp:
        tar = Path(tmp) / "mibig_gbk_9.9.tar.gz"
        _synthetic_tarball(tar, "9.9", {"BGC0000116": b"LOCUS x\n//\n"})
        written, missing = fm._extract_from_tarball(
            str(tar), ["not-an-accession:label"], version="9.9", outdir=str(Path(tmp) / "o"))
        assert written == []
        assert "not-an-accession:label" in missing
