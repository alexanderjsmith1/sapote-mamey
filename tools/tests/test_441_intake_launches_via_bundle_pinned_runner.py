"""The harness must launch the engine so the bundle's mamey wins over any stray cwd mamey/.
`python -m mamey` puts the child's cwd first on sys.path; `python <bundle>/mamey_run.py` puts the
bundle dir first and never cwd. Black Cherry 2 / 88fdad06, v9.7.441. Verifies EB3DF1EF's finding."""
import os, re, subprocess, sys, textwrap
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / "intake_harness.py"

def test_source_launches_via_mamey_run_not_dash_m(tmp_path):
    src = HARNESS.read_text(encoding="utf-8")
    assert '"-m", "mamey"' not in src, "harness still uses `-m mamey`, which cwd can shadow"
    assert src.count('os.path.join(ROOT, "mamey_run.py"), "run"') == 2
    assert 'PYTHONDONTWRITEBYTECODE' in src

def _decoy(tmp_path):
    # a stray package on cwd that must NOT win
    (tmp_path/"decoy"/"realpkg").mkdir(parents=True)
    (tmp_path/"decoy"/"realpkg"/"__init__.py").write_text('__version__="0.0.0-DECOY"\n')
    # the real package + a mamey_run-style entry (script dir goes on path[0], not cwd)
    (tmp_path/"bundle"/"realpkg").mkdir(parents=True)
    (tmp_path/"bundle"/"realpkg"/"__init__.py").write_text('__version__="9.9.9-REAL"\n')
    (tmp_path/"bundle"/"run.py").write_text(textwrap.dedent('''
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import realpkg; sys.stdout.write(realpkg.__version__)
    '''))
    return tmp_path/"decoy", tmp_path/"bundle"

def test_dash_m_is_shadowed_by_cwd_but_script_is_not(tmp_path):
    decoy, bundle = _decoy(tmp_path)
    env = dict(os.environ, PYTHONPATH=str(bundle))
    # BUG shape: -m with cwd=decoy picks the decoy even though PYTHONPATH points at the bundle
    bug = subprocess.run([sys.executable, "-c", "import realpkg,sys;sys.stdout.write(realpkg.__version__)"],
                         cwd=str(decoy), env=env, capture_output=True, text=True)
    assert bug.stdout == "0.0.0-DECOY", bug.stdout
    # FIX shape: running the bundle script from cwd=decoy resolves the bundle package
    fix = subprocess.run([sys.executable, str(bundle/"run.py")], cwd=str(decoy),
                         env=dict(os.environ), capture_output=True, text=True)
    assert fix.stdout == "9.9.9-REAL", fix.stdout
