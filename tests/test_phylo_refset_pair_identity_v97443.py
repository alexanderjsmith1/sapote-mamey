"""Tier-2 dedup reports the identity of the pair it collapsed, not the run's maximum.

Before the fix every Tier-2 collapse quoted max() over all measured pairs in the run, so an
unrelated 100% pair was written beside a 99.60% collapse. A member linked to the kept record only
through a third record has no direct measurement, so its identity is left blank.
Hermetic: makeblastdb/blastn are replaced with a canned BLAST table.
"""
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")

RECS = [
    ("Streptomyces_alpha_strain_DSM_1_NR_000001", "A" * 1400),
    ("Streptomyces_alpha_strain_JCM_2_NR_000002", "A" * 1400),
    ("Streptomyces_beta_strain_DSM_3_NR_000003", "C" * 1400),
    ("Streptomyces_beta_strain_JCM_4_NR_000004", "C" * 1400),
    ("Streptomyces_gamma_strain_DSM_5_NR_000005", "G" * 1400),
    ("Streptomyces_gamma_strain_JCM_6_NR_000006", "G" * 1400),
    ("Streptomyces_gamma_strain_NBRC_7_NR_000007", "G" * 1400),
]
# s0..s6 follow RECS order. gamma is a chain: s4~s5 and s5~s6, with no s4~s6 alignment.
DIRECT = {("s0", "s1"): 99.60, ("s2", "s3"): 100.00, ("s4", "s5"): 99.70, ("s5", "s6"): 99.80}


def _load():
    spec = importlib.util.spec_from_file_location("phylo_refset_pairid_v97443", os.path.join(TOOLS, "phylo_refset.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _fake_run(cmd, *a, **k):
    if os.path.basename(cmd[0]) == "blastn":
        lines = [f"{q}\t{s}\t{pid}\t1400\t1400\t1400" for (q, s), pid in DIRECT.items()]
        return subprocess.CompletedProcess(cmd, 0, "\n".join(lines) + "\n", "")
    return subprocess.CompletedProcess(cmd, 0, "", "")


def test_each_collapse_quotes_its_own_pair(monkeypatch):
    rs = _load()
    monkeypatch.setattr(rs, "_bin", lambda name: f"/stub/{name}")
    monkeypatch.setattr(rs.subprocess, "run", _fake_run)
    kept, collapses = rs.dedup(RECS, report=None, verbose=False)
    sid = {h: f"s{i}" for i, (h, _) in enumerate(RECS)}
    tier2 = [c for c in collapses if c["tier"] == 2]
    assert len(tier2) == 4 and len(kept) == 3
    for c in tier2:
        pair = tuple(sorted((sid[c["kept"]], sid[c["dropped"]])))
        want = f"{DIRECT[pair]:.2f}" if pair in DIRECT else ""
        assert c["identity"] == want, (c["kept"], c["dropped"], c["identity"])
    assert any(c["identity"] == "" for c in tier2)  # the chain member has no direct pair
