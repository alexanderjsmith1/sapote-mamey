"""The standalone rggmci package must give the engine's answer, and pass its own tests, when built from this bundle.

The package is built from the bundle's own source (packaging/rggmci/build_rggmci_package.py), so a change to
mamey/rggmci.py or to the region parsing reaches it on the next build (packaging/rggmci/). This test catches the other direction:
a change that the package build cannot carry, such as a new record field the scorer reads.

Input: tests/fixtures/rggmci_public_VWPH00000000.1_subset.zip, five regions cut from the public antiSMASH result
for NCBI WGS VWPH00000000.1 (Saccharopolyspora), with their ClusterBlast files. It gives 10 scored pairs, 4 HIGH,
and three locus-proxy ties that once depended on the Python hash seed.
"""
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "packaging" / "rggmci" / "build_rggmci_package.py"
FIXTURE = ROOT / "tests" / "fixtures" / "rggmci_public_VWPH00000000.1_subset.zip"
FIELDS = ("bgc_id", "contig", "region_number", "contig_length", "products", "edge_status")
PROBE = """
import json, sys
import rggmci
from rggmci.reader import read_regions
assert not any(m == "mamey" or m.startswith(("mamey.", "Bio")) for m in sys.modules), "package imported the engine"
b = read_regions(sys.argv[1])
print(json.dumps({"records": [[getattr(x, f) for f in %r] for x in b],
                  "result": rggmci.run_rggmci(sys.argv[1], b)}, sort_keys=True, default=str))
""" % (FIELDS,)


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    out = tmp_path_factory.mktemp("rggmci_build") / "pkg"
    r = subprocess.run([sys.executable, str(BUILD), "--bundle", str(ROOT), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return out


# Pinned to the run without a MIBiG protein database (v9.7.445): reference-guided completion then records tier
# NO_MIBIG_PROTEINS on both sides whatever aligner is installed, so the test runner's environment cannot change what is
# compared. The completion code itself is compared byte for byte by the package build (VERBATIM).
_PINNED_OFF = ("RGGMCI_MIBIG_DB", "RGGMCI_DIAMOND", "RGGMCI_PFAM_HMM")


def _clean_env(src: Path) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONSTARTUP", *_PINNED_OFF)}
    env["PYTHONPATH"] = str(src)          # the package only: the bundle root is not importable
    return env


def test_package_matches_the_engine_on_a_public_fixture(package, tmp_path, monkeypatch):
    for k in _PINNED_OFF:
        monkeypatch.delenv(k, raising=False)
    from mamey import parsers, rggmci
    bgcs = parsers.parse_bgcs_from_zip(str(FIXTURE), json_mode="off")
    engine = json.dumps({"records": [[getattr(x, f) for f in FIELDS] for x in bgcs],
                         "result": rggmci.run_rggmci(str(FIXTURE), bgcs)}, sort_keys=True, default=str)
    r = subprocess.run([sys.executable, "-c", PROBE, str(FIXTURE)], cwd=tmp_path, env=_clean_env(package / "src"),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    got = r.stdout.strip()
    assert json.loads(got)["result"]["ranked_pairs"], "the fixture must score pairs, or this compares nothing"
    assert json.loads(got)["result"]["reference_completion"]["completion_tier"] == "NO_MIBIG_PROTEINS"
    if got != engine:   # name the first difference; pytest's own diff of two long JSON strings is slow and unreadable
        i = next(k for k, (x, y) in enumerate(zip(got, engine)) if x != y) if len(got) == len(engine) else \
            next((k for k, (x, y) in enumerate(zip(got, engine)) if x != y), min(len(got), len(engine)))
        pytest.fail(f"package differs from engine at char {i}:\n package: …{got[max(0, i - 150):i + 150]}…\n"
                    f" engine:  …{engine[max(0, i - 150):i + 150]}…")


def test_package_own_tests_pass_in_a_clean_interpreter(package, tmp_path):
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=",
                        str(package / "tests")], cwd=tmp_path, env=_clean_env(package / "src"),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]


def test_package_cli_public_pair_outputs_match_engine_and_current_input(package, tmp_path):
    """Actual built CLI, positive public fixture, and shared-formatter table bytes."""
    from mamey import parsers, ref_completion, rggmci
    bgcs = parsers.parse_bgcs_from_zip(str(FIXTURE), json_mode="off")
    expected = rggmci.run_archive(str(FIXTURE), reference_completion="off", threads=1)
    out = tmp_path / "new/results"
    r = subprocess.run([sys.executable, "-m", "rggmci", str(FIXTURE), "--out-dir", str(out),
                        "--reference-completion", "off", "--threads", "1"],
                       cwd=tmp_path, env=_clean_env(package / "src"), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    result = json.loads((out / f"{FIXTURE.stem}.json").read_text())
    assert result["input"]["antismash_zip_sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert result["ranked_pairs"], "positive output-contract test must exercise scored pairs"
    assert [{k: p[k] for k in e} for p, e in zip(result["ranked_pairs"], expected["ranked_pairs"], strict=True)] == \
        expected["ranked_pairs"]
    with (out / f"{FIXTURE.stem}_pairs.tsv").open(newline="") as fh:
        table = csv.DictReader(fh, delimiter="\t")
        assert set(table.fieldnames) == {key for pair in result["ranked_pairs"] for key in pair}
        rows = list(table)
    expected_artifacts = rggmci.canonical_artifacts(expected, name=FIXTURE.stem)
    for name, payload in expected_artifacts.items():
        if name.endswith(".tsv"):
            assert (out / name).read_bytes() == payload
    assert len(rows) == len(result["ranked_pairs"])
    assert [(row["pair"], float(row["rggmci_score"]), row["rggmci_confidence"]) for row in rows] == \
        [(row["pair"], row["rggmci_score"], row["rggmci_confidence"]) for row in expected["ranked_pairs"]]
    with (out / "SUMMARY.tsv").open(newline="") as fh:
        summary = list(csv.DictReader(fh, delimiter="\t"))
    assert len(summary) == 1 and int(summary[0]["scored_pairs"]) == len(rows)
    direct = tmp_path / "shared_formatter"
    direct.mkdir()
    for path in ref_completion.write_tables(result["reference_completion"], direct, f"{FIXTURE.stem}_"):
        assert path.read_bytes() == (out / path.name).read_bytes()


def test_repository_docs_name_files_that_exist(package):
    """CONTRIBUTING and the README templates name files of the standalone repository; each must exist there
    (the built package, a file make_repo_candidate.py writes) or in packaging/rggmci/."""
    import re
    here = ROOT / "packaging" / "rggmci"
    known = {p.name for p in package.rglob("*") if p.is_file()} | {p.name for p in here.rglob("*") if p.is_file()}
    writer = (here / "make_repo_candidate.py").read_text(encoding="utf-8")
    missing = []
    for doc in list((here / "repo_extras").rglob("*.md")) + list((here / "templates").rglob("*.md")):
        for ref in re.findall(r"`([A-Za-z0-9_\-/\.]+\.(?:py|sh))`", doc.read_text(encoding="utf-8")):
            name = Path(ref).name
            # Contributor docs also identify upstream engine owners, outside the standalone tree.
            if ref.startswith("mamey/") and (ROOT / ref).is_file():
                continue
            if name not in known and f'"{name}"' not in writer:
                missing.append(f"{doc.relative_to(here)}: {ref}")
    assert not missing, missing


@pytest.mark.parametrize("kind", ["size", "ratio"])
@pytest.mark.parametrize("mixed", [False, True])
def test_built_package_shared_text_guard_parity(package, tmp_path, monkeypatch, kind, mixed):
    import zipfile
    from mamey import parsers, rggmci
    member = "clusterblast/SYNTHETIC_REFUSED.txt"
    archive = tmp_path / "SYNTHETIC_GUARD.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if mixed: zf.writestr("clusterblast/SYNTHETIC_ADMITTED.txt", "synthetic admitted marker")
        zf.writestr(member, "X" * 4096)
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "256" if kind == "size" else "8192")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "10000" if kind == "size" else "2")
    with pytest.raises(parsers.GbkSizeGuardRefusal) as error:
        rggmci.parse_clusterblast_reference_map(archive, [])
    expected = {"type": type(error.value).__name__, "member": error.value.member, "reason": error.value.reason}
    core = (package / "src/rggmci/core.py").read_text()
    assert "from ._parsers import GbkSizeGuardRefusal, _safe_read_text" in core
    assert "from .parsers import GbkSizeGuardRefusal, _safe_read_text" not in core
    probe = """
import json, sys, zipfile
import rggmci.core as core
from rggmci._parsers import GbkSizeGuardRefusal
assert not any(m == 'mamey' or m.startswith('mamey.') for m in sys.modules)
def forbidden(*a, **k):
    raise AssertionError('unbounded whole read forbidden')
zipfile.ZipFile.read = forbidden
try:
    core.parse_clusterblast_reference_map(sys.argv[1], [])
except GbkSizeGuardRefusal as exc:
    print(json.dumps({'type':type(exc).__name__, 'member':exc.member, 'reason':exc.reason}))
else:
    raise AssertionError('resource refusal became a successful/null map')
"""
    result = subprocess.run([sys.executable, "-c", probe, str(archive)], cwd=tmp_path,
                            env=_clean_env(package / "src"), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == expected
