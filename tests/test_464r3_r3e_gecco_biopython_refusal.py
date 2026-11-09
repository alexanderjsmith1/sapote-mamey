"""GECCO cross-check without Biopython in Mamey's own Python refuses with a typed reason.

Biopython is not a core dependency. The adapter used to import it at module load, which the
command's refusal handler never sees, so a core-only environment crashed with a traceback even
when the separate GECCO executable was present.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_BLOCK_BIO = textwrap.dedent("""
    import sys
    class _NoBio:
        def find_spec(self, name, path=None, target=None):
            if name == 'Bio' or name.startswith('Bio.'):
                raise ImportError('No module named ' + repr(name))
            return None
    sys.meta_path.insert(0, _NoBio())
    for key in [k for k in sys.modules if k == 'Bio' or k.startswith('Bio.')]:
        del sys.modules[key]
""")


def _run(body):
    code = _BLOCK_BIO + textwrap.dedent(body)
    return subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=120)


def test_module_imports_without_biopython():
    result = _run("""
        import mamey.gecco_crosscheck as g
        print('IMPORTED', hasattr(g, 'crosscheck'), hasattr(g, 'bound_support'))
    """)
    assert result.returncode == 0, result.stderr
    assert 'IMPORTED True True' in result.stdout


def test_crosscheck_refuses_before_running_gecco(tmp_path, monkeypatch):
    import shutil
    import mamey.gecco_crosscheck as g
    # A None entry makes `from Bio import SeqIO` raise ImportError; monkeypatch restores both.
    monkeypatch.setitem(sys.modules, 'Bio', None)
    calls = []
    monkeypatch.setattr(shutil, 'which', lambda *a, **k: calls.append(a))
    try:
        g.crosscheck(str(tmp_path), executable='gecco')
    except ValueError as exc:
        reason = str(exc).split(':')[0]
    else:
        reason = None
    assert reason == 'GECCO_BIOPYTHON_MISSING'
    assert calls == []


def test_cli_handler_reports_refusal_not_traceback(tmp_path):
    result = _run(f"""
        import argparse
        from mamey.cli import gecco_crosscheck_command
        args = argparse.Namespace(package={str(tmp_path)!r}, source_zip=None, out=None, threshold=0.8,
                                  jobs=1, genome_member=None, gap_genes=())
        print('RC', gecco_crosscheck_command(args))
    """)
    assert result.returncode == 0, result.stderr
    assert 'RC 2' in result.stdout
    assert 'GECCO_BIOPYTHON_MISSING' in result.stdout + result.stderr
    assert 'Traceback' not in result.stderr
