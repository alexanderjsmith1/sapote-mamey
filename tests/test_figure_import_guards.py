"""B4 + #35: every figure module must IMPORT cleanly when matplotlib is absent (guard the module,
not just define _HAVE_MPL). Run in a subprocess so blocking matplotlib doesn't pollute the session.
The .210 test only asserted hasattr(_HAVE_MPL) WITH matplotlib installed — it never simulated absence,
which is why B4 (unconditional plt.rcParams + a stray LogNorm import in cohort_figures) slipped through."""
import subprocess, sys, textwrap

_MODS = ["mamey.cohort_figures", "mamey.collection_figures", "mamey.locus_map",
         # W2-H3/v9.7.352: these were cli-/heatmap-imported with UNGUARDED matplotlib -> core-only crash
         "mamey.master_figure_atlas", "mamey.cohort_figures_extended"]

def _import_without_matplotlib(modname):
    code = textwrap.dedent(f"""
        import sys, builtins
        _real = builtins.__import__
        def block(name, *a, **k):
            if name == "matplotlib" or name.startswith("matplotlib."):
                raise ModuleNotFoundError("No module named '" + name + "'")
            return _real(name, *a, **k)
        builtins.__import__ = block
        import {modname} as m
        assert m._HAVE_MPL is False, "expected _HAVE_MPL False when matplotlib blocked"
        print("OK")
    """)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

def test_figure_modules_import_without_matplotlib():
    for mod in _MODS:
        r = _import_without_matplotlib(mod)
        assert r.returncode == 0 and "OK" in r.stdout, f"{mod} failed to import without matplotlib:\n{r.stderr}"
