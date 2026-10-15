import importlib.util
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deliverable_tools"))
spec = importlib.util.spec_from_file_location("batch_context_candidate", ROOT / "deliverable_tools/batch_mibig_comparator_context.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

@pytest.mark.parametrize("mode", ["receipt_source", "output_symlink", "receipt_context"])
def test_all_batch_paths_are_admitted_before_output_writes(tmp_path, monkeypatch, mode):
    source_root = tmp_path / "reports"
    source_root.mkdir()
    source = source_root / "REPORT.html"
    source.write_text("original report")
    context = tmp_path / "context.json"
    context.write_text("original context")
    out = tmp_path / "output"
    receipt = source if mode == "receipt_source" else context if mode == "receipt_context" else None
    if mode == "output_symlink":
        out.mkdir()
        (out / "REPORT.html").symlink_to(source)
    monkeypatch.setattr(mod, "enhance_mibig_summary", lambda *args: ("candidate", dict.fromkeys(("rows", "unique_comparators", "activity_verified_context_rows", "mechanism_verified_context_rows", "no_admitted_comparator_rows", "comparator_context_unresolved_rows", "component_bound_rows"), 0)))
    with pytest.raises(ValueError):
        mod.build(source_root, out, tmp_path / "mibig", context, receipt)
    assert source.read_text() == "original report"
    assert context.read_text() == "original context"
    assert not (out / "MIBIG_COMPARATOR_CONTEXT_BATCH_RECEIPT.json").exists()
