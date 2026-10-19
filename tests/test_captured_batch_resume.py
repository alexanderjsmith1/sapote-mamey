"""Tiny actual-pipeline batch/resume plus explicit fault interfaces; no real biological input."""
from pathlib import Path
from copy import copy
import hashlib
import json
import zipfile
import pytest

try:
    from .test_captured_actual_run import fixture_archive, inputs, run_args
except ImportError:
    from test_captured_actual_run import fixture_archive, inputs, run_args
from mamey import cli, captured_run, captured_batch, capture_completion
from mamey.intake_session import CapturedIntakeHold


def parse(argv):
    return cli.build_parser().parse_args(argv)


def batch_inputs(tmp_path):
    one = fixture_archive(tmp_path / "one.zip")
    two = fixture_archive(tmp_path / "two.zip", malformed_json=True)
    # Distinct fabricated biological identity; preserve malformed evidence in the second.
    with zipfile.ZipFile(two) as z:
        members = [(i.filename, z.read(i).replace(b"SYNTHETICCASE", b"SYNTHETICCASE_TWO")) for i in z.infolist()]
    with zipfile.ZipFile(two, "w") as z:
        for name, data in members:
            z.writestr(name, data)
    policy = tmp_path / "batch-policy.json"
    policy.write_text(json.dumps(dict(max_archive_bytes=64000, max_members=30,
        max_total_uncompressed_bytes=100000, max_publish_bytes=64000000,
        max_batch_inputs=2, max_batch_archive_bytes=128000,
        max_batch_uncompressed_bytes=200000, max_worker_threads=1)))
    return one, two, policy


def batch_args(tmp_path, sources, policy, *extra):
    return ["run", "--strains", *map(str, sources), "--outdir", str(tmp_path / "batch"),
            "--master", str(tmp_path / "master.xlsx"), "--brief", "none", "--locus-maps", "off",
            "--reference-completion", "off", "--json-evidence", "full", "--rggmci-threads", "1",
            "--capture-policy", str(policy), "--capture-batch-policy", "all-or-nothing", *extra]


def parsed_batch(tmp_path):
    one, two, policy = batch_inputs(tmp_path)
    return parse(batch_args(tmp_path, [one, two], policy)), one, two, policy


def stub_pipeline(private):
    root = Path(private.outdir) / private.strain / "package"
    root.mkdir(parents=True)
    (root / "run_phase_receipts.jsonl").write_text('{"phase":"SYNTHETIC_STUB","status":"OK"}\n')
    (root / "manifest.json").write_text(json.dumps({"strain": private.strain}))
    if private.master:
        from openpyxl import Workbook
        book = Workbook();book.active.append([private.strain]);book.save(private.master);book.close()
    return 0


def test_actual_single_completion_resume_and_changed_options_hold(inputs, tmp_path, monkeypatch):
    argv = run_args(inputs, tmp_path)
    assert cli.main(argv) == 0
    original = (tmp_path / "out/captured_completion.json").read_bytes()
    def forbidden(*a, **k):
        pytest.fail("verified resume reran scientific pipeline")
    monkeypatch.setattr(captured_run, "execute_stage", forbidden)
    assert cli.main([*argv, "--capture-resume"]) == 0
    assert (tmp_path / "out/captured_completion.json").read_bytes() == original
    assert cli.main([*argv, "--capture-resume", "--json-evidence", "full"]) == 2
    inputs[0].write_bytes(b"changed source")
    assert cli.main([*argv, "--capture-resume"]) == 2
    assert (tmp_path / "out/captured_completion.json").read_bytes() == original


def test_actual_batch_same_source_intrinsic_rg_missingness_and_resume(inputs, tmp_path, monkeypatch):
    one, two, policy = batch_inputs(tmp_path)
    argv = batch_args(tmp_path, [one, two], policy)
    from mamey import source_context, rggmci
    original = cli.extract_contig_sequences
    seen = []
    def extracted(locator):
        frame = source_context.active()
        assert frame is not None
        assert source_context.bound_source(locator) is frame.session.snapshot
        seen.append(frame.session.snapshot.input_sha256)
        return original(locator)
    monkeypatch.setattr(cli, "extract_contig_sequences", extracted)
    from mamey.archive_snapshot import ArchiveSnapshot
    actual_capture = ArchiveSnapshot.capture
    actual_open = Path.open
    blocked = set()
    saved_inputs = {p: p.read_bytes() for p in (one, two)}
    def captured(cls, path, **kwargs):
        snapshot = actual_capture(path, **kwargs)
        if kwargs.get("expected_sha256") is not None:
            selected = Path(path)
            selected.unlink()
            blocked.add(selected)
        return snapshot
    def opened(path, mode="r", *a, **k):
        assert path not in blocked or not ("r" in mode or "+" in mode), "reopened deleted admitted source"
        return actual_open(path, mode, *a, **k)
    monkeypatch.setattr(ArchiveSnapshot, "capture", classmethod(captured))
    monkeypatch.setattr(Path, "open", opened)
    assert cli.main(argv) == 0
    assert not one.exists() and not two.exists()
    monkeypatch.setattr(Path, "open", actual_open)
    monkeypatch.setattr(ArchiveSnapshot, "capture", actual_capture)
    for path, data in saved_inputs.items(): path.write_bytes(data)
    root = tmp_path / "batch"
    batch = json.loads((root / "CAPTURED_BATCH.json").read_text())
    assert len(batch["items"]) == 2 and len(set(seen)) == 2
    assert batch["publication_policy"] == "all-or-nothing"
    assert (tmp_path / "master.xlsx").is_file()
    from mamey.validate import verify_checksums
    for item in batch["items"]:
        package = Path(item["package"])
        assert package.is_dir() and not verify_checksums(package)
        manifest = json.loads((package / "manifest.json").read_text())
        receipt = manifest["captured_source"]
        assert receipt["input_sha256"] == item["source"]["input_sha256"]
        assert receipt["pin_origin"] == "PLANNED_CONSUMED_VERSION"
        assert receipt["original_version"] == "ORIGINAL_VERSION_UNASSERTED"
        assert receipt["replay_version_verified"] is True
        assert receipt["denominator"]["value"] == 1
        assert receipt["denominator"]["expected_biological_total"] is None
        assert manifest["bgcs"][0]["riq_score"] is None
        assert manifest["bgcs"][0]["kcb_cumulative"] == 42
        assert not [p for p in package.rglob("*") if p.suffix.lower() in {".png", ".pdf", ".svg"}]
        assert all(".mamey-captured-batch-" not in p.read_text() for p in package.glob("*.json"))
    partial = batch["items"][1]["source"]["source_completeness"]
    assert partial["json_state"] == "INCOMPLETE"
    before = len(seen)
    assert cli.main([*argv, "--capture-resume"]) == 0 and len(seen) == before
    (root / "CAPTURED_BATCH.json").write_text("{}")
    assert cli.main([*argv, "--capture-resume"]) == 2


def test_second_source_changes_after_plan_all_or_nothing(tmp_path, monkeypatch):
    args, one, two, _ = parsed_batch(tmp_path)
    master = Path(args.master);master.write_bytes(b"old master")
    actual = captured_batch.plan
    def changed(*a):
        roster = actual(*a)
        two.write_bytes(b"changed after plan")
        return roster
    monkeypatch.setattr(captured_batch, "plan", changed)
    assert captured_batch.run_batch(args, stub_pipeline) == 2
    assert master.read_bytes() == b"old master" and not Path(args.outdir).exists()
    receipts = list(tmp_path.glob(".batch.captured-failure-*/FAILURE.json"))
    assert receipts and json.loads(receipts[0].read_text())["package_or_master_admitted"] is False


def test_second_pipeline_failure_preserves_first_item_and_master(tmp_path):
    args, _, _, _ = parsed_batch(tmp_path)
    master = Path(args.master);master.write_bytes(b"old master")
    calls = []
    def failed(private):
        calls.append(private.strain)
        stub_pipeline(private)
        return 0 if len(calls) == 1 else 2
    assert captured_batch.run_batch(args, failed) == 2
    assert len(calls) == 2 and master.read_bytes() == b"old master" and not Path(args.outdir).exists()
    retained = list(tmp_path.glob(".batch.captured-failure-*/runs/*/package/run_phase_receipts.jsonl"))
    assert len(retained) == 2


@pytest.mark.parametrize("mutation", ["policy", "code", "output", "master"])
def test_batch_resume_exact_bindings(tmp_path, monkeypatch, mutation):
    args, _, _, policy = parsed_batch(tmp_path)
    assert captured_batch.run_batch(args, stub_pipeline) == 0
    args.capture_resume = True
    assert captured_batch.run_batch(args, lambda _: pytest.fail("resume reran")) == 0
    if mutation == "policy":
        data = json.loads(policy.read_text());data["max_publish_bytes"] -= 1;policy.write_text(json.dumps(data))
    elif mutation == "code":
        monkeypatch.setattr(capture_completion, "code_binding", lambda: "0" * 64)
    elif mutation == "output":
        next(Path(args.outdir).glob("*/package/manifest.json")).write_text("changed output")
    else:
        Path(args.master).write_bytes(b"changed master")
    assert captured_batch.run_batch(args, lambda _: pytest.fail("held resume reran")) == 2


@pytest.mark.parametrize("mutation", ["duplicate", "identity", "count", "archive", "expanded", "threads", "policy"])
def test_batch_admission_refuses_before_work(tmp_path, mutation):
    args, one, two, policy = parsed_batch(tmp_path)
    data = json.loads(policy.read_text())
    if mutation == "duplicate": args.strains = [str(one), str(one)]
    elif mutation == "identity": two.write_bytes(one.read_bytes())
    elif mutation == "count": data["max_batch_inputs"] = 1
    elif mutation == "archive": data["max_batch_archive_bytes"] = 1
    elif mutation == "expanded": data["max_batch_uncompressed_bytes"] = 1
    elif mutation == "threads": args.rggmci_threads = 2
    else: args.capture_batch_policy = None
    policy.write_text(json.dumps(data))
    assert captured_batch.run_batch(args, lambda _: pytest.fail("held batch worked")) == 2
    assert not Path(args.outdir).exists() and not Path(args.master).exists()


def test_package_resume_preserves_capture_states_without_raw_locator(tmp_path, monkeypatch):
    from mamey import session_resume
    package = tmp_path / "package";package.mkdir()
    capture = {"input_sha256": "a" * 64, "original_version": "ORIGINAL_VERSION_UNASSERTED",
               "denominator": {"value": 1, "expected_biological_total": None, "whole_assembly_completeness": "UNKNOWN"},
               "source_completeness": {"json_state": "INCOMPLETE"}, "biological_absence": "NOT_ESTABLISHED"}
    (package / "manifest.json").write_text(json.dumps({"strain_id": "SYNTHETIC", "input_zip": "missing-raw.zip", "captured_source": capture}))
    (package / "SYNTHETIC_AntiSMASH_Evidence_Parse.json").write_text(json.dumps({"json_errors": ["fabricated malformed record"], "txt_errors": None}))
    original = Path.open
    def opened(path, *a, **k):
        assert "missing-raw.zip" not in str(path)
        return original(path, *a, **k)
    monkeypatch.setattr(Path, "open", opened)
    result = session_resume.build_resume(package)
    assert result["captured_source"] == capture
    assert result["captured_evidence_errors"]["SYNTHETIC_AntiSMASH_Evidence_Parse.json"]["txt_errors"] is None
    assert "INCOMPLETE" in result["markdown"] and '"expected_biological_total": null' in result["markdown"]


def test_batch_aggregate_publication_refusal_and_committed_error(tmp_path, monkeypatch):
    args, _, _, policy_path = parsed_batch(tmp_path)
    from mamey import captured_run
    master = Path(args.master);master.write_bytes(b'old master')
    data = json.loads(policy_path.read_text());data['max_publish_bytes'] = 100
    policy_path.write_text(json.dumps(data))
    assert captured_batch.run_batch(args, stub_pipeline) == 2
    assert master.read_bytes() == b'old master' and not Path(args.outdir).exists()
    data['max_publish_bytes'] = 64000000;policy_path.write_text(json.dumps(data))
    original = captured_run.publish_payloads
    def committed(payloads, *, replacement=None):
        original(payloads, replacement=replacement)
        error = OSError('fabricated after actual publisher commit')
        error.output_transaction_commit_status = 'COMMITTED'
        raise error
    monkeypatch.setattr(captured_run,'publish_payloads',committed)
    with pytest.raises(RuntimeError,match='COMMITTED_POSTCOMMIT_FAILURE'):
        captured_batch.run_batch(args, stub_pipeline)
    assert Path(args.outdir).is_dir() and master.read_bytes() != b'old master'


def test_referenced_option_files_change_resume_binding(tmp_path):
    args, _, _, path = parsed_batch(tmp_path)
    policy = captured_run.load_policy(path)
    roster = captured_batch.plan(args, policy)
    privacy = tmp_path/'synthetic-option.json';privacy.write_text('{"synthetic":1}')
    args.privacy_profile = str(privacy)
    before = capture_completion.binding(args, policy, roster)
    privacy.write_text('{"synthetic":2}')
    after = capture_completion.binding(args, policy, roster)
    assert before['options'] == after['options']
    assert before['referenced_option_files'] != after['referenced_option_files']


def test_saved_binding_does_not_alias_mutable_caller_options(tmp_path):
    args,_,_,path = parsed_batch(tmp_path)
    args.capture_harness_context = {'nested': {'value': [1]}}
    policy = captured_run.load_policy(path)
    identity = capture_completion.binding(args,policy,[])
    args.capture_harness_context['nested']['value'].append(2)
    policy['max_publish_bytes'] += 1
    assert identity['options']['capture_harness_context']['nested']['value'] == [1]
    assert identity['policy']['max_publish_bytes'] != policy['max_publish_bytes']


def test_failed_batch_resume_pins_saved_attempt_and_retries_unchanged(tmp_path,monkeypatch):
    args,one,two,_ = parsed_batch(tmp_path)
    def failed(private):
        stub_pipeline(private)
        return 2
    assert captured_batch.run_batch(args,failed)==2
    assert list(tmp_path.glob('.batch.captured-failure-*/BINDING.json'))
    args.capture_resume=True
    original=two.read_bytes()
    with zipfile.ZipFile(two) as archive:
        members=[(i.filename,archive.read(i)) for i in archive.infolist()]
    with zipfile.ZipFile(two,'w') as archive:
        for name,data in members:archive.writestr(name,data)
        archive.writestr('new-planned-version.txt','fabricated')
    assert captured_batch.run_batch(args,lambda _:pytest.fail('changed failed-attempt source ran'))==2
    two.write_bytes(original)
    assert captured_batch.run_batch(args,stub_pipeline)==0


def test_failed_single_resume_pins_saved_options(inputs,tmp_path,monkeypatch):
    argv=run_args(inputs,tmp_path)
    args=parse(argv)
    def failed(private):
        stub_pipeline(private)
        return 2
    assert captured_run.run(args,failed)==2
    args.capture_resume=True
    args.json_evidence='full'
    assert captured_run.run(args,lambda _:pytest.fail('changed failed-attempt options ran'))==2
    args.json_evidence='off'
    assert captured_run.run(args,stub_pipeline)==0


def test_resume_recaptures_against_stored_pin_not_new_consumed_digest(inputs,tmp_path,monkeypatch):
    args=parse(run_args(inputs,tmp_path))
    assert captured_run.run(args,stub_pipeline)==0
    digest=hashlib.sha256(inputs[0].read_bytes()).hexdigest()
    actual=captured_run.capture
    pins=[]
    def checked(args,policy,expected=None):
        pins.append(expected)
        return actual(args,policy,expected)
    monkeypatch.setattr(captured_run,'capture',checked)
    args.capture_resume=True
    assert captured_run.run(args,lambda _:pytest.fail('verified resume reran'))==0
    assert pins==[digest]
