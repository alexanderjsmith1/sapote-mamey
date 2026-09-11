"""AMBER_04 (v9.7.349): tests for the MLSA outgroup-stability scan's RF core
(tools/mlsa_outgroup_scan.py).

No external tools, no tree building. Checks the Robinson-Foulds distance on shared
ingroup tips: identical ingroup topology under two different outgroups gives RF=0
(STABLE), and a genuine ingroup rearrangement gives RF>0 (CHECK). Outgroup tips are
dropped before comparison so only the ingroup is judged.
"""
import os
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_S = os.path.join(ROOT, "tools", "mlsa_outgroup_scan.py")
spec = importlib.util.spec_from_file_location("mlsa_outgroup_scan", _S)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

# Same ingroup topology ((A,B),(C,D)); two different outgroups O1 vs O2.
T1 = "((((A:1,B:1):1,(C:1,D:1):1):1,O1_OUTGROUP:2):0);"
T2 = "((((A:1,B:1):1,(C:1,D:1):1):1,O2_OUTGROUP:2):0);"
# Different ingroup: ((A,C),(B,D)) — a real rearrangement.
T3 = "((((A:1,C:1):1,(B:1,D:1):1):1,O2_OUTGROUP:2):0);"


def test_identical_ingroup_different_outgroup_is_rf0():
    rf, nshared, mx = scan.rf_distance(T1, T2)
    assert nshared == 4                      # A,B,C,D (outgroups dropped)
    assert rf == 0                           # STABLE


def test_rearranged_ingroup_is_rf_positive():
    rf, nshared, mx = scan.rf_distance(T1, T3)
    assert nshared == 4
    assert rf > 0                            # CHECK — ingroup moved


def test_bipartitions_are_nontrivial_only():
    root = scan._parse(T1)
    parts = scan.bipartitions(root, restrict={"A", "B", "C", "D"})
    # the only non-trivial split among 4 ingroup tips is {A,B} | {C,D}
    assert frozenset({"A", "B"}) in parts or frozenset({"C", "D"}) in parts
    for p in parts:
        assert 1 < len(p) < 4
