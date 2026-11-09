"""A requested pyswrd prefilter that cannot run is refused, never silently replaced by the exhaustive path."""
import builtins
import importlib.util
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cluster_gene_compare.py"


def _module():
    spec = importlib.util.spec_from_file_location("cgc_464r3", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_unimportable_pyswrd_is_refused(monkeypatch):
    m = _module()
    real = builtins.__import__

    def fake(name, *args, **kwargs):
        if name == "pyswrd":
            raise ImportError("not installed (synthetic)")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake)
    with pytest.raises(RuntimeError, match="CLUSTER_GENE_COMPARE_ENGINE_UNAVAILABLE"):
        m.prefilter([("a", [{"aa": "MAAA"}]), ("b", [{"aa": "MAAA"}])], 30.0)
