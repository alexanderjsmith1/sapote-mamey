"""v9.7.418 — a bundle-only consumer must resolve the SHIPPED outgroup registry, not a missing path.

The registry that ships in the bundle is `mamey/data/outgroup_registry.tsv`. But `outgroup_registry.py`
(the outgroup generator used by phylo_place / phylo_refset) only ever searched env -> cwd-parents ->
file-parents for `OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv` and, finding none, returned that non-existent
path. The bundle ships NO `OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv` (verified), and nothing but this file's
own test reads the shipped `mamey/data/` copy — so a bundle-only run resolved the registry to a path
that does not exist and the generator went dark.

This guard pins the last-resort fallback to the shipped package asset. A workspace
`OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv` still wins when present, so this does NOT decide which table is
canonical (that is a separate, owner-level ruling); it only stops the hard failure for the shipped
tree. Filesystem/path resolution only; no scan, score, or biological claim. Judgment deferred.
"""
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    monkeypatch.syspath_prepend(str(ROOT))
    spec = importlib.util.spec_from_file_location("ogr_under_test", ROOT / "tools" / "outgroup_registry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_shipped_registry_path_points_at_the_bundled_asset(monkeypatch):
    mod = _load(monkeypatch)
    shipped = mod._shipped_registry_path()
    assert shipped is not None, "the shipped mamey/data/outgroup_registry.tsv must be resolvable"
    assert shipped.replace("\\", "/").endswith("mamey/data/outgroup_registry.tsv")
    assert os.path.exists(shipped), "the resolved shipped registry must actually exist on disk"


def test_registry_default_falls_back_to_shipped_when_no_official_data(monkeypatch):
    """With no OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv reachable, the resolver must return the shipped
    package asset — not `<ROOT>/OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv`, which does not exist in a bundle."""
    mod = _load(monkeypatch)
    for var in ("OUTGROUP_REGISTRY", "SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"):
        monkeypatch.delenv(var, raising=False)
    shipped = mod._shipped_registry_path()
    assert shipped and os.path.exists(shipped)

    real_exists = os.path.exists

    def fake_exists(p):
        ps = str(p).replace("\\", "/")
        if ps.endswith("OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv"):
            return False                      # simulate a bundle-only tree: no workspace copy anywhere
        if ps == shipped:
            return True
        return real_exists(p)

    monkeypatch.setattr(mod.os.path, "exists", fake_exists)
    resolved = mod._registry_default()
    assert resolved == shipped, (
        "no OFFICIAL_DATA registry is reachable, so the resolver must fall back to the shipped "
        f"package asset, got {resolved!r}")
    assert not resolved.endswith("OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv"), (
        "the resolver must not hand back the non-existent workspace path for a bundle-only tree")


def test_official_data_still_wins_when_present(monkeypatch, tmp_path):
    """The fallback must NOT override a real workspace registry — precedence is unchanged, so the
    canonical-content ruling is not pre-empted."""
    mod = _load(monkeypatch)
    ws = tmp_path / "OFFICIAL_DATA"
    ws.mkdir()
    reg = ws / "OUTGROUP_REGISTRY.tsv"
    reg.write_text("genus\tX\n", encoding="utf-8")
    monkeypatch.delenv("OUTGROUP_REGISTRY", raising=False)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    assert mod._registry_default() == str(reg), "an explicit workspace OFFICIAL_DATA copy must win"
