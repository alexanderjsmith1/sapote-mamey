"""v9.7.156 — Bug 1 root cause: _run_locus_maps must return an int figure count.

render_for_compile_report returns {"rendered": [bgc_ids]} (a list). The prior
`res.get("rendered", 0) or len(res.get("files", []))` short-circuited on the
truthy list and returned the list itself as the count, so the runner emitted
{"figures": <list>} into the summary JSON. See PATCH_CHAT_MEMO 2026-06-30 Bug 1.
"""
from pathlib import Path
import mamey.render_all_figures as raf


def test_locus_maps_runner_normalizes_list_rendered_to_count(tmp_path, monkeypatch):
    monkeypatch.setattr(
        raf, "_run_locus_maps", raf._run_locus_maps  # ensure real fn
    )
    import mamey.locus_map as lm
    monkeypatch.setattr(
        lm, "render_for_compile_report",
        lambda pkg, top_n=10: {"rendered": ["BGC001", "BGC002", "BGC003"], "out": str(Path(pkg) / "locus_maps")},
    )
    out = raf._run_locus_maps(tmp_path, top_n=3)
    assert out["status"] == "RAN"
    assert out["figures"] == 3, f"expected int 3, got {out['figures']!r}"
    assert isinstance(out["figures"], int)


def test_locus_maps_runner_handles_int_rendered(tmp_path, monkeypatch):
    import mamey.locus_map as lm
    monkeypatch.setattr(
        lm, "render_for_compile_report",
        lambda pkg, top_n=10: {"rendered": 5, "out": str(Path(pkg) / "locus_maps")},
    )
    out = raf._run_locus_maps(tmp_path, top_n=5)
    assert out["figures"] == 5 and isinstance(out["figures"], int)


def test_locus_maps_runner_empty_rendered_is_skipped(tmp_path, monkeypatch):
    import mamey.locus_map as lm
    monkeypatch.setattr(
        lm, "render_for_compile_report",
        lambda pkg, top_n=10: {"rendered": [], "out": str(Path(pkg) / "locus_maps")},
    )
    out = raf._run_locus_maps(tmp_path, top_n=3)
    assert out["figures"] == 0 and out["status"] == "SKIPPED"
