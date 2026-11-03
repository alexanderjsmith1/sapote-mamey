"""Malformed ZIP diagnostics stay distinct from successful hygiene checks."""
from pathlib import Path
import importlib.util, os, shutil, subprocess, sys, zipfile
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("payload",[b"",b"not a ZIP file"])
def test_malformed_zip_cli_reports_hold_without_traceback(tmp_path,payload):
    tools=tmp_path/"tools";tools.mkdir()
    for name in ("preflight_zip_hygiene.py","zip_hygiene_allowlist.py","_console.py"):
        shutil.copyfile(ROOT/"tools"/name,tools/name)
    (tools/"zip_hygiene_allowlist.tsv").write_text("# optional empty policy\n")
    archive=tmp_path/"fixture.zip";archive.write_bytes(payload);env=os.environ.copy();env["PYTHONDONTWRITEBYTECODE"]="1"
    q=subprocess.run([sys.executable,"-B",str(tools/"preflight_zip_hygiene.py"),str(archive)],env=env,capture_output=True,text=True)
    assert q.returncode==2 and "ZIP_HYGIENE_ARCHIVE_HOLD" in q.stderr
    assert "BadZipFile" in q.stderr and "Traceback" not in q.stderr and q.stdout==""

def test_callable_main_preserves_badzip_exception(tmp_path):
    path=ROOT/"tools/preflight_zip_hygiene.py";spec=importlib.util.spec_from_file_location("zip_archive_api",path);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    archive=tmp_path/"fixture.zip";archive.write_bytes(b"not a ZIP file")
    with pytest.raises(zipfile.BadZipFile):tool.main(["preflight",str(archive)])


def test_directory_archive_cli_reports_io_hold(tmp_path):
    tools=tmp_path/"tools";tools.mkdir()
    for name in ("preflight_zip_hygiene.py","zip_hygiene_allowlist.py","_console.py"):
        shutil.copyfile(ROOT/"tools"/name,tools/name)
    archive=tmp_path/"archive_directory";archive.mkdir();env=os.environ.copy();env["PYTHONDONTWRITEBYTECODE"]="1"
    q=subprocess.run([sys.executable,"-B",str(tools/"preflight_zip_hygiene.py"),str(archive)],env=env,capture_output=True,text=True)
    assert q.returncode==2 and "ZIP_HYGIENE_ARCHIVE_HOLD" in q.stderr
    assert "IsADirectoryError" in q.stderr and "Traceback" not in q.stderr and q.stdout==""

def test_callable_scan_and_output_errors_remain_distinct(tmp_path,monkeypatch):
    path=ROOT/"tools/preflight_zip_hygiene.py";spec=importlib.util.spec_from_file_location("zip_archive_io_api",path);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    archive=tmp_path/"fixture.zip";archive.write_bytes(b"placeholder")
    def denied(_):raise PermissionError("synthetic denied")
    monkeypatch.setattr(tool,"scan",denied)
    with pytest.raises(PermissionError):tool.main(["preflight",str(archive)])
    with pytest.raises(tool.ZipArchiveIOError) as error:tool.main(["preflight",str(archive)],_cli_archive_errors=True)
    assert isinstance(error.value.__cause__,PermissionError)
    monkeypatch.setattr(tool,"scan",lambda _:{"cache":[],"hidden":[],"large":[]})
    def output_failure(*a,**kw):raise BrokenPipeError("synthetic output")
    monkeypatch.setattr(tool,"emit",output_failure)
    with pytest.raises(BrokenPipeError):tool.main(["preflight",str(archive)],_cli_archive_errors=True)
