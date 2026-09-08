#!/usr/bin/env python3
"""test_bigscape_integration.py — stdlib-only tests for the `mamey bigscape` runner.

No real BiG-SCAPE, no HMMER, no network. Covers the four things that make the integration
correct-by-construction:
  (a) region-GBK discovery + staging into a no-space work dir (spaces gotcha),
  (b) the fasttree-symlink shim (casing gotcha): a FastTree-only bin becomes `fasttree`-resolvable,
  (c) the assembled command carries the exact proven flags,
  (d) a --dry-run path prints the command and does NOT execute BiG-SCAPE.

Runs standalone: `python3 tests/test_bigscape_integration.py` (also collectible by pytest).
"""
import importlib.util
import os
import shutil
import sys
import tempfile

# import the runner by file path (it lives in ../deliverable_tools/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_DT = os.path.join(os.path.dirname(_HERE), "deliverable_tools")
_spec = importlib.util.spec_from_file_location(
    "bigscape_run", os.path.join(_DT, "bigscape_run.py"))
bsr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsr)


def _write(path, text=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text or "LOCUS x\n//\n")


# --- (a) discovery + no-space staging ------------------------------------------------
def test_discover_inputs_priority():
    mode, items = bsr.discover_inputs(input_gbk_dir="/x/gbks")
    assert mode == "gbk_dir" and items == ["/x/gbks"]
    mode, items = bsr.discover_inputs(package="/x/pkg")
    assert mode == "packages" and items == ["/x/pkg"]


def test_stage_gbks_into_no_space_dir():
    src = tempfile.mkdtemp(prefix="bs src with spaces ")  # deliberately spaced source
    try:
        _write(os.path.join(src, "AS-705.region001.gbk"))
        _write(os.path.join(src, "AS-705.region002.gbk"))
        _write(os.path.join(src, "._AS-705.region003.gbk"))  # AppleDouble -> skipped
        _write(os.path.join(src, "AS-705.txt"))              # non-GBK -> skipped
        out = os.path.join(tempfile.mkdtemp(prefix="bs_work_"), "input")
        n = bsr.stage_gbks("gbk_dir", [src], out)
        staged = sorted(os.listdir(out))
        assert n == 2, f"expected 2 region GBKs, got {n}: {staged}"
        assert all("._" not in f for f in staged)
        assert " " not in os.path.abspath(out), "staging dir must be space-free"
    finally:
        shutil.rmtree(src, ignore_errors=True)


def test_stage_packages_reuses_prep():
    # proves the tools/bigscape_prep.py reuse path works on a bare package dir
    pkg = tempfile.mkdtemp(prefix="AS-999_pkg_")
    try:
        _write(os.path.join(pkg, "sub", "NODE_1.region001.gbk"))
        out = os.path.join(tempfile.mkdtemp(prefix="bs_work_"), "input")
        n = bsr.stage_gbks("packages", [pkg], out)
        assert n == 1
        # strain-prefixed so cross-strain NODE_* names never collide
        assert any("region001" in f for f in os.listdir(out))
    finally:
        shutil.rmtree(pkg, ignore_errors=True)


# --- (b) fasttree shim (casing gotcha) -----------------------------------------------
def test_ensure_fasttree_symlinks_capitalized(monkeypatch):
    envbin = tempfile.mkdtemp(prefix="bs_env_bin_")
    shim = tempfile.mkdtemp(prefix="bs_shim_")
    try:
        # mock a FastTree-only env bin (no lowercase fasttree), plus the bigscape binary
        fake_bigscape = os.path.join(envbin, "bigscape")
        _write(fake_bigscape, "#!/bin/sh\n")
        os.chmod(fake_bigscape, 0o755)
        fake_ft = os.path.join(envbin, "FastTree")
        _write(fake_ft, "#!/bin/sh\n")
        os.chmod(fake_ft, 0o755)

        used = bsr.ensure_fasttree(fake_bigscape, shim)
        assert used == shim
        link = os.path.join(shim, "fasttree")
        assert os.path.lexists(link), "fasttree shim was not created"
        # resolves back to the capitalized binary
        assert os.path.realpath(link) == os.path.realpath(fake_ft)
        # and would be resolvable once shim is on PATH
        # monkeypatch.setenv, NOT a raw os.environ assignment: pytest restores it at teardown.
        # A raw assignment leaked here — the `finally` below deletes `shim`, so every later test in
        # the process inherited a PATH entry pointing at a directory that no longer exists, and any
        # subprocess inheriting this environment searched it. Harmless in isolation, but it made the
        # suite order-dependent through shared process state. Guarded by
        # tests/test_suite_collection_guard_v97407.py.
        monkeypatch.setenv("PATH", shim + os.pathsep + os.environ.get("PATH", ""))
        assert shutil.which("fasttree") == link or os.path.samefile(shutil.which("fasttree"), link)
    finally:
        shutil.rmtree(envbin, ignore_errors=True)
        shutil.rmtree(shim, ignore_errors=True)


# --- (c) exact proven command flags --------------------------------------------------
def test_build_command_has_proven_flags():
    cmd = bsr.build_command("bigscape", "/w/input", "/deliv/out", "/p/Pfam-A.hmm", 4)
    s = " ".join(cmd)
    assert cmd[0] == "bigscape" and cmd[1] == "cluster"
    for token in ("-i /w/input", "-o /deliv/out", "-p /p/Pfam-A.hmm",
                  "--record-type region", "--classify category",
                  "--gcf-cutoffs 0.3,0.5,0.7", "--include-singletons", "-c 4"):
        assert token in s, f"missing proven flag: {token}\nfull: {s}"


def test_stage_no_space_symlinks_spaced_pfam():
    spaced = tempfile.mkdtemp(prefix="Pfam With Spaces ")
    try:
        pfam = os.path.join(spaced, "Pfam-A.hmm")
        _write(pfam, "HMMER3\n")
        work = tempfile.mkdtemp(prefix="bs_work_")
        used = bsr._stage_no_space(pfam, work)
        assert " " not in os.path.abspath(used), f"spaced pfam not de-spaced: {used}"
        assert os.path.realpath(used) == os.path.realpath(pfam)
    finally:
        shutil.rmtree(spaced, ignore_errors=True)


# --- (d) dry-run path does not execute -----------------------------------------------
def test_dry_run_does_not_execute(monkeypatch=None):
    src = tempfile.mkdtemp(prefix="bs_gbks_")
    _write(os.path.join(src, "AS-1.region001.gbk"))
    called = {"run": False}

    def _boom(*a, **k):
        called["run"] = True
        raise AssertionError("subprocess.run must NOT be called on --dry-run")

    orig = bsr.subprocess.run
    bsr.subprocess.run = _boom
    try:
        out = tempfile.mkdtemp(prefix="bs out spaces ")  # spaced OUTPUT dir is allowed
        res = bsr.run_pipeline(input_gbk_dir=src, out=out, bigscape_bin="bigscape",
                               pfam="/p/Pfam-A.hmm", cpus=4, dry_run=True, run_widgets=False)
        assert res["dry_run"] is True
        assert called["run"] is False
        assert res["command"][1] == "cluster"
        assert res["n_gbks"] == 1
    finally:
        bsr.subprocess.run = orig
        shutil.rmtree(src, ignore_errors=True)


def _run_all():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
