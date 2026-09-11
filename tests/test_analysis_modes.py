"""Tests for the Layer-3 analysis modes: rare_motif, split_detector, bgc_walk.
Ground-truth-light smoke + logic tests (the modules need real antiSMASH GBKs for full runs;
these lock the importable API + the pure-logic pieces)."""
import ast
from pathlib import Path

import pytest

MAMEY = Path(__file__).resolve().parent.parent / "mamey"


def test_rare_motif_important_motifs_is_valid_dict():
    pytest.importorskip("Bio")  # rare_motif/split_detector import Bio at module top
    from mamey.rare_motif import IMPORTANT_MOTIFS
    assert isinstance(IMPORTANT_MOTIFS, dict)
    # every value is a human description string; keys are domain tokens
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in IMPORTANT_MOTIFS.items())
    # the discriminating markers the roadmap calls out must be present
    for key in ("PEP_mutase", "DHQ_synthase", "ene_KS", "Stand_Alone_Lasso_RRE"):
        assert key in IMPORTANT_MOTIFS


def test_rare_motif_scan_empty_dirs():
    pytest.importorskip("Bio")  # rare_motif/split_detector import Bio at module top
    from mamey.rare_motif import rare_motif_scan
    ranked, counts = rare_motif_scan([], rarity_threshold=2)
    assert ranked == [] and counts == {}


def test_split_detector_empty_dir_no_candidates():
    pytest.importorskip("Bio")  # rare_motif/split_detector import Bio at module top
    import tempfile
    from mamey.split_detector import detect
    with tempfile.TemporaryDirectory() as td:
        assert detect(td) == []


def test_modules_parse_and_expose_api():
    import pytest
    pytest.importorskip("pyhmmer")  # bgc_walk imports pyhmmer at module top; skip on a bare checkout
    import mamey.split_detector as sd
    import mamey.bgc_walk as bw
    assert hasattr(sd, "detect") and hasattr(sd, "detect_with_class_scoring")
    assert hasattr(bw, "bgc_walk") and hasattr(bw, "render_walk")
