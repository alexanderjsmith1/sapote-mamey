"""End-to-end package-write smoke tests.

Before this file, no test exercised the full run_one_strain -> _write_package path: extractors,
scans, and parsers were each tested in isolation, but nothing ran a strain all the way to a sealed
package. That gap is exactly why two defects shipped/regressed undetected:

  * the v9.7.22 streaming "Object of type Decimal is not JSON serializable" crash in _write_package
    (ijson yields JSON numbers as Decimal; un-floated record evidence then fails json.dumps), and
  * the F1 bare-assembly guard mis-fire that failed a region-bearing strain when the antiSMASH
    version string was merely undetected (raw > 0 but antismash_ver is None).

These tests run the real entrypoint on the synthetic fixture and assert a package is written —
including under forced streaming, which is the regression guard for the Decimal crash.
"""
import json
import copy
import os
import pathlib
import zipfile

import pytest

from mamey.cli import run_one_strain
import mamey.antismash_evidence as ae
from tools.fixture_inputs import SYNTHETIC_FULL_CONTIG_ID

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SYNTH = FIXTURES / "synthetic_single_contig_antismash.zip"


def _run(input_zip, outdir, json_mode="bounded"):
    return run_one_strain(
        strain_id="SMOKE", display_name="SMOKE",
        input_zip=str(input_zip), outdir=str(outdir), mode="full",
        taxonomy="", source="", bioactivity="",
        master_path=None, json_mode=json_mode,
    )




@pytest.fixture(scope="module")
def synth_run(tmp_path_factory, synthetic_single_contig_full_locus_zip):
    """Run the synthetic package-write fixture once; this is an integration smoke and is slow."""
    out = tmp_path_factory.mktemp("package_write_synth")
    res = _run(synthetic_single_contig_full_locus_zip, out)
    return res, out

def test_package_write_smoke_gbk_only(synth_run):
    """run_one_strain on a region-bearing antiSMASH fixture must write a package.

    The synthetic fixture parses 3 BGCs but has no detectable antiSMASH version string. Before the
    F1 fix this returned MAMEY_FAILED (mis-classified as a bare assembly); it must now PASS, prove a
    package on disk, and record the missing version as an issue rather than discarding the strain.
    """
    res, outdir = synth_run
    assert res["status"] in {"PASS", "MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES"} or str(res.get("validator_status","")).startswith("PASS"), res
    pkg = res.get("package_zip")
    assert pkg and os.path.exists(pkg), f"no package written: {res}"
    assert res.get("raw_bgcs", 0) >= 1, res
    # F1: missing version with regions present is a recorded issue, not a fatal bare-assembly fail.
    assert any("version string not detected" in i for i in res.get("issues", [])), res


def _fixture_with_numeric_records(src_zip: pathlib.Path, dst_zip: pathlib.Path) -> None:
    """Copy the GBK/TXT synthetic fixture and add a records JSON whose product-class prediction
    carries raw JSON numbers (score/weight/count).

    The product-class extractor embeds the whole prediction dict into package evidence. Under
    streaming, ijson yields those numbers as Decimal by default; if any reach _write_package
    un-floated, json.dumps raises 'Object of type Decimal is not JSON serializable'. With the
    use_float fix they serialize as float and the package writes.
    """
    records = {
        "records": [
            {
                "id": SYNTHETIC_FULL_CONTIG_ID,
                "modules": {
                    "antismash.modules.t2pks": {
                        "protocluster_predictions": {
                            "1": {
                                "product_classes": ["polyketide"],
                                "score": 3780.0,
                                "weight": 0.95,
                                "count": 8,
                            }
                        }
                    }
                },
            }
        ]
    }
    with zipfile.ZipFile(src_zip) as zin, \
            zipfile.ZipFile(dst_zip, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            admitted = copy.copy(item)
            if admitted.filename.lower().endswith((".fa", ".fna", ".fasta", ".fas")):
                admitted.compress_type = zipfile.ZIP_STORED
            zout.writestr(admitted, zin.read(item.filename))
        zout.writestr(f"syn/{SYNTHETIC_FULL_CONTIG_ID}.records.json", json.dumps(records))


@pytest.mark.skipif(not ae._HAVE_IJSON, reason="streaming path requires ijson")
def test_package_write_smoke_streaming_no_decimal_crash(
    tmp_path, monkeypatch, synthetic_single_contig_full_locus_zip
):
    """Forcing streaming over a numeric records JSON must still write a package.

    This is the direct regression guard for the v9.7.22 Decimal-serialize crash: with the bug
    (ijson Decimals reaching _write_package), this run raises in json.dumps and no package is
    written. _STREAM_JSON_MODE is read at import, so patch the module global to force streaming
    regardless of the (tiny) fixture size.
    """
    fx = tmp_path / "syn_numeric.zip"
    _fixture_with_numeric_records(synthetic_single_contig_full_locus_zip, fx)
    monkeypatch.setattr(ae, "_STREAM_JSON_MODE", "always")
    res = _run(fx, tmp_path, json_mode="bounded")
    assert res["status"] in {"PASS", "MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES"} or str(res.get("validator_status","")).startswith("PASS"), res
    pkg = res.get("package_zip")
    assert pkg and os.path.exists(pkg), f"no package written under forced streaming: {res}"

def test_triage_board_class_conf_label_not_arch_conf(synth_run):
    """W9: the triage board's class-call confidence column must be labelled Class_Conf, not Arch_Conf.

    Abbreviating architecture_class_confidence -> 'Arch_Conf' dropped 'class' and read as confidence in
    the A-E architecture GRADE, producing the apparent 'Arch=A, Arch_Conf=LOW' contradiction. The column
    is the confidence in the class-capacity CALL, so it is now Class_Conf and must sit alongside the
    distinct Arch (grade) and Arch_Capacity (class call) columns.
    """
    res, outdir = synth_run
    assert res["status"] in {"PASS", "MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES"} or str(res.get("validator_status","")).startswith("PASS"), res
    boards = list(pathlib.Path(outdir).rglob("*_4_triage_board.csv"))
    assert boards, "no triage board written"
    header = boards[0].read_text().splitlines()[0].split(",")
    assert "Class_Conf" in header, header
    assert "Arch_Conf" not in header, header
    # the two distinct sibling axes must still be present and separate
    assert "Arch" in header and "Arch_Capacity" in header, header


# The synthetic source is deliberately outside the generated package tree.
def _source_locator_manifest(synth_run):
    _result, outdir = synth_run
    return outdir / "SMOKE" / "package" / "manifest.json"


def test_stored_source_zip_records_original_path_and_digest(
    synth_run, synthetic_single_contig_full_locus_zip
):
    import hashlib
    source = synthetic_single_contig_full_locus_zip.resolve()
    payload = json.loads(_source_locator_manifest(synth_run).read_text())
    assert payload["input_zip"] == str(source)
    assert payload["input_zip_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_stored_source_zip_default_reader_finds_original(
    synth_run, synthetic_single_contig_full_locus_zip
):
    from mamey.postseal_output import resolve_source_archive
    archive, receipt = resolve_source_archive(_source_locator_manifest(synth_run).parent)
    assert archive == synthetic_single_contig_full_locus_zip.resolve()
    assert receipt["state"] == "ARCHIVE_HASH_VERIFIED"


def test_stored_source_zip_figure_reader_finds_original(
    synth_run, synthetic_single_contig_full_locus_zip
):
    from mamey.render_all_figures import _resolve_source_zip
    assert _resolve_source_zip(_source_locator_manifest(synth_run).parent) == str(synthetic_single_contig_full_locus_zip.resolve())


def test_stored_source_zip_bigscape_stages_original_regions(synth_run, tmp_path):
    from deliverable_tools.bigscape_run import _stage_bound_package
    destination = tmp_path / "staged"
    destination.mkdir()
    assert _stage_bound_package(str(_source_locator_manifest(synth_run).parent), str(destination)) > 0
    assert list(destination.glob("*.gbk"))


def test_stored_source_zip_explicit_override_still_wins(
    synth_run, synthetic_single_contig_full_locus_zip, tmp_path
):
    from mamey.postseal_output import resolve_source_archive
    from mamey.render_all_figures import _resolve_source_zip
    override = tmp_path / "moved.zip"
    override.write_bytes(synthetic_single_contig_full_locus_zip.read_bytes())
    package = _source_locator_manifest(synth_run).parent
    archive, _receipt = resolve_source_archive(package, override)
    assert archive == override.resolve()
    assert _resolve_source_zip(package, override) == str(override.resolve())


def test_stored_source_zip_explicit_digest_mismatch_is_refused(synth_run, tmp_path):
    from mamey.postseal_output import resolve_source_archive
    from mamey.render_all_figures import _resolve_source_zip
    wrong = tmp_path / "wrong.zip"
    wrong.write_bytes(b"software fixture with a different digest")
    package = _source_locator_manifest(synth_run).parent
    with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
        resolve_source_archive(package, wrong)
    with pytest.raises(ValueError, match="DIGEST_MISMATCH"):
        _resolve_source_zip(package, wrong)


def test_stored_source_zip_bigscape_archive_finds_original(synth_run, tmp_path):
    from deliverable_tools.bigscape_run import _stage_bound_package
    result, _outdir = synth_run
    destination = tmp_path / "from_package_zip"
    assert _stage_bound_package(result["package_zip"], str(destination)) > 0
    assert list(destination.glob("*.gbk"))
