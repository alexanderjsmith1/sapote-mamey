from pathlib import Path
import importlib.util
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("review_tool", ROOT / "tools/check_chatgpt_next_paths.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

@pytest.mark.parametrize("state", ["SAVE STATE not saved", "SAVE STATE — not saved",
                                  "SAVE STATE — savedness", "SAVE STATE — saved but not saved"])
def test_negative_save_claim_is_rejected(tmp_path, state):
    handoff = tmp_path / "handoff.md"
    handoff.write_text("1. Inspect current source bindings.\n2. Compare the retained regression receipts.\n3. "
                       + state + " [checkpoint](STATE.md)\n")
    assert tool.main(str(handoff)) == 1

@pytest.mark.parametrize("state", ["SAVE STATE — saved [checkpoint](STATE.md)", "SAVE STATE — FAILED"])
def test_explicit_legacy_save_claim(tmp_path, state):
    handoff = tmp_path / "handoff.md"
    handoff.write_text("1. Inspect current source bindings.\n2. Compare the retained regression receipts.\n3. "
                       + state + "\n")
    assert tool.main(str(handoff)) == 0
