# Synthetic regression inputs only.
"""write-narrative does not replace an authored section unless --force is given, and stages uniquely."""
from __future__ import annotations

import json
from types import SimpleNamespace

from mamey.compile_report import narrative_filename, write_narrative, write_narrative_command

CLEAN = "A capacity-based description of the strain's biosynthetic potential."


def _pkg(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "SYN-1"}), encoding="utf-8")
    return pkg


def test_second_write_is_refused_and_keeps_the_first(tmp_path):
    pkg = _pkg(tmp_path)
    first = write_narrative(pkg, "executive_summary", CLEAN)
    assert first["status"] == "WRITTEN"
    second = write_narrative(pkg, "executive_summary", "A different capacity-based text.")
    assert second["status"] == "EXISTS"
    assert (pkg / "judgment" / narrative_filename("executive_summary", "SYN-1")).read_text() == CLEAN


def test_force_replaces(tmp_path):
    pkg = _pkg(tmp_path)
    write_narrative(pkg, "executive_summary", CLEAN)
    res = write_narrative(pkg, "executive_summary", "Replacement capacity-based text.", force=True)
    assert res["status"] == "WRITTEN"
    assert "Replacement" in (pkg / "judgment" / narrative_filename("executive_summary", "SYN-1")).read_text()


def test_fixed_tmp_sibling_is_not_overwritten(tmp_path):
    pkg = _pkg(tmp_path)
    jd = pkg / "judgment"
    jd.mkdir()
    name = narrative_filename("executive_summary", "SYN-1")
    stray = jd / (name + ".tmp")
    stray.write_text("someone else's file", encoding="utf-8")
    assert write_narrative(pkg, "executive_summary", CLEAN)["status"] == "WRITTEN"
    assert stray.read_text(encoding="utf-8") == "someone else's file"
    assert sorted(p.name for p in jd.iterdir()) == sorted([name, name + ".tmp"])


def test_cli_exit_code_for_existing_section(tmp_path, capsys):
    pkg = _pkg(tmp_path)
    src = tmp_path / "in.md"
    src.write_text(CLEAN, encoding="utf-8")
    args = SimpleNamespace(package_dir=str(pkg), section="executive_summary", file=str(src), force=False)
    assert write_narrative_command(args) == 0
    assert write_narrative_command(args) == 4
    assert "already exists" in capsys.readouterr().err
