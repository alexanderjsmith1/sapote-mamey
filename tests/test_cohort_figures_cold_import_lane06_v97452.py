"""Cold-import state and explicit dependency contracts; no figure rendering."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp_path, code):
    cwd = tmp_path / "foreign"
    cwd.mkdir()
    cache = tmp_path / "mpl-cache"
    cache.mkdir()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MPLCONFIGDIR"] = str(cache)
    prefix = "import sys\nsys.path.insert(0, sys.argv[1])\n"
    result = subprocess.run([sys.executable, "-I", "-B", "-c", prefix + code, str(ROOT)],
                            cwd=cwd, env=env, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not list(cwd.iterdir())


def _needs(*names):
    for name in names:
        if importlib.util.find_spec(name) is None:
            pytest.skip(f"explicit-call control needs optional dependency {name}")


def test_cold_import_preserves_process_logging_and_source(tmp_path):
    _run(tmp_path, r'''
import csv, hashlib, logging, os, threading
from pathlib import Path
root = Path(sys.argv[1])
source = root / 'mamey/cohort_figures.py'
digest = hashlib.sha256(source.read_bytes()).hexdigest()
def logging_state():
    values = {'<root>': logging.getLogger()}
    values.update(logging.Logger.manager.loggerDict)
    return {name: (type(value).__name__, getattr(value, 'level', None),
                   getattr(value, 'disabled', None), getattr(value, 'propagate', None),
                   tuple((id(h), h.level, id(h.formatter)) for h in getattr(value, 'handlers', ())))
            for name, value in values.items()}
before = (logging_state(), os.getcwd(), dict(os.environ), list(sys.path),
          list(sys.argv), csv.field_size_limit(), threading.active_count())
assert not any(name in sys.modules for name in ('numpy', 'scipy', 'matplotlib', 'mamey'))
operations = []
def audit(event, args):
    if event == 'open':
        mode, flags = args[1:3]
        if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)):
            operations.append((event, repr(args)))
    elif event in {'os.mkdir', 'os.remove', 'os.rename', 'os.rmdir', 'os.chdir',
                   'os.putenv', 'os.unsetenv', 'subprocess.Popen', 'os.system',
                   'os.posix_spawn', 'os.fork', 'os.exec', 'socket.connect', 'socket.bind'}:
        operations.append((event, repr(args)))
sys.addaudithook(audit)
import mamey.cohort_figures as cf
after = (logging_state(), os.getcwd(), dict(os.environ), list(sys.path),
         list(sys.argv), csv.field_size_limit(), threading.active_count())
assert after == before, (before, after)
assert not operations, operations
assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
assert not any(name in sys.modules for name in (
    'numpy', 'scipy', 'matplotlib', 'charset_normalizer', 'mamey.figure_save'))
assert cf.build_cohort_figures([], 'unused') == {'status': 'SKIPPED_SINGLE_STRAIN', 'figure_count': 0}
assert cf._num('2.5') == 2.5
assert cf._matrix_fig_size(2, 3, 0.4, 2.0, 0.3, 1.0) == (8.0, 3.2)
''')


def test_explicit_math_style_and_scipy_calls_resolve_real_dependencies(tmp_path):
    _needs("numpy", "matplotlib", "scipy")
    _run(tmp_path, r'''
import mamey.cohort_figures as cf
assert not any(n in sys.modules for n in ('numpy', 'matplotlib', 'scipy'))
record = {'architecture': "{'domain_counts': {'PKS_KS': 1}}"}
profiles = cf._strain_profiles({'control': {'gene': {'domain_arch': [record]}}}, ['control'])
import numpy as np
np.testing.assert_allclose(profiles['control'][0], np.log(2.0))
assert 'matplotlib' not in sys.modules and 'scipy' not in sys.modules
@cf._with_cohort_style
def control():
    assert cf.matplotlib.rcParams['font.size'] == cf._COHORT_STYLE['font.size']
    assert cf.matplotlib.get_backend().lower() == 'agg'
    return cf.matplotlib, cf.plt, cf.mp, cf.LogNorm, cf.save_figure
mpl, plt, mp, norm, saver = control()
assert cf._HAVE_MPL is True and type(cf._HAVE_MPL) is bool
assert plt.__name__ == 'matplotlib.pyplot' and mp.__name__ == 'matplotlib.patches'
assert norm.__module__ == 'matplotlib.colors' and saver.__module__ == 'mamey.figure_save'
assert mpl.rcParams['font.size'] == mpl.rcParamsDefault['font.size']
assert 'scipy' not in sys.modules
assert cf._HAS_SCIPY is True and type(cf._HAS_SCIPY) is bool
tree = cf.linkage([[0.0], [2.0]], method='single')
assert cf.leaves_list(tree).tolist() == [0, 1]
assert not plt.get_fignums()
''')


def test_missing_matplotlib_keeps_boolean_flag_and_install_diagnostic(tmp_path):
    _needs("numpy")
    _run(tmp_path, r'''
import importlib.abc
class Missing(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'matplotlib' or fullname.startswith('matplotlib.'):
            raise ModuleNotFoundError('controlled missing matplotlib', name='matplotlib')
sys.meta_path.insert(0, Missing())
import mamey.cohort_figures as cf
assert cf._HAVE_MPL is False and type(cf._HAVE_MPL) is bool
assert cf._MPL_ERR == 'controlled missing matplotlib'
try:
    cf.generate(out='must-not-exist')
except RuntimeError as exc:
    assert 'Figure generation needs matplotlib' in str(exc)
    assert "pip install -e '.[figures]'" in str(exc)
    assert 'controlled missing matplotlib' in str(exc)
else:
    raise AssertionError('missing matplotlib must retain the installation diagnostic')
''')


@pytest.mark.parametrize("failure", ["ModuleNotFoundError", "RuntimeError"])
def test_optional_scipy_flag_retains_unavailable_and_broken_import_fallback(tmp_path, failure):
    _run(tmp_path, '''
import importlib.abc
class Missing(importlib.abc.MetaPathFinder):
    calls = 0
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'scipy' or fullname.startswith('scipy.'):
            Missing.calls += 1
            raise ''' + failure + '''('controlled scipy failure')
sys.meta_path.insert(0, Missing())
import mamey.cohort_figures as cf
assert cf._HAS_SCIPY is False and type(cf._HAS_SCIPY) is bool
try:
    cf.linkage
except AttributeError:
    pass
else:
    raise AssertionError('unavailable optional callable must stay unavailable')
assert Missing.calls == 1, 'failed optional dependency should not be retried on attribute access'
''')


def test_required_numpy_failure_surfaces_on_explicit_math_call(tmp_path):
    _run(tmp_path, r'''
import importlib.abc
class Missing(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'numpy' or fullname.startswith('numpy.'):
            raise ModuleNotFoundError('controlled missing numpy', name='numpy')
sys.meta_path.insert(0, Missing())
import mamey.cohort_figures as cf
try:
    cf._strain_profiles({}, [])
except ModuleNotFoundError as exc:
    assert exc.name == 'numpy'
else:
    raise AssertionError('required numpy failure was hidden')
''')


def test_module_cli_help_still_exits_before_loading_plot_dependencies(tmp_path):
    _run(tmp_path, r'''
import contextlib, io, runpy
sys.argv = ['mamey.cohort_figures', '--help']
output = io.StringIO()
with contextlib.redirect_stdout(output):
    try:
        runpy.run_module('mamey.cohort_figures', run_name='__main__')
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError('--help must exit')
assert '--runs-dir' in output.getvalue() and '--public-only' in output.getvalue()
assert not any(n in sys.modules for n in ('numpy', 'scipy', 'matplotlib'))
''')


def test_first_save_preserves_supplied_callable_without_preloading_plot_aliases(tmp_path):
    _needs("numpy", "matplotlib")
    _run(tmp_path, r'''
import warnings
from pathlib import Path
import mamey.cohort_figures as cf
assert '_HAVE_MPL' not in vars(cf)
assert not any(name in sys.modules for name in ('numpy', 'matplotlib', 'scipy'))
# This lookup followed by assignment is the first-use seam of MonkeyPatch.setattr.
original_saver = cf.save_figure
assert callable(original_saver)
assert '_HAVE_MPL' not in vars(cf)
assert not any(name in sys.modules for name in ('numpy', 'matplotlib', 'scipy'))
calls = []
def supplied_saver(*args, **kwargs):
    calls.append((args, kwargs))
cf.save_figure = supplied_saver
class BrokenLayout:
    def set(self, **kwargs):
        raise RuntimeError('controlled incompatible layout')
class FakeFigure:
    def get_layout_engine(self):
        return BrokenLayout()
figure = FakeFigure()
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    cf._save_pair(figure, Path.cwd() / 'generic.png')
assert cf.save_figure is supplied_saver
assert len(calls) == 1 and calls[0][0] == (figure,)
assert calls[0][1]['renderer'] == 'cohort_figures'
assert calls[0][1]['provenance'] == 'normalized_cohort_tables'
assert any('LAYOUT_ENGINE_RECT_UNAVAILABLE' in str(w.message) for w in caught)
assert cf._HAVE_MPL is True and type(cf._HAVE_MPL) is bool
assert not list(Path.cwd().iterdir())
''')


def test_first_initialization_preserves_numpy_and_other_supplied_plot_aliases(tmp_path):
    _needs("numpy")
    _run(tmp_path, r'''
import contextlib
from types import SimpleNamespace
import mamey.cohort_figures as cf
real_numpy = cf.np
assert '_HAVE_MPL' not in vars(cf) and 'matplotlib' not in sys.modules
lookups = []
class NumpyControl:
    def __getattr__(self, name):
        lookups.append(name)
        return getattr(real_numpy, name)
numpy_control = NumpyControl()
cf.np = numpy_control
record = {'architecture': "{'domain_counts': {'PKS_KS': 1}}"}
profile = cf._strain_profiles({'control': {'gene': {'domain_arch': [record]}}}, ['control'])
real_numpy.testing.assert_allclose(profile['control'][0], real_numpy.log(2.0))
assert {'zeros', 'array', 'log1p'} <= set(lookups)
assert cf.np is numpy_control and '_HAVE_MPL' not in vars(cf)
style_calls = []
@contextlib.contextmanager
def supplied_context(style):
    style_calls.append(style)
    yield
matplotlib_control = SimpleNamespace(rc_context=supplied_context)
plt_control, mp_control, norm_control = object(), object(), object()
cf.matplotlib, cf.plt, cf.mp, cf.LogNorm = matplotlib_control, plt_control, mp_control, norm_control
def supplied_saver(*args, **kwargs):
    return None
cf.save_figure = supplied_saver
@cf._with_cohort_style
def explicit_call():
    return 'called'
assert explicit_call() == 'called' and style_calls == [cf._COHORT_STYLE]
assert cf.np is numpy_control and cf.matplotlib is matplotlib_control
assert cf.plt is plt_control and cf.mp is mp_control and cf.LogNorm is norm_control
assert cf._HAVE_MPL is True and type(cf._HAVE_MPL) is bool
assert 'matplotlib' not in sys.modules
''')


def test_scipy_flag_initialization_preserves_supplied_clustering_callables(tmp_path):
    _needs("scipy")
    _run(tmp_path, r'''
import mamey.cohort_figures as cf
assert '_HAS_SCIPY' not in vars(cf) and 'scipy' not in sys.modules
calls = []
def supplied_linkage(value):
    calls.append(('linkage', value))
    return 'tree-control'
def supplied_leaves(value):
    calls.append(('leaves', value))
    return 'leaves-control'
cf.linkage, cf.leaves_list = supplied_linkage, supplied_leaves
assert cf._HAS_SCIPY is True and type(cf._HAS_SCIPY) is bool
assert cf.linkage is supplied_linkage and cf.leaves_list is supplied_leaves
assert cf.linkage('input-control') == 'tree-control'
assert cf.leaves_list('tree-control') == 'leaves-control'
assert calls == [('linkage', 'input-control'), ('leaves', 'tree-control')]
assert '_HAVE_MPL' not in vars(cf)
''')


def test_supplied_availability_flags_do_not_skip_uninitialized_dependencies(tmp_path):
    _needs("numpy", "matplotlib", "scipy")
    _run(tmp_path, r'''
import mamey.cohort_figures as cf
assert not any(n in sys.modules for n in ('numpy', 'matplotlib', 'scipy'))
# A supplied flag controls behavior; it is not proof that aliases were loaded.
cf._HAVE_MPL = True
cf._HAS_SCIPY = True
@cf._with_cohort_style
def explicit_call():
    return cf.matplotlib.rcParams['font.size']
assert explicit_call() == cf._COHORT_STYLE['font.size']
assert cf.np.__name__ == 'numpy' and cf.plt.__name__ == 'matplotlib.pyplot'
assert cf._HAVE_MPL is True and type(cf._HAVE_MPL) is bool
tree = cf.linkage([[0.0], [2.0]], method='single')
assert cf.leaves_list(tree).tolist() == [0, 1]
assert cf._HAS_SCIPY is True and type(cf._HAS_SCIPY) is bool
assert not cf.plt.get_fignums()
''')
