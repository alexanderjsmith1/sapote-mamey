"""Synthetic Markdown only: the preflight refuses to overwrite its input or existing outputs."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("md_preflight_fresh_464r3", ROOT / "tools/sapote_md_preflight.py")
mp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp)
WIDE = "| " + " | ".join(f"c{i}" for i in range(9)) + " |\n|" + "---|" * 9 + "\n| " + " | ".join(f"v{i}" for i in range(9)) + " |\n"


def _source(tmp_path):
    src = tmp_path / "source.md"
    src.write_text("# Source\n\n" + WIDE, encoding="utf-8")
    return src, src.read_bytes()


def test_output_equal_to_input_is_refused_even_with_replace(tmp_path):
    src, saved = _source(tmp_path)
    for extra in ([], ["--replace"]):
        assert mp.main([str(src), str(src), "--appendix-md", str(tmp_path / f"a{len(extra)}.md")] + extra) == 2
        assert src.read_bytes() == saved
    assert not list(tmp_path.glob("a*.md"))


def test_appendix_or_qa_equal_to_input_is_refused(tmp_path):
    src, saved = _source(tmp_path)
    assert mp.main([str(src), str(tmp_path / "boss.md"), "--appendix-md", str(src), "--replace"]) == 2
    assert mp.main([str(src), str(tmp_path / "boss.md"), "--qa-json", str(src), "--replace"]) == 2
    assert src.read_bytes() == saved
    assert not (tmp_path / "boss.md").exists()


def test_explicit_appendix_and_qa_must_differ(tmp_path):
    src, _ = _source(tmp_path)
    same = tmp_path / "side.txt"
    assert mp.main([str(src), str(tmp_path / "boss.md"), "--appendix-md", str(same), "--qa-json", str(same)]) == 2
    assert not same.exists() and not (tmp_path / "boss.md").exists()


def test_existing_output_needs_replace(tmp_path):
    src, _ = _source(tmp_path)
    boss = tmp_path / "boss.md"
    boss.write_text("PRIOR", encoding="utf-8")
    app = tmp_path / "app.md"
    assert mp.main([str(src), str(boss), "--appendix-md", str(app)]) == 2
    assert boss.read_text() == "PRIOR" and not app.exists()
    assert mp.main([str(src), str(boss), "--appendix-md", str(app), "--replace"]) == 0
    assert "| c0 | c1" not in boss.read_text() and "| c0 | c1" in app.read_text()


def test_fresh_outputs_still_work(tmp_path):
    src, saved = _source(tmp_path)
    assert mp.main([str(src), str(tmp_path / "boss.md"), "--qa-json", str(tmp_path / "qa.json")]) == 0
    assert (tmp_path / "boss.appendix.md").exists()
    assert src.read_bytes() == saved
