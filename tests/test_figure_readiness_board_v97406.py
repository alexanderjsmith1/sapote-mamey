import hashlib, json
from pathlib import Path
import importlib.util

PATH=Path(__file__).parents[1]/"tools/figure_readiness_board.py"
spec=importlib.util.spec_from_file_location("figure_readiness_board",PATH); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_states_from_owner_blocks_and_bound_receipts(tmp_path):
    specs=tmp_path/"specs"; specs.mkdir()
    (specs/"REPAIR_SPEC_Q-001_A.md").write_text("# x\n## Owner binding required\nNone.\n## End\n")
    (specs/"REPAIR_SPEC_Q-002_B.md").write_text("# x\n## Owner binding required\n1. Exact field.\n## End\n")
    out=tmp_path/"out"; out.mkdir(); png=out/"x.png"; svg=out/"x.svg"; png.write_bytes(b"png"); svg.write_bytes(b"svg")
    def rec(p): return {"logical_locator":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size}
    rows=[{"figure_id":"Q001_A","binding_state":"BOUND","outputs":{"png":rec(png),"svg":rec(svg)}},
          {"figure_id":"Q002_B","binding_state":"PROVISIONAL_BINDING","outputs":{"png":rec(png),"svg":rec(svg)}}]
    (out/"figure_receipts.jsonl").write_text("\n".join(json.dumps(r) for r in rows)+"\n")
    board=mod.build_board(specs,tmp_path); states={r["queue_id"]:r["state"] for r in board["figures"]}
    assert states=={"Q-001":"RECEIPT_VERIFIED","Q-002":"PROVISIONAL"}

def test_no_receipt_states_and_malformed_receipt(tmp_path):
    specs=tmp_path/"specs"; specs.mkdir()
    (specs/"REPAIR_SPEC_Q-003_A.md").write_text("# x\n## Owner binding required\nNone for this repair.\n")
    (specs/"REPAIR_SPEC_Q-004_B.md").write_text("# x\n## Owner binding required\n1. Cohort.\n")
    states={r["queue_id"]:r["state"] for r in mod.build_board(specs,tmp_path)["figures"]}
    assert states=={"Q-003":"BOUND","Q-004":"OWNER_HELD"}
    bad=tmp_path/"bad"; bad.mkdir(); (bad/"figure_receipts.jsonl").write_text("{bad\n")
    try: mod.build_board(specs,tmp_path)
    except mod.ReadinessRefusal as exc: assert "READINESS_RECEIPT_INVALID" in str(exc)
    else: raise AssertionError("malformed receipt accepted")

def test_provisional_state_is_driven_by_the_shared_publication_gate(tmp_path, monkeypatch):
    # BC2-407: proves the board's PROVISIONAL classification is now delegated to
    # publication_bridge.validate_figure_receipt_for_publication rather than a second,
    # independently-drifting "binding_state == PROVISIONAL_BINDING" string check. A
    # receipt whose binding_state does NOT match that literal string, but which the
    # shared gate refuses for its own (here, arbitrary) reason, must still land as
    # PROVISIONAL -- proving the board asks the canonical gate, not its own copy of it.
    specs=tmp_path/"specs"; specs.mkdir()
    (specs/"REPAIR_SPEC_Q-005_A.md").write_text("# x\n## Owner binding required\nNone.\n## End\n")
    out=tmp_path/"out"; out.mkdir()
    (out/"figure_receipts.jsonl").write_text(
        json.dumps({"figure_id":"Q005_A","binding_state":"SOME_OTHER_UNBOUND_STATE"})+"\n"
    )

    def _always_refuse(receipt):
        raise mod.PublicationBridgeRefusal("FIGURE_PUBLICATION_TEST_REFUSAL: forced by test")

    monkeypatch.setattr(mod, "validate_figure_receipt_for_publication", _always_refuse)
    states={r["queue_id"]:r["state"] for r in mod.build_board(specs,tmp_path)["figures"]}
    assert states=={"Q-005":"PROVISIONAL"}

def test_readiness_board_imports_the_real_publication_bridge_gate():
    # No-regression / no-drift guard: the names the board relies on must be the actual
    # publication_bridge symbols, not local reimplementations that happen to share a name.
    from mamey.interactive_figures.publication_bridge import (
        PublicationBridgeRefusal,
        validate_figure_receipt_for_publication,
    )
    assert mod.PublicationBridgeRefusal is PublicationBridgeRefusal
    assert mod.validate_figure_receipt_for_publication is validate_figure_receipt_for_publication
