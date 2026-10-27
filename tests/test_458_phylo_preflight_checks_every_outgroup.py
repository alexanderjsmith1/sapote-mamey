"""phylo_preflight runs the O2 (genus not in ingroup) and O3 (sister group) checks for every outgroup.

With more than one outgroup it printed the O1 WARN and skipped O2 and O3 entirely, so an
outgroup from an ingroup genus, or a distant one, passed unchecked.
Hermetic: environment, genome-file and registry checks are stubbed; nothing runs or is written.
"""
import importlib.util
import os
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools")
sys.path.insert(0, TOOLS)


def _load():
    spec = importlib.util.spec_from_file_location("phylo_preflight_458", os.path.join(TOOLS, "phylo_preflight.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run(monkeypatch, tmp_path, names):
    mod = _load()
    d = tmp_path / "genomes"
    d.mkdir()
    for n in names:
        (d / n).write_text(">x\nACGT\n")
    for fn in ("check_env", "check_genomes", "check_assembly_quality", "check_superseded",
               "check_cohort", "check_genus_comparators", "check_registry_accessions"):
        monkeypatch.setattr(mod, fn, lambda *a, **k: None)
    monkeypatch.setattr(mod, "load_ssot", lambda: ({}, {}))
    monkeypatch.setattr(mod, "load_spec", lambda _d: ({"scope": "family", "taxon": "Streptomycetaceae"}, "spec"))
    got = {}
    monkeypatch.setattr(mod, "_emit", lambda rep, a: got.setdefault("rep", rep))
    monkeypatch.setattr(sys, "argv", ["phylo_preflight", str(d)])
    with pytest.raises(SystemExit):
        mod.main()
    return [i for i in got["rep"].items if i["check"] in ("O2", "O3")]


INGROUP = ["Streptomyces_coelicolor_A.fna", "Streptomyces_griseus_B.fna"]


def test_two_outgroups_each_get_o2_and_o3(monkeypatch, tmp_path):
    rows = _run(monkeypatch, tmp_path, INGROUP + ["Kitasatospora_setae_OUTGROUP.fna",
                                                  "Streptomyces_albus_OUTGROUP.fna"])
    o2 = [r for r in rows if r["check"] == "O2"]
    assert len(o2) == 2
    bad = [r for r in o2 if r["status"] == "FAIL"]
    assert len(bad) == 1 and "Streptomyces_albus_OUTGROUP.fna" in bad[0]["detail"]
    assert len([r for r in rows if r["check"] == "O3"]) == 2


def test_single_outgroup_output_is_unchanged(monkeypatch, tmp_path):
    rows = _run(monkeypatch, tmp_path, INGROUP + ["Kitasatospora_setae_OUTGROUP.fna"])
    assert [(r["check"], r["status"], r["detail"]) for r in rows] == [
        ("O2", "PASS", "Kitasatospora"),
        ("O3", "PASS", "Kitasatospora (Streptomycetaceae, Streptomycetales)"),
    ]
