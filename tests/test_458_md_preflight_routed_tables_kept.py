"""sapote_md_preflight keeps routed wide tables when --appendix-md is not given.

Wide tables were cut from the boss markdown and written only to --appendix-md; without that
option they existed nowhere, while the output still said "use the technical appendix".
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("sapote_md_preflight_458", ROOT / "tools" / "sapote_md_preflight.py")
mp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mp)

WIDE = "| " + " | ".join(f"c{i}" for i in range(9)) + " |\n|" + "---|" * 9 + "\n| " + " | ".join(f"v{i}" for i in range(9)) + " |\n"


def test_routed_table_lands_in_a_default_sidecar(tmp_path):
    src = tmp_path / "in.md"
    src.write_text("# Report\n\n" + WIDE)
    out = tmp_path / "boss.md"
    mp.main([str(src), str(out)])
    side = tmp_path / "boss.appendix.md"
    assert side.exists() and "| c0 | c1" in side.read_text()
    assert "| c0 | c1" not in out.read_text()


def test_no_wide_table_writes_no_sidecar(tmp_path):
    src = tmp_path / "in.md"
    src.write_text("# Report\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    out = tmp_path / "boss.md"
    mp.main([str(src), str(out)])
    assert not (tmp_path / "boss.appendix.md").exists()


def test_explicit_appendix_path_is_still_used(tmp_path):
    src = tmp_path / "in.md"
    src.write_text("# Report\n\n" + WIDE)
    app = tmp_path / "chosen.md"
    mp.main([str(src), str(tmp_path / "boss.md"), "--appendix-md", str(app)])
    assert app.exists() and not (tmp_path / "boss.appendix.md").exists()
