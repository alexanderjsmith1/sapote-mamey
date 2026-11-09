"""protein_space_standalone: receipt and outputs are checked before work; replacement is identified.

Before: only the two HTML outputs were checked for existence. An existing receipt was replaced,
outputs could collide with each other or with a source, and --replace-candidate replaced any file.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pss_464r3", ROOT / "tools" / "protein_space_standalone.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def _paths(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    return [out / "Protein_Space.html", out / "Reference_Matches.html", out / "RECEIPT.json"]


def test_existing_receipt_is_refused(tmp_path):
    outputs = _paths(tmp_path)
    outputs[2].write_text("{}")
    with pytest.raises(ValueError, match="Output exists"):
        M.check_outputs(outputs, [], False)


def test_output_aliasing_an_input_or_another_output_is_refused(tmp_path):
    outputs = _paths(tmp_path)
    source = tmp_path / "viewer.html"
    source.write_text("source")
    with pytest.raises(ValueError, match="OUTPUT_ALIASES_INPUT"):
        M.check_outputs([source, outputs[1], outputs[2]], [source], True)
    with pytest.raises(ValueError, match="OUTPUT_COLLISION"):
        M.check_outputs([outputs[0], outputs[0], outputs[2]], [], False)


def test_replace_candidate_needs_a_matching_earlier_receipt(tmp_path):
    viewer_out, catalogue_out, receipt = _paths(tmp_path)
    viewer_out.write_text("old viewer")
    with pytest.raises(ValueError, match="REPLACE_CANDIDATE_UNIDENTIFIED"):
        M.check_outputs([viewer_out, catalogue_out, receipt], [], True)
    receipt.write_text(json.dumps({"schema": "sapote.protein_space.standalone.v1",
                                   "outputs": {str(viewer_out): "0" * 64}}))
    with pytest.raises(ValueError, match="REPLACE_CANDIDATE_UNIDENTIFIED"):
        M.check_outputs([viewer_out, catalogue_out, receipt], [], True)
    receipt.write_text(json.dumps({"schema": "sapote.protein_space.standalone.v1",
                                   "outputs": {str(viewer_out): hashlib.sha256(b"old viewer").hexdigest()}}))
    M.check_outputs([viewer_out, catalogue_out, receipt], [], True)


def test_all_fresh_outputs_pass(tmp_path):
    M.check_outputs(_paths(tmp_path), [tmp_path / "viewer.html"], False)
