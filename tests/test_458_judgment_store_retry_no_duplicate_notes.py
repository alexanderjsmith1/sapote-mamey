"""Re-recording a BGC's Mode B replaces its layperson and fermentation sections instead of repeating them.

The Mode B file is overwritten on a retry, but _append_section added the reader notes again,
so each retried save left another copy of the same BGC's paragraphs.
"""
from mamey import judgment_store as js


def _sections(path, bgc):
    return path.read_text(encoding="utf-8").count(f"## {bgc}\n")


def test_retry_replaces_reader_sections(tmp_path, monkeypatch):
    lay = tmp_path / "S1_laypersons_section.md"
    ferm = tmp_path / "S1_fermentation_section.md"
    monkeypatch.setattr(js, "_laypersons_path", lambda _p: lay)
    monkeypatch.setattr(js, "_fermentation_path", lambda _p: ferm)
    monkeypatch.setattr(js, "_update_register", lambda *a, **k: [])
    monkeypatch.setattr(js, "_mode_b_path", lambda _p, b: tmp_path / f"S1_{b}_mode_b.md")
    for text in ("first draft", "second draft"):
        js.record_mode_b(tmp_path, "BGC001", "## §1\nbody\n", layperson_paragraph=f"lay {text}",
                         fermentation_note=f"ferm {text}")
    js.record_mode_b(tmp_path, "BGC002", "## §1\nbody\n", layperson_paragraph="lay other",
                     fermentation_note="ferm other")
    for path, word in ((lay, "lay"), (ferm, "ferm")):
        text = path.read_text(encoding="utf-8")
        assert _sections(path, "BGC001") == 1 and _sections(path, "BGC002") == 1
        assert f"{word} second draft" in text and f"{word} first draft" not in text
        assert text.index("## BGC001") < text.index("## BGC002")
