"""pins the sapote_version_guard.py hook's core behavior: it must resolve the NEWEST
Sapote-Mamey bundle and read its engine __version__.

Why: the version-guard hook is the safety net that stops a session from authoring 'corrections' to
stale-engine cards (the mode_b_v9.7.339 incident). If the resolver silently breaks — e.g. a directory
rename changes the glob, or a tie between a -CODE- tree and a doc bundle flips — the guard would inject a
WRONG 'current version' and the net fails open. This test pins: highest version wins, a -CODE- tree beats a
doc bundle on a tie, __version__ is read, and main() emits a well-formed additionalContext block naming the
newest bundle. The hook ships in the bundle's portable hooks/ (this imports that copy).
"""
from __future__ import annotations
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "sapote_version_guard.py"


def _load():
    spec = importlib.util.spec_from_file_location("sapote_version_guard", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_bundle(base: pathlib.Path, name: str, version: str | None):
    d = base / name
    (d / "mamey").mkdir(parents=True)
    if version is not None:
        (d / "mamey" / "__init__.py").write_text(f'__version__ = "{version}"\n')
    return d


def test_hook_ships_in_bundle():
    assert HOOK.exists(), "sapote_version_guard.py must ship in the bundle's portable hooks/"


def test_newest_bundle_picks_highest_version(tmp_path):
    mod = _load()
    _make_bundle(tmp_path, "sapote-mamey-v9.7.100-CODE-old", "1.9.100")
    _make_bundle(tmp_path, "sapote-mamey-v9.7.354-CODE-new", "1.9.119")
    _make_bundle(tmp_path, "Sapote Mamey v9.7.200", None)  # a doc bundle, lower version
    mod.ROOT = str(tmp_path)
    newest = mod._newest_bundle()
    assert pathlib.Path(newest).name == "sapote-mamey-v9.7.354-CODE-new"


def test_code_tree_preferred_on_version_tie(tmp_path):
    mod = _load()
    _make_bundle(tmp_path, "Sapote Mamey v9.7.354", None)          # doc bundle, same version
    _make_bundle(tmp_path, "sapote-mamey-v9.7.354-CODE-x", "1.9.119")  # code tree, same version
    mod.ROOT = str(tmp_path)
    newest = mod._newest_bundle()
    assert "-CODE-" in pathlib.Path(newest).name, "a -CODE- tree must win a version tie over a doc bundle"


def test_engine_version_read(tmp_path):
    mod = _load()
    b = _make_bundle(tmp_path, "sapote-mamey-v9.7.354-CODE-x", "1.9.119")
    assert mod._engine_version(str(b)) == "1.9.119"


def test_main_emits_additionalContext_naming_newest(tmp_path, capsys):
    mod = _load()
    _make_bundle(tmp_path, "sapote-mamey-v9.7.354-CODE-new", "1.9.119")
    mod.ROOT = str(tmp_path)
    rc = mod.main()
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "UserPromptSubmit"
    ctx = hso["additionalContext"]
    assert "sapote-mamey-v9.7.354-CODE-new" in ctx
    assert "1.9.119" in ctx
    assert "VERSION GUARD" in ctx


def test_no_bundle_is_silent(tmp_path, capsys):
    mod = _load()
    mod.ROOT = str(tmp_path)  # empty dir, no bundles
    rc = mod.main()
    assert rc == 0
    assert capsys.readouterr().out == "", "with no bundle the guard must stay silent, never emit junk"
