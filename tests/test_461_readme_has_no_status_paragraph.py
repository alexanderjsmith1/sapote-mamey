from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_drops_the_status_and_other_organisms_paragraphs():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in (
        "**Status.** The program and documentation are under active development",
        "known\ngaps in metadata handling",
        "several basidiomycetes and ascomycetous fungi",
    ):
        assert phrase not in text
    assert "## What you can do" in text
