"""Protein-space page captions pluralize the legend label once: a label that is already plural is not given a second
"s" (seen as "isolatess" on the 15 Oct run-7 pages)."""
import importlib.util, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ppd", ROOT / "tools" / "protein_pcoa_page_docs.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_plural_keeps_plural_labels():
    assert m._plural("bee and wasp isolates") == "bee and wasp isolates"
    assert m._plural("cohort protein") == "cohort proteins"


def test_caption_builder_has_no_raw_s_suffix():
    src = (ROOT / "tools" / "protein_pcoa_page_docs.py").read_text()
    body = src[src.index("def caption_text"):]
    assert not re.search(r"\{who[^}]*\}s\b", body) and "}s are coloured" not in body
