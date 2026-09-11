"""Behavior test for mamey_pipeline.py (BB10). Proves the orchestrator chains LOCATE ->
VALIDATE -> EXPLAIN -> REPORT against a *stub* engine + a fake sealed package, without the
real Sapote-Mamey tree. Self-contained: builds a tiny fake package dir and a fake mamey_run.py
that answers `validate` (prints MAMEY_COMPLETE) and `explain` (prints a summary). stdlib only."""
import subprocess, sys, pathlib

def _find_root(name):
    for p in pathlib.Path(__file__).resolve().parents:
        if (p / "tools" / name).exists() or (p / "Tools" / name).exists():
            return p
    raise RuntimeError(f"{name} not found above test")

# BB10 tool lives in its card's tools/ dir (fold target: Tools/)
CARD = pathlib.Path(__file__).resolve().parents[1]
TOOL = CARD / "tools" / "mamey_pipeline.py"

FAKE_ENGINE = '''import sys
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
if cmd == "validate":
    print('{"validator_status": "MAMEY_COMPLETE"}'); print("MAMEY_COMPLETE")
elif cmd == "explain":
    print("Mamey explain - STRAINX\\n  Status : MAMEY_COMPLETE\\n  Raw BGCs : 3")
sys.exit(0)
'''

def test_pipeline_orchestrates_stub_engine(tmp_path):
    # fake sealed engine tree with a stub mamey_run.py
    engine = tmp_path / "engine"; engine.mkdir()
    (engine / "mamey_run.py").write_text(FAKE_ENGINE)
    # fake sealed package with a couple of files to pin
    pkg = tmp_path / "runs" / "STRAINX" / "package"; pkg.mkdir(parents=True)
    (pkg / "STRAINX_1_intake.json").write_text('{"strain":"STRAINX"}')
    (pkg / "STRAINX_2_inventory.csv").write_text("bgc_id\\nBGC001\\n")
    out = tmp_path / "out"

    r = subprocess.run([sys.executable, str(TOOL),
                        "--strain", "STRAINX", "--package", str(pkg),
                        "--engine", str(engine), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    # manifest pinned both package files
    man = (out / "STRAINX_PACKAGE_MANIFEST.tsv").read_text().strip().splitlines()
    assert man[0].split("\t") == ["file", "sha256", "size"]
    assert len(man) == 3, man  # header + 2 files

    # validate + explain captured from the stub engine
    assert "MAMEY_COMPLETE" in (out / "STRAINX_validate.txt").read_text()
    assert "Raw BGCs" in (out / "STRAINX_explain.txt").read_text()

    # report written, links the stages, carries the claim-safety line
    rep = (out / "REPORT_STRAINX.md").read_text()
    assert "# Sapote-Mamey pipeline report — STRAINX" in rep
    assert "validate" in rep and "explain" in rep.lower()
    assert "judgment deferred" in rep
