"""Actual single-run source binding and package/master transaction on fabricated input."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import zipfile

import pytest
from mamey import cli, captured_run
from mamey.archive_snapshot import ArchiveSnapshot, ArchiveSnapshotPolicy
from mamey.intake_session import CapturedIntakeSession, CapturedIntakeHold, EvidenceOptions, encode


def fixture_archive(path, *, malformed_json=False):
    # Literal12-base GBK supports both Bio and the fallback reader.
    cid = "SYNTHETIC_NODE_A.1"
    gbk = (f"LOCUS       {cid}         12 bp    DNA     linear   BCT 01-JAN-2000\n"
           f"ACCESSION   {cid}\nVERSION     {cid}\n"
           "  ORGANISM  Streptomyces syntheticus strain SYNTHETICCASE\n"
           "            Bacteria; Actinomycetota.\n"
           "COMMENT     ##antiSMASH-Data-START##\n            Version :: 8.0.0\n            ##antiSMASH-Data-END##\n"
           'FEATURES             Location/Qualifiers\n     region          1..12\n                     /product="NRPS"\n'
           '     CDS             1..12\n                     /locus_tag="SYNTHETIC_GENE"\n                     /translation="MRTK"\n'
           "ORIGIN\n        1 acgtacgtacgt\n//\n")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("full.gbk", gbk); z.writestr("record.region001.gbk", gbk)
        z.writestr(f"knownclusterblast/{cid}_c1.txt", "\n>>\nSource: BGC0000001.1 synthetic\nCumulative BLAST score: 42\nNumber of proteins with BLAST hits to this cluster: 2\n")
        z.writestr("records.json", "{" if malformed_json else json.dumps({"records": [{"id": cid, "modules": {}}]}))
    return path


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    official = tmp_path / "synthetic_governance"; official.mkdir()
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": [], "scope": "fabricated test only"}))
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(official))
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(tmp_path / "empty_data"))
    source = fixture_archive(tmp_path / "input.zip")
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(dict(max_archive_bytes=64000, max_members=30,
                                     max_total_uncompressed_bytes=100000, max_publish_bytes=64000000)))
    return source, policy


def run_args(inputs, tmp_path, *extra):
    source, policy = inputs
    return ["run", "--strain", "SYNTHETIC-CAPTURED-RUN", "--input-zip", str(source),
            "--outdir", str(tmp_path / "out"), "--master", str(tmp_path / "master.xlsx"),
            "--brief", "none", "--locus-maps", "off", "--reference-completion", "off",
            "--json-evidence", "off", "--capture-policy", str(policy), *extra]


def trap_after_capture(monkeypatch, source):
    import builtins, io, os
    original_capture = ArchiveSnapshot.capture
    originals = (Path.open, builtins.open, io.open, os.open)
    def is_source(p):
        return isinstance(p, (str, bytes, Path)) and Path(os.fsdecode(p)).resolve() == source.resolve()
    def capture(cls, locator, **kwargs):
        snapshot = original_capture(locator, **kwargs)
        source.write_bytes(b"changed original after capture")
        def path_open(p, mode="r", *a, **k):
            if is_source(p) and ("r" in mode or "+" in mode): pytest.fail("original Path reopened")
            return originals[0](p, mode, *a, **k)
        def builtin_open(p, mode="r", *a, **k):
            if is_source(p) and ("r" in mode or "+" in mode): pytest.fail("original builtin reopened")
            return originals[1](p, mode, *a, **k)
        def io_open(p, mode="r", *a, **k):
            if is_source(p) and ("r" in mode or "+" in mode): pytest.fail("original io reopened")
            return originals[2](p, mode, *a, **k)
        def os_open(p, flags, *a, **k):
            if is_source(p) and flags & os.O_ACCMODE != os.O_WRONLY: pytest.fail("original os reopened")
            return originals[3](p, flags, *a, **k)
        monkeypatch.setattr(Path, "open", path_open); monkeypatch.setattr(builtins, "open", builtin_open)
        monkeypatch.setattr(io, "open", io_open); monkeypatch.setattr(os, "open", os_open)
        return snapshot
    monkeypatch.setattr(ArchiveSnapshot, "capture", classmethod(capture))


def test_actual_run_traps_original_reopens_and_publishes_package_master(inputs, tmp_path, monkeypatch, capsys):
    source, _ = inputs; digest = hashlib.sha256(source.read_bytes()).hexdigest()
    trap_after_capture(monkeypatch, source)
    assert cli.main(run_args(inputs, tmp_path, "--capture-expected-sha256", digest)) == 0
    package = tmp_path / "out/SYNTHETIC-CAPTURED-RUN/package"
    manifest = json.loads((package / "manifest.json").read_text())
    assert manifest["input_zip_sha256"] == manifest["captured_source"]["input_sha256"] == digest
    assert manifest["captured_source"]["original_version"] == "EXPECTED_DIGEST_MATCHED"
    assert manifest["captured_source"]["biological_absence"] == "NOT_ESTABLISHED"
    archives = list((tmp_path / "out").rglob("*Complete_Package.zip")); assert len(archives) == 1
    with zipfile.ZipFile(archives[0]) as z:
        member = next(n for n in z.namelist() if n.endswith("manifest.json"))
        assert json.loads(z.read(member))["captured_source"]["input_sha256"] == digest
    assert (tmp_path / "master.xlsx").is_file() and list(package.glob("*.xlsx"))
    assert "checksum: " + hashlib.sha256((tmp_path / "master.xlsx").read_bytes()).hexdigest()[:16] in capsys.readouterr().out
    assert not [p for p in package.rglob("*") if p.suffix.lower() in {".png", ".svg", ".pdf"}]
    for p in package.rglob("*.json"):
        assert ".mamey-captured-run-" not in p.read_text()
    handback = json.loads((tmp_path / "out/HANDBACK.json").read_text())
    assert Path(handback["primary_deliverables"][0]["zip"]).is_file()
    from mamey.validate import verify_checksums
    assert not verify_checksums(package)


def test_actual_run_late_failure_keeps_existing_master_and_no_package(inputs, tmp_path, monkeypatch):
    from openpyxl import Workbook
    master = tmp_path / "master.xlsx"; book = Workbook(); book.save(master); book.close()
    before = master.read_bytes()
    reached = []
    def refuse(*a, **k):
        reached.append(True)
        raise RuntimeError("fabricated late publication refusal")
    monkeypatch.setattr(captured_run, "publish_result", refuse)
    assert cli.main(run_args(inputs, tmp_path)) == 2
    assert reached == [True]
    assert master.read_bytes() == before and not (tmp_path / "out").exists()


def test_actual_run_wrong_expected_version_has_no_publication(inputs, tmp_path):
    assert cli.main(run_args(inputs, tmp_path, "--capture-expected-sha256", "0" * 64)) == 2
    assert not (tmp_path / "out").exists() and not (tmp_path / "master.xlsx").exists()


def test_actual_run_unavailable_consumer_holds_before_capture(inputs, tmp_path, monkeypatch):
    def forbidden(*a, **k): pytest.fail("unsupported profile captured source")
    monkeypatch.setattr(ArchiveSnapshot, "capture", forbidden)
    assert cli.main(run_args(inputs, tmp_path, "--reference-completion", "auto")) == 2
    assert not (tmp_path / "out").exists()


def test_self_consistent_reconstructed_evidence_is_not_a_minted_parse_origin(inputs):
    source, _ = inputs; session = CapturedIntakeSession.capture(source, policy=ArchiveSnapshotPolicy(64000, 30, 100000))
    options = EvidenceOptions(budget_seconds=0); bound = session.parse_evidence(options)
    data = json.loads(bound._payload); data["evidence"]["unparsed_marker"] = "not emitted by parser"
    payload = encode(data); reconstructed = replace(bound, _payload=payload, payload_sha256=hashlib.sha256(payload).hexdigest())
    with pytest.raises(CapturedIntakeHold, match="BINDING_REFUSED"):
        session.prepare("SYNTHETIC", options=options, bound_evidence=reconstructed)


def test_reused_capture_retains_expected_version(inputs):
    source, _ = inputs; policy = ArchiveSnapshotPolicy(64000, 30, 100000)
    snapshot = ArchiveSnapshot.capture(source, policy=policy, expected_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    source.unlink()
    data = CapturedIntakeSession(snapshot, policy=policy).prepare("SYNTHETIC", options=EvidenceOptions(budget_seconds=0))
    assert data["original_version"] == "EXPECTED_DIGEST_MATCHED"
    assert data["transaction"]["input_sha256"] == snapshot.input_sha256



def test_actual_run_retains_partial_json_errors_missingness_and_denominator(inputs, tmp_path):
    source, _ = inputs
    fixture_archive(source, malformed_json=True)
    assert cli.main(run_args(inputs, tmp_path, "--json-evidence", "full")) == 0
    package = tmp_path / "out/SYNTHETIC-CAPTURED-RUN/package"
    manifest = json.loads((package / "manifest.json").read_text())
    evidence = json.loads(next(package.glob("*_AntiSMASH_Evidence_Parse.json")).read_text())
    assert evidence["json_errors"] and evidence["source_completeness"]["json_state"] == "INCOMPLETE"
    assert manifest["captured_source"]["source_completeness"]["json_state"] == "INCOMPLETE"
    denominator = manifest["captured_source"]["denominator"]
    assert denominator["value"] == 1 and denominator["expected_biological_total"] is None
    assert denominator["whole_assembly_completeness"] == "UNKNOWN"
    assert manifest["captured_source"]["biological_absence"] == "NOT_ESTABLISHED"
    assert manifest["bgcs"][0]["riq_score"] is None and manifest["bgcs"][0]["kcb_cumulative"] == 42
