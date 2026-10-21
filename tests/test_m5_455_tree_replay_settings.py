"""Lane CLAUDE_M5_v9.7.455_tree_display_options_v3: an exported tree source package replays every tree display
setting of the m5_452 card, including the three v2 settings GG_SUPPORT_POS, GG_SUPPORT_UNPLACED and GG_SCALE_PAGES
(before this lane they were dropped from the generated _rerender_captioned.sh, so a replay redrew sealed placement).
Runs the real exporter on a minimal synthetic source folder (as test_export_tree_source_package_runs_v97439.py)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/export_tree_figure_source_package.py"
SETTINGS = {"GG_PAGE_TITLE": "0", "GG_SUPPORT_MAX": "100", "GG_SCALE_OFFSET": "0.3", "GG_SUPPORT_POS": "auto",
            "GG_SUPPORT_UNPLACED": "omit", "GG_SCALE_PAGES": "last"}


def _make_source(src: Path, stem: str, env: dict) -> None:
    src.mkdir(parents=True)
    (src / f"{stem}_display.nwk").write_text("(A:0.1,B:0.1);\n")
    (src / f"{stem}_rect02.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (src / f"{stem}_rect02.pdf").write_bytes(b"%PDF-1.4\n")
    (src / f"{stem}_rect02.methods.txt").write_text("caption text\n")
    (src / "display_input.tsv").write_text("label\tsource\nA\tbee\n")
    (src / "display_input.fasta").write_text(">A\nACGT\n")
    (src / "METHODS.md").write_text("# methods\n")
    (src / "analysis.nwk").write_text("(A:0.1,B:0.1);\n")
    (src / "display_tree.nwk").write_text("(A:0.1,B:0.1);\n")
    (src / "display_meta.tsv").write_text("label\nA\n")
    (src / f"{stem}_display_receipt.json").write_text(json.dumps({
        "inputs": {"analysis_tree": {"path": "analysis.nwk"}},
        "outputs": {"tree": {"path": "display_tree.nwk"}, "metadata": {"path": "display_meta.tsv"}}}))
    (src / "placement_display_receipt.json").write_text(json.dumps({"render_environment": env}))


def _helper(tmp_path, env):
    src, out = tmp_path / "src", tmp_path / "out"
    _make_source(src, "SYN_tree_v1", env)
    r = subprocess.run([sys.executable, str(TOOL), str(src), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return next(out.glob("*_rerender_captioned.sh")).read_text()


def test_all_six_tree_display_settings_are_replayed(tmp_path):
    helper = _helper(tmp_path, dict(SETTINGS))
    for key, value in SETTINGS.items():
        assert f"export {key}={value}" in helper, key


def test_unlisted_settings_are_still_not_replayed(tmp_path):
    helper = _helper(tmp_path, dict(SETTINGS, GG_NOT_A_SETTING="1", PATH="/somewhere"))
    assert "GG_NOT_A_SETTING" not in helper and "export PATH=" not in helper


def test_v2_settings_absent_from_the_receipt_add_nothing(tmp_path):
    helper = _helper(tmp_path, {"GG_SUPPORT_MAX": "100"})
    assert "export GG_SUPPORT_MAX=100" in helper
    assert all(k not in helper for k in ("GG_SUPPORT_POS", "GG_SUPPORT_UNPLACED", "GG_SCALE_PAGES"))
