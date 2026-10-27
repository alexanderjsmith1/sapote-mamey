"""--host-override cannot bring an excluded or unknown strain back into domain_prevalence.

The override wrote `hostmap[k] = None` for a strain outside scope; its features then passed the
`st in hostmap` check and were counted, and the strain index lookup could raise.
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_prev_fixture_458o", ROOT / "tests" / "test_domain_prevalence_v97413.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


class _Args:
    pass


def _run(tmp_path, overrides):
    cen, gbk, out = tmp_path / "c.sqlite", tmp_path / "g.sqlite", tmp_path / "out"
    _fx._census(str(cen))
    _fx._gbk(str(gbk))
    a = _Args()
    a.census, a.gbk_domains, a.out = str(cen), str(gbk), str(out)
    a.nr = a.cnr = a.sp = None
    a.host_tsv, a.host_strain_col, a.host_source_col, a.host_class_col = None, "strain", "source", None
    a.exclude, a.host_override, a.rare_loci_max = ["SYNTHETIC-CASE-002"], overrides, 5
    _fx._load().build(a)
    return json.load(open(out / "domain_prevalence_ranking.json"))


def test_override_for_an_excluded_strain_is_ignored(tmp_path, capsys):
    r = _run(tmp_path, ["SYNTHETIC-CASE-002=bee"])
    assert r["scope"]["strains"] == 1
    row = {x["domain_label"]: x for x in r["rows"]}["CommonDom"]
    assert row["strains"] == 1
    assert "not in scope" in capsys.readouterr().err


def test_override_for_an_in_scope_strain_applies(tmp_path):
    r = _run(tmp_path, ["AS-1=moss"])
    row = {x["domain_label"]: x for x in r["rows"]}["CommonDom"]
    assert set(row["by_host"]) == {"moss"}
