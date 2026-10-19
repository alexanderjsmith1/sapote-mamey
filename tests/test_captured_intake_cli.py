"""Twelve-base fabricated inputs exercise the actual opt-in captured CLI slice."""
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import warnings
import zipfile

import pytest
from mamey import cli, parsers, antismash_evidence as ev, captured_intake_cli as command
from mamey.archive_snapshot import ArchiveSnapshot, ArchiveSnapshotPolicy
from mamey.intake_session import CapturedIntakeSession, CapturedIntakeHold, EvidenceOptions

POLICY = ArchiveSnapshotPolicy(64000, 30, 100000)
CID = "SYNTHETIC_NODE_A.1"
TXT = ("ClusterBlast scores for synthetic source\n\n>>\nSource: BGC0000001.1 fabricated\n"
       "Cumulative BLAST score: 42\nNumber of proteins with BLAST hits to this cluster: 2\n")


def archive(path, *, extra=(), malformed_json=False):
    pytest.importorskip("Bio", reason="Biopython builds this fabricated GenBank archive")
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, SimpleLocation
    r = SeqRecord(Seq("ACGTACGTACGT"), id=CID, name=CID, description="fabricated intake")
    r.annotations.update(molecule_type="DNA", organism="Streptomyces syntheticus strain SYNTHETICCASE",
                         taxonomy=["Bacteria", "Actinomycetota"],
                         structured_comment={"antiSMASH-Data": {"Version": "8.0.0"}})
    r.features = [SeqFeature(SimpleLocation(0, 12), type="region", qualifiers={"product": ["NRPS"]}),
                  SeqFeature(SimpleLocation(0, 12), type="CDS", qualifiers={"locus_tag": ["SYNTHETIC_GENE"], "translation": ["MRTK"]})]
    s = io.StringIO(); SeqIO.write(r, s, "genbank")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("full.gbk", s.getvalue()); z.writestr("record.region001.gbk", s.getvalue())
        z.writestr(f"knownclusterblast/{CID}_c1.txt", TXT)
        z.writestr("records.json", "{" if malformed_json else json.dumps({"records": [{"id": CID, "modules": {}}]}))
        for name, value in extra:
            z.writestr(name, value)
    return path


def args(path, out, *extra):
    return ["intake-captured", "--input-zip", str(path), "--outdir", str(out),
            "--max-archive-bytes", "64000", "--max-members", "30",
            "--max-total-uncompressed-bytes", "100000", *extra]


def load(out):
    return json.loads((out / "intake.json").read_text()), json.loads((out / "manifest.json").read_text())


def test_actual_cli_never_reopens_original_after_capture(tmp_path, monkeypatch):
    path = archive(tmp_path / "input.zip"); digest = hashlib.sha256(path.read_bytes()).hexdigest()
    original_capture = ArchiveSnapshot.capture
    original_open = Path.open
    trapped = []

    def capture_then_trap(cls, source, **kwargs):
        captured = original_capture(source, **kwargs)
        path.write_bytes(b"fabricated changed original after capture")

        def guarded_open(p, mode="r", *a, **k):
            if p.resolve() == path.resolve() and ("r" in mode or "+" in mode):
                trapped.append(str(p)); pytest.fail("original source reopened after capture")
            return original_open(p, mode, *a, **k)

        monkeypatch.setattr(Path, "open", guarded_open)
        # Builtin open could otherwise bypass Path.open.
        import builtins
        original_builtin = builtins.open
        def guarded_builtin(p, mode="r", *a, **k):
            if isinstance(p, (str, Path)) and Path(p).resolve() == path.resolve() and ("r" in mode or "+" in mode):
                trapped.append(str(p)); pytest.fail("original source reopened via builtin open")
            return original_builtin(p, mode, *a, **k)
        monkeypatch.setattr(builtins, "open", guarded_builtin)
        import os
        original_io, original_os = io.open, os.open
        def guarded_io(p, mode="r", *a, **k):
            if isinstance(p, (str, Path)) and Path(p).resolve() == path.resolve() and ("r" in mode or "+" in mode):
                trapped.append(str(p)); pytest.fail("original source reopened via io.open")
            return original_io(p, mode, *a, **k)
        def guarded_os(p, flags, *a, **k):
            if isinstance(p, (str, Path)) and Path(p).resolve() == path.resolve() and flags & os.O_ACCMODE != os.O_WRONLY:
                trapped.append(str(p)); pytest.fail("original source reopened via os.open")
            return original_os(p, flags, *a, **k)
        monkeypatch.setattr(io, "open", guarded_io)
        monkeypatch.setattr(os, "open", guarded_os)
        return captured

    monkeypatch.setattr(ArchiveSnapshot, "capture", classmethod(capture_then_trap))
    out = tmp_path / "out"
    assert cli.main(args(path, out, "--expected-sha256", digest, "--json-evidence", "full")) == 0
    data, manifest = load(out)
    assert not trapped and data["input_sha256"] == manifest["input_sha256"] == digest
    assert data["strain_resolution"]["source"] == "archive"
    assert data["original_version"] == "EXPECTED_DIGEST_MATCHED"
    assert data["capture_receipt"]["verified_uncompressed_bytes"] == data["capture_receipt"]["declared_uncompressed_bytes"]
    assert data["assembly"]["genome_bp"] == 12 and len(data["bgcs"]) == len(data["cds"]) == 1
    assert data["sequence_roster"][0]["length"] == 12
    assert hashlib.sha256((out / "intake.json").read_bytes()).hexdigest() == manifest["outputs"][0]["sha256"]
    assert manifest["full_package_published"] is manifest["workbook_updated"] is False


def test_expected_version_mismatch_has_no_publication(tmp_path, capsys):
    path = archive(tmp_path / "input.zip"); out = tmp_path / "out"
    assert cli.main(args(path, out, "--expected-sha256", "0" * 64)) == 2
    assert "HASH_MISMATCH" in capsys.readouterr().err and not out.exists()


def test_fallback_preserves_status_pass_count_and_source(tmp_path, monkeypatch):
    path = archive(tmp_path / "input.zip"); out = tmp_path / "out"; passes = []
    run = ev._run_record_extractors
    def counted(source, handlers):
        passes.append((source.input_sha256, len(handlers))); return run(source, handlers)
    monkeypatch.setattr(ev, "_run_record_extractors", counted)
    def timeout(*a, **k): raise cli._BoundedTimeout()
    monkeypatch.setattr(cli, "_with_timeout", timeout)
    assert cli.main(args(path, out, "--json-evidence", "bounded")) == 0
    data, _ = load(out); evidence = data["evidence"]
    assert passes == [(data["input_sha256"], 2)]
    assert evidence["json_mode_requested"] == "bounded" and evidence["json_mode"] == "off"
    assert evidence["json_parse_budget"]["state"] == "EXCEEDED_FALLBACK_OFF"
    assert data["bgcs"][0]["kcb_cumulative"] == 42 and "kcb_assignment_audit" in evidence


@pytest.mark.parametrize("mode, tigrfam, structured, count", [("off", True, False, 2),
    ("off", False, False, 0), ("off", False, True, 5), ("bounded", True, False, 7)])
def test_bound_evidence_reuse_preserves_options_and_one_record_pass(tmp_path, monkeypatch, mode, tigrfam, structured, count):
    path = archive(tmp_path / "input.zip"); session = CapturedIntakeSession.capture(path, policy=POLICY)
    passes = []; original = ev._run_record_extractors
    def counted(source, handlers): passes.append(len(handlers)); return original(source, handlers)
    monkeypatch.setattr(ev, "_run_record_extractors", counted)
    options = EvidenceOptions(mode, tigrfam, structured, 0)
    bound = session.parse_evidence(options); data = session.prepare("SYNTHETIC-CASE", options=options, bound_evidence=bound)
    assert passes == ([count] if count else [])
    assert data["evidence_parse_origin_sha256"] == bound.payload_sha256
    assert "kcb_assignment_audit" in data["evidence"]
    assert "kcb_assignment_audit" not in session.working_evidence(bound)


@pytest.mark.parametrize("stage", ["evidence_apply", "features", "manifest", "manifest_interrupt"])
def test_late_failures_never_publish_intake_manifest(tmp_path, monkeypatch, stage):
    path = archive(tmp_path / "input.zip"); out = tmp_path / "out"
    def fail(*a, **k):
        if stage == "manifest_interrupt": raise KeyboardInterrupt("fabricated interrupt")
        raise RuntimeError("fabricated late failure")
    if stage == "evidence_apply": monkeypatch.setattr(parsers, "apply_evidence_to_bgcs", fail)
    elif stage == "features": monkeypatch.setattr(parsers, "extract_domain_features", fail)
    else: monkeypatch.setattr(command, "manifest_payload", fail)
    if stage == "manifest_interrupt":
        with pytest.raises(KeyboardInterrupt): cli.main(args(path, out))
    else: assert cli.main(args(path, out)) == 2
    assert not out.exists()
    assert not list(tmp_path.glob("*.xlsx")) and not list(tmp_path.glob("*.mamey-output-*"))


@pytest.mark.parametrize("name", ["records.json", f"knownclusterblast/{CID}_c1.txt", "full.gbk"])
@pytest.mark.parametrize("partial", [False, True])
def test_duplicate_namespace_is_held_even_with_explicit_partial_policy(tmp_path, name, partial):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); path = archive(tmp_path / "input.zip", extra=[(name, "contradictory last entry")])
    out = tmp_path / "out"
    assert cli.main(args(path, out, *(["--allow-incomplete-genbank"] if partial else []))) == 2
    assert not out.exists()


@pytest.mark.parametrize("partial", [False, True])
def test_partial_inputs_preserve_missingness_denominator_and_errors(tmp_path, partial):
    path = archive(tmp_path / "input.zip", extra=[("broken.gbk", "unparseable")], malformed_json=True)
    out = tmp_path / "out"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        code = cli.main(args(path, out, "--json-evidence", "full", *(["--allow-incomplete-genbank"] if partial else [])))
    if not partial:
        assert code == 2 and not out.exists(); return
    assert code == 0
    data, manifest = load(out)
    assert data["genbank_complete"] is False and manifest["denominator"]["source_complete"] is False
    assert data["denominator"]["value"] == 1 and data["denominator"]["expected_biological_total"] is None
    assert data["evidence"]["json_errors"] and data["evidence"]["source_completeness"]["json_state"] == "INCOMPLETE"
    assert data["bgcs"][0]["riq_score"] is None and data["bgcs"][0]["kcb_cumulative"] == 42
    assert data["biological_absence"] == data["upstream_search_completion"] == "NOT_ESTABLISHED"


def test_unbound_foreign_and_tampered_evidence_are_held(tmp_path):
    path = archive(tmp_path / "input.zip")
    a = CapturedIntakeSession.capture(path, policy=POLICY); b = CapturedIntakeSession.capture(path, policy=POLICY)
    bound = a.parse_evidence(EvidenceOptions(budget_seconds=0))
    for supplied in [{}, bound, replace(bound, _payload=b"{}")]:
        session = b if supplied is bound else a
        with pytest.raises(CapturedIntakeHold, match="BINDING_REFUSED"):
            session.working_evidence(supplied)


def test_unavailable_consumers_hold_before_capture(tmp_path, monkeypatch):
    def forbidden(*a, **k): pytest.fail("unavailable consumer captured source")
    monkeypatch.setattr(ArchiveSnapshot, "capture", forbidden)
    out = tmp_path / "out"
    assert cli.main(args(tmp_path / "missing.zip", out, "--consumer", "gold")) == 2
    assert not out.exists()


@pytest.mark.parametrize("value", ["0", "-1"])
def test_nonpositive_policy_refused_without_outputs(tmp_path, value):
    out = tmp_path / "out"; path = archive(tmp_path / "input.zip")
    assert cli.main(args(path, out, "--max-members", value)) == 2
    assert not out.exists()



def test_bound_options_cannot_be_relabelled(tmp_path):
    session = CapturedIntakeSession.capture(archive(tmp_path / "input.zip"), policy=POLICY)
    bound = session.parse_evidence(EvidenceOptions(budget_seconds=0))
    changed = replace(bound, options=EvidenceOptions("full", True, True, 0))
    with pytest.raises(CapturedIntakeHold, match="BINDING_REFUSED"):
        session.working_evidence(changed)


def test_reused_capture_must_fit_explicit_session_policy(tmp_path):
    snapshot = ArchiveSnapshot.capture(archive(tmp_path / "input.zip"), policy=POLICY)
    with pytest.raises(CapturedIntakeHold, match="POLICY_MISMATCH"):
        CapturedIntakeSession(snapshot, policy=ArchiveSnapshotPolicy(1, 30, 100000))


def test_actual_cli_fallback_backend(tmp_path, monkeypatch):
    path = archive(tmp_path / "input.zip"); out = tmp_path / "out"
    monkeypatch.setattr(parsers, "_require_seqio", lambda: None)
    assert cli.main(args(path, out, "--strain", "SYNTHETIC-FALLBACK")) == 0
    data, manifest = load(out)
    assert data["assembly"]["genome_bp"] == 12 and data["bgcs"][0]["contig"] == CID
    assert data["evidence"]["kcb_assignment_audit"]["status"] == "PASS"
    assert manifest["input_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
