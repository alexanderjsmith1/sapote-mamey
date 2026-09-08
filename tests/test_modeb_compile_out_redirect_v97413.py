"""v9.7.413 (BC2) — `modeb-compile` must be able to write somewhere other than the two canonical
targets.

`deliverable_tools/build_modeb_compilation.py` writes, per strain and unconditionally, to BOTH
`<MAMEY_DATA_ROOT>/strain_data/<STRAIN>/` and the dated
`<MAMEY_DATA_ROOT>/strain_data/modeb_compilation_2026-08-05/` — and `strain_data` is a symlink to
the canonical home (`AS Strain Master`). It accepted no output flag at all, so there was no way to
run it without overwriting real deliverables in place.

This is the same defect class as the `surface-leads --out` fix that landed in `.412`, but with a
larger blast radius on three counts, all observed:
  * two canonical targets per strain rather than one;
  * `build()` reads live per-strain state, so a re-run REPLACES rather than reproduces (the
    surface-leads accident cost 3 bytes precisely because that tool is deterministic — this one
    is not);
  * the canonical dated folder also holds `.pdf` files this tool does not regenerate, so an
    unguarded run leaves a stale PDF beside a rewritten MD/DOCX with nothing recording it.

Scope: output-location only. The compiled content is unchanged; the default targets are unchanged.
"""
import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO_ROOT, "deliverable_tools", "build_modeb_compilation.py")


def _load_tool(data_root):
    # Callers bind the environment through pytest's restoring monkeypatch fixture.
    spec = importlib.util.spec_from_file_location("build_modeb_compilation_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_modeb_compile_out_does_not_touch_either_canonical_target(tmp_path, monkeypatch):
    """--out collapses both canonical writes into the given directory and touches neither."""
    data_root = tmp_path / "workspace"
    (data_root / "strain_data").mkdir(parents=True)
    alt = tmp_path / "redirected"

    monkeypatch.setenv("MAMEY_DATA_ROOT", str(data_root))
    mod = _load_tool(data_root)
    # keep the test about output plumbing, not about compilation content
    monkeypatch.setattr(mod, "build", lambda s: f"# {s} synthetic compilation\n")
    monkeypatch.setattr(sys, "argv",
                        ["build_modeb_compilation", "--strain", "AS-000",
                         "--no-docx", "--out", str(alt)])
    rc = mod.main()

    assert rc == 0
    assert (alt / "AS-000_ModeB_compilation.md").is_file(), "--out did not redirect the compilation"
    # neither canonical target may be created
    assert not (data_root / "strain_data" / "AS-000").exists(), \
        "--out given, yet the per-strain canonical folder was written"
    assert not (data_root / "strain_data" / "modeb_compilation_2026-08-05").exists(), \
        "--out given, yet the canonical dated folder was written"


def test_modeb_compile_default_targets_unchanged(tmp_path, monkeypatch):
    """Control: with no --out, BOTH canonical targets are still written (default preserved)."""
    data_root = tmp_path / "workspace"
    (data_root / "strain_data").mkdir(parents=True)

    monkeypatch.setenv("MAMEY_DATA_ROOT", str(data_root))
    mod = _load_tool(data_root)
    monkeypatch.setattr(mod, "build", lambda s: f"# {s} synthetic compilation\n")
    monkeypatch.setattr(sys, "argv",
                        ["build_modeb_compilation", "--strain", "AS-000", "--no-docx"])
    rc = mod.main()

    assert rc == 0
    assert (data_root / "strain_data" / "AS-000" / "AS-000_ModeB_compilation.md").is_file()
    assert (data_root / "strain_data" / "modeb_compilation_2026-08-05"
            / "AS-000_ModeB_compilation.md").is_file()


def test_cli_modeb_compile_accepts_and_forwards_out():
    """`mamey modeb-compile --out DIR` parses, and the dispatcher forwards it to the tool."""
    from mamey import cli
    parser = cli.build_parser()
    ns = parser.parse_args(["modeb-compile", "--strain", "AS-000", "--out", "/tmp/somewhere"])
    assert getattr(ns, "out", None) == "/tmp/somewhere", "modeb-compile does not accept --out"
    assert ns.func.__name__ == "_flagged_lead_command"

    import inspect
    src = inspect.getsource(cli._flagged_lead_command)
    modeb_branch = src.split('elif args.command == "modeb-compile":')[-1]
    assert '"--out"' in modeb_branch, "dispatcher does not forward --out for modeb-compile"
