"""test_exclusion_gate_integration.py — end-to-end proof that a hard-excluded strain
cannot validate as a GOVERNED sealed package (AMBER_EXCLUSION_HARDENING, .353 candidate).

The 12 unit tests in test_exclusion_gate.py exercise the gate module in isolation. This
integration test drives the real ``validate.validate_package`` over a minimal on-disk sealed
package and asserts the wired gate fires:

  * a package whose ``manifest.strain_id`` is hard-excluded (AS-920), AND
  * a bundled ``*master*.xlsx`` carrying an AS-920 row

both make ``validate_package`` report ``exclusion_gate == FAIL`` and overall
``status == FAIL``, with AS-920 named in the offenders.

Fail-closed: on the pre-fix .352 validator there is no ``exclusion_gate`` key at all, so the
``== "FAIL"`` assertions fail. A clean AS-40 control package must report the gate as PASS, so
the gate is not merely always-FAIL.

stdlib + pytest + openpyxl (a shipped dep). No network, no engine run.
"""
import json

import pytest

from mamey import validate

openpyxl = pytest.importorskip("openpyxl")


def _write_master_xlsx(path, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BGC_Master"
    ws.append(["strain", "bgc_id", "class"])
    for r in rows:
        ws.append(r)
    wb.save(str(path))


def _make_package(pkg_dir, strain_id, master_rows):
    pkg_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "mode": "gold",
        "strain_id": strain_id,
        "bgcs": [{"bgc_id": f"{strain_id}_BGC1"}],
    }
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _write_master_xlsx(pkg_dir / "project_master.xlsx", master_rows)
    return pkg_dir


def test_excluded_strain_package_fails_validation(tmp_path):
    pkg = _make_package(
        tmp_path / "AS-920_package",
        strain_id="AS-920",
        master_rows=[["AS-40", "AS-40_BGC1", "NRPS"],
                     ["AS-920", "AS-920_BGC3", "RiPP"]],  # excluded strain leaked into master
    )
    result = validate.validate_package(str(pkg))

    # fail-closed: pre-fix validator has no exclusion_gate key -> this assertion fails
    assert result.get("exclusion_gate") == "FAIL", \
        f"exclusion_gate not FAIL (got {result.get('exclusion_gate')!r}) — wiring missing"

    # AS-920 must be named among the offenders (package strain_id and/or master sheet)
    offenders = result.get("exclusion_gate_offenders", {})
    flat = json.dumps(offenders)
    assert "AS-920" in flat, f"AS-920 not named in offenders: {offenders!r}"

    # overall verdict must be a non-PASS FAIL
    assert result.get("status") == "FAIL", \
        f"overall status not FAIL for an excluded-strain package (got {result.get('status')!r})"


def test_clean_governed_package_passes_the_exclusion_gate(tmp_path):
    # positive control: a normal strain with a clean master must PASS the exclusion gate,
    # proving the gate is discriminating rather than always-FAIL. (Overall status may still
    # be FAIL/JUDGMENT_PENDING on other completeness gates — we only assert the exclusion gate.)
    pkg = _make_package(
        tmp_path / "AS-40_package",
        strain_id="AS-40",
        master_rows=[["AS-40", "AS-40_BGC1", "NRPS"],
                     ["AS-696", "AS-696_BGC2", "PKS"]],
    )
    result = validate.validate_package(str(pkg))
    assert result.get("exclusion_gate") == "PASS", \
        f"clean package tripped the exclusion gate: {result.get('exclusion_gate')!r} " \
        f"offenders={result.get('exclusion_gate_offenders')!r}"

