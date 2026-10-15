import json
import pytest
from mamey import phylo_evidence as mod

@pytest.mark.parametrize("status", ["HOLD", "PASS"])
def test_cli_preserves_actual_receipt_state(tmp_path, monkeypatch, capsys, status):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"status": status}))
    monkeypatch.setattr(mod, "produce_phylo_evidence_receipt", lambda **kwargs: receipt)
    required = ("tree", "alignment", "gtotree-receipt", "iqtree-receipt", "marker-set-receipt", "outgroup-tip", "outgroup-registry", "ingroup-taxon", "tree-scope", "assembly-quality-flags", "package-tree-crosswalk", "host-table")
    args = [arg for key in required for arg in ("--" + key, "synthetic")]
    assert mod.main(args) == (0 if status == "PASS" else 2)
    assert json.loads(capsys.readouterr().out)["status"] == status
