"""v9.7.409 — gates that the hostile audit of the sealed .408 artifact found open (Black Cherry, 2026-09-04).

Each test names the attack that got through on .408 and pins the fail-closed behaviour now required."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"


# H2 — strain id is a path component -------------------------------------------------------------
@pytest.mark.parametrize("bad", ["../escaped", "a/b", "a\\b", "AS-1; echo X", "$(id)", "AS 1", "", ".hidden", "x" * 65])
def test_unsafe_strain_ids_are_refused(bad):
    from mamey.strain_identity import validate_strain_id, UnsafeStrainId
    with pytest.raises(UnsafeStrainId):
        validate_strain_id(bad)


@pytest.mark.parametrize("good", ["AS-40", "SID10815", "Nocardia_fusca", "GCF_000123.1", "T-01.v2"])
def test_safe_strain_ids_pass(good):
    from mamey.strain_identity import validate_strain_id
    assert validate_strain_id(good) == good


def test_run_refuses_traversal_strain_id_and_writes_nothing(tmp_path):
    out = tmp_path / "out"; out.mkdir()
    r = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "run", "--strain", "../escaped",
                        "--input-zip", str(SMOKE), "--outdir", str(out), "--mode", "gold",
                        "--capped-session", "--json-evidence", "off"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=300)
    assert r.returncode == 2, r.stdout[-400:] + r.stderr[-400:]
    assert "REFUSED" in r.stderr
    assert not (tmp_path / "escaped").exists(), "on .408 this directory was created OUTSIDE --outdir"
    assert not any(out.iterdir()), "nothing may be written for a refused strain id"


# H1 — single-digit private prefix bypassed the non-overridable leak guard --------------------------
@pytest.mark.parametrize("sid", ["AJS-9", "AJS9", "AJS-99", "AJS-327", "PENDING-3"])
def test_public_override_refused_for_every_private_prefix_width(sid):
    from mamey.dedup_and_guard import resolve_release
    release, refused = resolve_release(sid, "PUBLIC")
    assert (release, refused) == ("PRIVATE", True), f"{sid}: PUBLIC override must be refused"


# H5 — structure gate reported PASS on files it never evaluated ------------------------------------
def _fresh_package(tmp_path: Path) -> Path:
    out = tmp_path / "run"
    r = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "run", "--strain", "TEST-01",
                        "--input-zip", str(SMOKE), "--outdir", str(out), "--mode", "gold",
                        "--capped-session", "--json-evidence", "off"], cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-600:]
    return out / "TEST-01" / "package"


@pytest.mark.parametrize("content,expect_code", [("", "EMPTY_CARD"), ("# not a card\n\nhello\n", "UNRESOLVED_BGC")])
def test_ingest_never_reports_structure_pass_for_a_non_card(tmp_path, content, expect_code):
    from mamey.mode_b_receipt import ingest_one_card
    pkg = _fresh_package(tmp_path)
    card = tmp_path / "x.md"; card.write_text(content, encoding="utf-8")
    summary = ingest_one_card(pkg, card)
    findings = summary["structure_findings"]
    assert findings and findings[0]["severity"] == "ERROR" and findings[0]["code"] == expect_code, summary
    assert summary["status"] in {"NO_CONTENT", "UNRESOLVED_BGC"}


# H3 — validate ignored a manifest whose identity disagreed with the package files --------------------
def test_validate_fails_when_manifest_strain_id_disagrees_with_files(tmp_path):
    from mamey.validate import validate_package
    pkg = _fresh_package(tmp_path)
    assert validate_package(pkg)["identity_binding"] == "PASS"
    m = json.loads((pkg / "manifest.json").read_text(encoding="utf-8")); m["strain_id"] = "AS-999"; m["strain"] = "AS-999"
    (pkg / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    res = validate_package(pkg)
    assert res["identity_binding"] == "FAIL" and res["status"] == "FAIL", res.get("identity_binding_detail")


# H4 — docs say `--json-evidence full` "refuses files >20 MB"; measured: with the vendored ijson such files are
# STREAMED and used (antismash_version binds from the JSON). The size guard on the eager branch is unreachable
# with ijson present. Pin the true contract: a 21 MB antiSMASH JSON under `full` is read, not dropped. -----------
def test_oversize_json_is_still_read_under_full_mode(tmp_path):
    big = tmp_path / "big.zip"
    with zipfile.ZipFile(SMOKE) as src, zipfile.ZipFile(big, "w") as dst:
        for n in src.namelist():
            dst.writestr(n, src.read(n))
        dst.writestr("smoke/NODE_1.json", '{"version":"7.0","records":[{"id":"NODE_1","pad":"' + "x" * 21_000_000 + '"}]}')
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "run", "--strain", "T7", "--input-zip", str(big),
                        "--outdir", str(out), "--mode", "gold", "--json-evidence", "full"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-600:]
    intake = json.loads((out / "T7" / "package" / "T7_1_intake.json").read_text(encoding="utf-8"))
    assert intake.get("antismash_version") == "7.0", "the 21 MB JSON must have been read (streamed), not silently dropped"


# H7 — DOS-epoch entries extract to 1979 in western timezones and cannot be re-zipped ---------------
def test_archive_epoch_is_safe_in_every_timezone():
    sys.path.insert(0, str(ROOT / "tools"))
    import importlib
    mod = importlib.import_module("finalize_public_archive")
    assert mod._ZIP_EPOCH >= (1980, 1, 2, 0, 0, 0)
    import datetime as dt
    assert dt.datetime(*mod._ZIP_EPOCH) - dt.timedelta(hours=14) >= dt.datetime(1980, 1, 1), "must stay ≥1980 at UTC-14"
