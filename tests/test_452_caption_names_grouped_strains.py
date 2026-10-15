"""T1 caption half (.452): tip labels no longer carry a grouping suffix, so the caption names each drawn representative
and the strains merged into it; the measured bounds and members stay in the grouping table. Synthetic data only."""
import csv
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("placement_display_t1", HERE / "tools" / "placement_display.py")
pd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pd)


def _ledger(tmp_path, rows):
    path = tmp_path / "x_collapse_ledger.tsv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["tip", "representative_tip", "action"], delimiter="\t")
        w.writeheader(); w.writerows(rows)
    return path


LABELS = {"r1": "Synus alpha SYN 1 (T) (NR_000001.1)", "m1": "Synus alpha SYN 9 (T) (NR_000009.1)",
          "r2": "Synus beta B 2 (T) (NR_000002.1)", "m2": "Synus beta B 7 (T) (AB123456.1)", "q": "Synus sp. AS-1 (PX000001)"}


def test_caption_names_representative_and_members_without_accessions(tmp_path):
    led = _ledger(tmp_path, [
        {"tip": "r1", "representative_tip": "r1", "action": "COLLAPSED_REPRESENTATIVE"},
        {"tip": "m1", "representative_tip": "r1", "action": "COLLAPSED_MEMBER"},
        {"tip": "r2", "representative_tip": "r2", "action": "COLLAPSED_REPRESENTATIVE"},
        {"tip": "m2", "representative_tip": "r2", "action": "COLLAPSED_MEMBER"},
        {"tip": "q", "representative_tip": "q", "action": "RETAINED"}])
    s = pd.grouped_reference_sentence(led, LABELS, 1, 500)
    assert "Synus alpha SYN 1 (T) (also Synus alpha SYN 9 (T))" in s
    assert "Synus beta B 2 (T) (also Synus beta B 7 (T))" in s
    assert "NR_" not in s and "AB123456" not in s
    assert "at most 1 nt over at least 500 shared sites" in s and "supplementary grouping table" in s
    assert "(+" not in s and "grouped;" not in s


def test_no_grouping_adds_nothing(tmp_path):
    led = _ledger(tmp_path, [{"tip": "q", "representative_tip": "q", "action": "RETAINED"}])
    assert pd.grouped_reference_sentence(led, LABELS, 1, 500) == ""
    assert pd.grouped_reference_sentence(tmp_path / "missing.tsv", LABELS, 1, 500) == ""


def test_caption_no_longer_describes_a_label_suffix():
    src = (HERE / "tools" / "placement_display.py").read_text(encoding="utf-8")
    assert "marked (+N;" not in src and "grouped_reference_sentence(" in src


def test_grouping_sentence_is_added_for_every_caption_route():
    """Codex review P2: the call sat inside `label_style == "short" and not args.methods`, so default-style and
    supplied (--methods) captions lost the disclosure. It must be at the level where the caption is final."""
    import ast
    src = (HERE / "tools" / "placement_display.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "grouped_reference_sentence"]
    assert len(calls) == 1
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    node = calls[0]
    while node in parents:
        node = parents[node]
        if isinstance(node, ast.If):
            cond = ast.unparse(node.test)
            assert "label_style" not in cond and "methods" not in cond, cond
