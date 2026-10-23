"""Gray protein-search labels on gap-rescue maps decode HTML entities from the BLASTp consensus names (Codex Y01, 22 Oct)."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("glm_entities", ROOT / "tools" / "gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec); sys.modules[spec.name] = glm; spec.loader.exec_module(glm)


@pytest.mark.parametrize("raw,want", [
    ("4&apos;-phosphopantetheinyl transferase", "4'-phosphopantetheinyl transferase"),
    ("ATP &amp; binding", "ATP & binding"),
    ("3&#39;-processing protein", "3'-processing protein"),
    ("plain protein", "plain protein"),
])
def test_entities_decoded_and_row_unchanged(raw, want):
    row = {"top10_consensus_name": raw, "db": "nr", "top10_mean_identity": "91"}
    before = dict(row)
    assert glm._blastp_label(row, name_chars=1000) == want + " (nr 91%)"
    assert row == before
