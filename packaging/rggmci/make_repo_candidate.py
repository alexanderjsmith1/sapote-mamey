#!/usr/bin/env python3
"""Generate a ready-to-publish `rggmci` repository from a Sapote-Mamey bundle.

The repository is a build target, not a second source. Everything comes from the bundle:
  1. build_rggmci_package.py writes the package (scorer copied, helpers lifted, templates added);
  2. repo_extras/ adds the repository-only files (CI, citation, changelog, contributing, .gitignore);
  3. examples/ gets the public test fixture from the bundle and the ENGINE's own result for it;
  4. tests/test_example_matches_engine.py makes the package reproduce that result exactly, so the standalone
     repository catches drift even without the bundle.

Publishing (creating the GitHub repository, pushing, uploading to PyPI) is the owner's step, not this script's.

Usage:
  python make_repo_candidate.py --bundle <sapote-mamey root> --out <empty or new dir>
"""
from __future__ import annotations

import argparse, json, os, pathlib, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
FIXTURE = "rggmci_public_VWPH00000000.1_subset.zip"
EXAMPLE = "VWPH00000000.1_subset.antismash.zip"
FIELDS = ("bgc_id", "contig", "region_number", "contig_length", "products", "edge_status")

ENGINE_PROBE = """
import json, sys
from mamey import parsers, rggmci
z = sys.argv[1]
b = parsers.parse_bgcs_from_zip(z, json_mode="off")
print(json.dumps({"records": [[getattr(x, f) for f in %r] for x in b], "result": rggmci.run_rggmci(z, b)},
                 sort_keys=True, default=str))
""" % (FIELDS,)

SNAPSHOT_TEST = '''"""The package must reproduce the Sapote-Mamey engine's own result on the public example, byte for byte.

`examples/%(expected)s` was written by the engine (see its "engine" key) when this repository was generated.
If this test fails, the package and the engine disagree: regenerate the repository from Sapote-Mamey rather
than editing either side here.
"""
import json
from pathlib import Path

import rggmci
from rggmci.reader import read_regions

ROOT = Path(__file__).resolve().parents[1]
FIELDS = %(fields)r


def test_example_matches_engine():
    z = ROOT / "examples" / "%(example)s"
    expected = json.loads((ROOT / "examples" / "%(expected)s").read_text())
    b = read_regions(z)
    got = json.loads(json.dumps({"records": [[getattr(x, f) for f in FIELDS] for x in b],
                                 "result": rggmci.run_rggmci(z, b)}, sort_keys=True, default=str))
    assert got["result"]["ranked_pairs"], "the example must score pairs, or this compares nothing"
    assert got["records"] == expected["records"]
    assert got["result"] == expected["result"]
'''


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bundle", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--python", default=sys.executable, help="interpreter with the bundle's dependencies (for the engine run)")
    a = ap.parse_args(argv)
    if a.out.exists() and any(a.out.iterdir()):
        if not (a.out / ".git").is_dir():
            print(f"refusing to write into a non-empty directory that is not a git repository: {a.out}", file=sys.stderr)
            return 2
        # Sync mode: regenerate into a temporary sibling, then replace everything except .git, so the repository's
        # history shows exactly what the regeneration changed.
        tmp = a.out.parent / (a.out.name + ".regen_tmp")
        if tmp.exists():
            print(f"refusing: {tmp} exists (an earlier regeneration was interrupted); inspect and remove it", file=sys.stderr)
            return 2
        rc = main([*(argv if argv is not None else sys.argv[1:]), "--out", str(tmp)])
        if rc:
            shutil.rmtree(tmp, ignore_errors=True)
            return rc
        for child in list(a.out.iterdir()):
            if child.name != ".git":
                shutil.rmtree(child) if child.is_dir() else child.unlink()
        for child in list(tmp.iterdir()):
            shutil.move(str(child), str(a.out / child.name))
        tmp.rmdir()
        print(f"synced into git repository {a.out} (only .git kept; review with git status / git diff)")
        return 0
    build = HERE / "build_rggmci_package.py"
    r = subprocess.run([sys.executable, str(build), "--bundle", str(a.bundle), "--out", str(a.out)], text=True)
    if r.returncode:
        return r.returncode
    version = json.loads((a.out / "src" / "rggmci" / "PROVENANCE.json").read_text())["package_version"]
    extras = HERE / "repo_extras"
    for p in extras.rglob("*"):
        if p.is_file():
            dst = a.out / p.relative_to(extras)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if p.name in ("CITATION.cff", "CHANGELOG.md"):   # one version, from pyproject.toml
                dst.write_text(p.read_text().replace("{version}", version))
            else:
                shutil.copy2(p, dst)
    fixture = a.bundle / "tests" / "fixtures" / FIXTURE
    if not fixture.is_file():
        fixture = HERE / "bundle_integration" / FIXTURE
    ex = a.out / "examples"
    ex.mkdir(exist_ok=True)
    shutil.copy2(fixture, ex / EXAMPLE)
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONSTARTUP")}
    env["PYTHONPATH"] = str(a.bundle)
    env["PYTHONHASHSEED"] = "0"
    probe = subprocess.run([a.python, "-c", ENGINE_PROBE, str(ex / EXAMPLE)], env=env, capture_output=True, text=True)
    if probe.returncode:
        print(probe.stderr[-2000:], file=sys.stderr)
        return 1
    engine = json.loads(probe.stdout)
    prov = json.loads((a.out / "src" / "rggmci" / "PROVENANCE.json").read_text())
    engine["engine"] = {"sapote_mamey": prov.get("built_from_bundle"), "engine": prov.get("engine"), "build": prov.get("build")}
    expected = EXAMPLE.replace(".antismash.zip", "_expected_engine.json")
    (ex / expected).write_text(json.dumps(engine, indent=1, sort_keys=True) + "\n")
    (ex / "README.md").write_text(
        f"# Example\n\n`{EXAMPLE}` holds five regions, with their ClusterBlast files, cut from the public antiSMASH result "
        f"for NCBI WGS VWPH00000000.1 (*Saccharopolyspora*). It gives {engine['result']['pairs_total']} scored pairs, "
        f"{engine['result']['high_pairs']} of them HIGH.\n\n"
        f"```bash\nrggmci examples/{EXAMPLE} --out result.json --pairs pairs.tsv\n```\n\n"
        f"`{expected}` is the Sapote-Mamey engine's own result on this file; `tests/test_example_matches_engine.py` "
        "checks that the package reproduces it exactly.\n")
    (a.out / "tests" / "test_example_matches_engine.py").write_text(
        SNAPSHOT_TEST % {"expected": expected, "example": EXAMPLE, "fields": FIELDS})
    print(f"repository candidate -> {a.out} (built from Sapote-Mamey {prov.get('built_from_bundle')}, engine {prov.get('engine')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
