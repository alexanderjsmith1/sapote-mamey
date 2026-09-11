from pathlib import Path
from types import SimpleNamespace
import hashlib
import zipfile
import pytest

SOURCE=Path(__file__).parents[1]/"tests/fixtures/synthetic_single_contig_antismash.zip"

def test_shared_fixture_preserves_content_and_original_guard(tmp_path):
    from tools.fixture_inputs import prepare_single_contig_fixture
    from mamey.parsers import assembly_metrics_from_zip, GbkSizeGuardRefusal
    original=SOURCE.read_bytes()
    with pytest.raises(GbkSizeGuardRefusal):assembly_metrics_from_zip(SOURCE)
    target=tmp_path/"admitted.zip"
    receipt=prepare_single_contig_fixture(SOURCE,target)
    assert SOURCE.read_bytes()==original
    assert receipt["source_sha256"]==hashlib.sha256(original).hexdigest()
    assert receipt["prepared_sha256"]==hashlib.sha256(target.read_bytes()).hexdigest()
    with zipfile.ZipFile(SOURCE) as left,zipfile.ZipFile(target) as right:
        assert left.namelist()==right.namelist()
        for name in left.namelist():assert left.read(name)==right.read(name)
    assert assembly_metrics_from_zip(target)

def test_shared_fixture_refuses_unbound_input_before_output(tmp_path):
    from tools.fixture_inputs import prepare_single_contig_fixture
    source=tmp_path/"unknown.zip";source.write_bytes(SOURCE.read_bytes()+b"changed")
    target=tmp_path/"admitted.zip"
    with pytest.raises(ValueError,match="source hash"):prepare_single_contig_fixture(source,target)
    assert not target.exists()

def test_shared_fixture_cannot_clobber_output(tmp_path):
    from tools.fixture_inputs import prepare_single_contig_fixture
    target=tmp_path/"admitted.zip";target.write_bytes(b"keep")
    with pytest.raises(FileExistsError):prepare_single_contig_fixture(SOURCE,target)
    assert target.read_bytes()==b"keep"

@pytest.mark.parametrize("policy", ["single_contig_stored_fasta_v1", "single_contig_full_locus_runtime_v1"])
def test_harness_uses_declared_preparation_and_reports_binding(tmp_path,monkeypatch,policy):
    import tools.determinism_fingerprint as det
    spec=det._load_json(det.DEFAULT_INVENTORY)
    case=next(c for c in spec["package_runs"] if c["id"]=="synthetic_single_contig")
    assert case["fixture_preparation"]=="single_contig_full_locus_runtime_v1"
    case = {**case, "fixture_preparation": policy}
    observed=[]
    def run(command,*args):
        observed.append(Path(command[command.index("--input-zip")+1]))
        return SimpleNamespace(returncode=1,stdout="fixture pipeline stopped",stderr="")
    monkeypatch.setattr(det,"_run",run)
    result=det._run_package_case(case,tmp_path,{})
    assert result["status"]=="RUN_FAILED"
    assert observed[0]!=SOURCE and observed[0].is_file()
    assert result["fixture_preparation"]["policy"]==policy
    if policy == "single_contig_full_locus_runtime_v1":
        assert result["fixture_preparation"]["declared_full_contig"]=="SYNTHETIC_CONTIG_000001"
        assert result["fixture_preparation"]["source_sequence_bases"]==100000
        assert len(result["fixture_preparation"]["member_mapping"])==7
    assert result["fixture_preparation"]["source_sha256"]==case["input_sha256"]
    assert result["fixture_preparation"]["prepared_sha256"]==hashlib.sha256(observed[0].read_bytes()).hexdigest()


def test_fixture_preparation_uses_admitted_bytes_not_reopened_source(tmp_path,monkeypatch):
    import io
    import tools.fixture_inputs as fixture
    real_zip=zipfile.ZipFile
    altered=io.BytesIO()
    with real_zip(SOURCE) as original,real_zip(altered,"w") as replacement:
        for info in original.infolist():
            content=original.read(info)
            if info.filename.endswith(".fasta"):content=b">changed\nACGT\n"
            replacement.writestr(info,content)
    def swapped_open(file,*args,**kwargs):
        if isinstance(file,(str,Path)) and Path(file)==SOURCE:
            return real_zip(io.BytesIO(altered.getvalue()),*args,**kwargs)
        return real_zip(file,*args,**kwargs)
    monkeypatch.setattr(fixture.zipfile,"ZipFile",swapped_open)
    target=tmp_path/"admitted.zip"
    fixture.prepare_single_contig_fixture(SOURCE,target)
    with real_zip(SOURCE) as original,real_zip(target) as prepared:
        for name in original.namelist():assert original.read(name)==prepared.read(name)


def test_helper_refuses_duplicate_members_before_output(tmp_path,monkeypatch):
    import tools.fixture_inputs as fixture
    source=tmp_path/"duplicate.zip"
    with zipfile.ZipFile(source,"w") as archive:
        archive.writestr("duplicate.txt",b"first")
        with pytest.warns(UserWarning):archive.writestr("duplicate.txt",b"second")
    # Substitute a governed digest only in this hostile unit fixture; production
    # remains bound to the original shipped archive's literal SHA-256.
    monkeypatch.setattr(fixture,"_SINGLE_CONTIG_SHA256",hashlib.sha256(source.read_bytes()).hexdigest())
    target=tmp_path/"prepared.zip"
    with pytest.raises(ValueError,match="duplicate"):fixture.prepare_single_contig_fixture(source,target)
    assert not target.exists()

def test_harness_preparation_collision_is_structured_and_non_clobbering(tmp_path,monkeypatch):
    import tools.determinism_fingerprint as det
    case=next(c for c in det._load_json(det.DEFAULT_INVENTORY)["package_runs"] if c["id"]=="synthetic_single_contig")
    target=tmp_path/case["id"]/"admitted_synthetic_input.zip"
    target.parent.mkdir();target.write_bytes(b"preserve")
    def forbidden(*args):raise AssertionError("pipeline must not run after preparation refusal")
    monkeypatch.setattr(det,"_run",forbidden)
    result=det._run_package_case(case,tmp_path,{})
    assert result["status"]=="RUN_FAILED" and result["runs"]==[]
    assert result["fixture_preparation"]["status"]=="FAILED"
    assert result["fixture_preparation"]["error_type"]=="FileExistsError"
    assert target.read_bytes()==b"preserve"
    assert not det.report_ok({"inventory_coverage":{"complete":True},"inputs":{case["id"]:result}})
