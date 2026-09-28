"""RG-GMCI's locus-number proxy must give the same answer under any Python hash seed.

Two locus-tag namespaces can tie on the smallest gap. The winner used to be whichever the set iterated
first, which depends on PYTHONHASHSEED, so the reported adjacency_span changed from run to run.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = """
from types import SimpleNamespace
from mamey.rggmci import _proxy_adjacency
ref = lambda subjects: SimpleNamespace(subjects=subjects)   # _proxy_adjacency reads only .subjects
# namespace CAB: many loci, gap 0, span 370; namespace CAD: one shared locus, gap 0, span 0
a = ref(["CAB38517.1", "CAB38887.1", "CAD55498.1"]); b = ref(["CAB38517.1", "CAD55498.1"])
print(_proxy_adjacency(a, b))
"""


def _run(seed: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
    return subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True,
                          check=True).stdout.strip()


def test_tie_is_broken_by_evidence_not_by_hash_seed():
    outs = {_run(str(seed)) for seed in range(8)}
    assert len(outs) == 1, outs
    assert outs.pop() == "('ADJACENT_OR_NEARBY_REFERENCE_SEGMENTS', 0, 370)"   # the many-loci namespace wins
