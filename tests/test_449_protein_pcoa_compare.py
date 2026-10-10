"""Card 6275a90d_449_protein_pcoa_collection_compare: tools/protein_pcoa_compare.py on a synthetic PCoA kit.

Checks the rules the card states: the genome-level test uses one value per genome; Benjamini-Hochberg matches the
textbook procedure; points without an identity value never get the identity code; a genus disagreement between the kit
and the cohort table is reported; density uses the region length; the tool refuses a non-empty output folder.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "protein_pcoa_compare.py"
scipy = pytest.importorskip("scipy")
pytest.importorskip("matplotlib")


def _load():
    spec = importlib.util.spec_from_file_location("protein_pcoa_compare", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tsv(path: Path, rows: list[dict]):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader(); w.writerows(rows)


def _kit(tmp: Path) -> Path:
    """Two sets (KS, RES01); collections alpha (4 genomes), beta (3), gamma (3); one SID point, one MIBiG, references."""
    kit = tmp / "kit"
    strains = {"alpha": ["s1", "s2", "s3", "s4"], "beta": ["s5", "s6", "s7"], "gamma": ["s8", "s9", "s10"]}
    ident = {"alpha": [95, 90, 88], "beta": [60, 65, 92], "gamma": [50, 55, 58]}
    for setname in ("KS", "RES01"):
        d = kit / f"out_{setname}"; d.mkdir(parents=True)
        pcoa, near, n = [], [], 0
        for coll, ss in strains.items():
            for s in ss:
                k = 3 if setname == "KS" else (2 if s in ("s1", "s5", "s8") else 1)
                if setname == "RES01" and s in ("s4", "s7"):
                    continue
                for j in range(k):
                    n += 1; pid = f"P{n:04d}"
                    pcoa.append({"id": pid, "PC1": n / 10, "PC2": -n / 10, "PC3": 0, "n_represented": 1, "source": "isolate",
                                 "group": "x", "genus": "Streptomyces", "strain": s})
                    near.append({"id": pid, "strain": s, "nearest_pident": ident[coll][j % 3]})
        pcoa += [{"id": "R1", "PC1": 0, "PC2": 0, "PC3": 0, "n_represented": 4, "source": "reference_held", "group": "r",
                  "genus": "Streptomyces", "strain": "ref1"},
                 {"id": "M1", "PC1": 0.1, "PC2": 0, "PC3": 0, "n_represented": 1, "source": "MIBiG", "group": "m", "genus": "",
                  "strain": "BGC0000001"},
                 {"id": "S1", "PC1": 0.2, "PC2": 0, "PC3": 0, "n_represented": 2, "source": "SID_held", "group": "s",
                  "genus": "Streptomyces", "strain": "SIDX"},
                 {"id": "Q1", "PC1": 0.3, "PC2": 0, "PC3": 0, "n_represented": 1, "source": "isolate", "group": "x",
                  "genus": "Streptomyces", "strain": "outsider"}]
        _tsv(d / f"PCOA_{setname}.tsv", pcoa)
        _tsv(d / f"NEAREST_{setname}.tsv", near)
        (d / f"RUN_{setname}.json").write_text(json.dumps({"set": setname, "pct_axes": [10.0, 5.0, 2.0]}))
    cohort = [{"strain": s, "collection": c, "genus": "Kribbella" if s == "s2" else "Streptomyces"}
              for c, ss in strains.items() for s in ss]
    _tsv(tmp / "cohort.tsv", cohort)
    _tsv(tmp / "region_kb.tsv", [{"strain": s, "region_kb": 200 if s == "s1" else 100}
                                 for ss in strains.values() for s in ss])
    return kit


def _run(tmp: Path, *extra) -> Path:
    mod = _load(); kit = _kit(tmp); out = tmp / "out"
    rc = mod.main(["--kit", str(kit), "--cohort", str(tmp / "cohort.tsv"), "--out", str(out),
                   "--region-kb", str(tmp / "region_kb.tsv"), "--permutations", "200", "--by-collection", "KS", *extra])
    assert rc == 0
    return out


def _rows(path: Path):
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_genome_level_test_uses_one_median_per_genome(tmp_path):
    out = _run(tmp_path, "--no-figures")
    ks = next(r for r in _rows(out / "STATS.tsv") if r["set"] == "KS")
    # every genome in a collection has the same three identities, so the genome medians are 90 / 65 / 55 per collection
    expect = scipy.stats.kruskal([90] * 4, [65] * 3, [55] * 3).pvalue
    assert float(ks["genome_KW_p"]) == pytest.approx(expect, rel=1e-3)
    assert ks["alpha_genomes"] == "4" and ks["alpha_proteins"] == "12"


def test_benjamini_hochberg_matches_textbook():
    mod = _load()
    p = [0.01, 0.04, 0.03, 0.20, float("nan")]
    q = mod.bh(p)
    # sorted 0.01, 0.03, 0.04, 0.20 (n = 4): raw p*n/rank = 0.04, 0.06, 0.0533, 0.20; running minimum from the top
    assert q[0] == pytest.approx(0.04)
    assert q[2] == pytest.approx(0.04 * 4 / 3) and q[1] == pytest.approx(0.04 * 4 / 3)
    assert q[3] == pytest.approx(0.20) and q[4] != q[4]


def test_points_without_identity_never_get_the_identity_code():
    mod = _load()
    assert mod.identity_style({"identity": None}, 70) == "none"
    assert mod.identity_style({"identity": 69.9}, 70) == "below"
    assert mod.identity_style({"identity": 70.0}, 70) == "at_or_above"


def test_sources_list_genus_disagreement_left_out_and_denominators(tmp_path):
    out = _run(tmp_path, "--no-figures")
    src = _rows(out / "SOURCES.tsv")
    assert any(r["kind"] == "genus_disagreement" and r["item"] == "s2" for r in src)
    assert any(r["kind"] == "left_out" and r["item"] == "outsider" for r in src)
    assert any(r["kind"] == "denominator" and r["item"] == "alpha" and r["detail"] == "4 genomes" for r in src)


def test_carriage_density_uses_region_length_and_keeps_raw(tmp_path):
    out = _run(tmp_path, "--no-figures")
    per = {r["strain"]: r for r in _rows(out / "CARRIAGE_PER_GENOME.tsv")}
    assert per["s1"]["proteins"] == "2" and float(per["s1"]["per_100kb_region"]) == pytest.approx(1.0)
    assert per["s4"]["proteins"] == "0"
    car = _rows(out / "CARRIAGE.tsv")[0]
    assert car["alpha_genomes_carrying"] == "3/4" and car["beta_genomes_carrying"] == "2/3"


def test_figures_written_and_caption_kept_off_figures(tmp_path):
    out = _run(tmp_path)
    for name in ("SHARE_BELOW_70", "IDENTITY_DOTPLOTS", "BY_COLLECTION_KS", "CARRIAGE"):
        assert (out / f"{name}.png").exists() and (out / f"{name}.pdf").exists()
    assert "not show that a strain is resistant" in (out / "CAPTION.md").read_text()


def test_refuses_non_empty_output(tmp_path):
    mod = _load(); kit = _kit(tmp_path); out = tmp_path / "busy"; out.mkdir(); (out / "x").write_text("x")
    rc = mod.main(["--kit", str(kit), "--cohort", str(tmp_path / "cohort.tsv"), "--out", str(out), "--no-figures"])
    assert rc == 2


def test_tool_source_carries_no_cohort_identifiers():
    src = TOOL.read_text()
    assert not re.search(r"\bAS-\d+", src) and not re.search(r"\bSID\d+", src)


def test_denominator_does_not_shrink_when_one_set_is_selected(tmp_path):
    """Review A02: a cohort genome present only in set U must still count when only set T is selected."""
    mod = _load(); kit = _kit(tmp_path)
    # s4 and s7 have no RES01 proteins (see _kit), so with only RES01 selected they would vanish from a set-derived roster
    out = tmp_path / "only_res"
    assert mod.main(["--kit", str(kit), "--cohort", str(tmp_path / "cohort.tsv"), "--out", str(out), "--sets", "RES01",
                     "--no-figures", "--permutations", "50"]) == 0
    car = _rows(out / "CARRIAGE.tsv")[0]
    assert car["alpha_genomes_carrying"] == "3/4" and car["beta_genomes_carrying"] == "2/3"
    den = _rows(out / "DENOMINATOR.tsv")
    members = {r["strain"] for r in den if r["status"] == "member"}
    assert {"s4", "s7"} <= members and len(members) == 10
    per = {r["strain"]: r for r in _rows(out / "CARRIAGE_PER_GENOME.tsv")}
    assert per["s4"]["proteins"] == "0"          # zero-carrier rows kept


def test_pairwise_values_are_labelled_raw(tmp_path):
    out = _run(tmp_path, "--no-figures")
    cols = _rows(out / "STATS.tsv")[0].keys()
    assert any(c.endswith("_p_raw") and c.startswith("protein_MW_") for c in cols)
    assert not any(c.startswith("protein_MW_") and (c.endswith("_p") or c.endswith("_q")) for c in cols)


def test_run_json_is_hashed(tmp_path):
    out = _run(tmp_path, "--no-figures")
    src = _rows(out / "SOURCES.tsv")
    assert any(r["kind"] == "input" and r["item"].endswith("RUN_KS.json") for r in src)
    assert any(r["kind"] == "software" and r["item"] == "scipy" for r in src)
    assert any(r["kind"] == "option" and r["item"] == "cut" for r in src)


@pytest.mark.parametrize("bad", ["nan", "inf", "-1", "101", "abc"])
def test_bad_identity_is_refused(tmp_path, bad):
    mod = _load(); kit = _kit(tmp_path)
    p = kit / "out_KS" / "NEAREST_KS.tsv"
    rows = _rows(p); rows[0]["nearest_pident"] = bad; _tsv(p, rows)
    assert mod.main(["--kit", str(kit), "--cohort", str(tmp_path / "cohort.tsv"), "--out", str(tmp_path / "o"),
                     "--no-figures"]) == 2


def test_conflicting_cohort_rows_are_refused(tmp_path):
    mod = _load(); kit = _kit(tmp_path)
    rows = _rows(tmp_path / "cohort.tsv"); rows.append({**rows[0], "collection": "beta"}); _tsv(tmp_path / "cohort.tsv", rows)
    assert mod.main(["--kit", str(kit), "--cohort", str(tmp_path / "cohort.tsv"), "--out", str(tmp_path / "o"),
                     "--no-figures"]) == 2


def test_roster_ignores_noncanonical_pcoa_files(tmp_path):
    """A stale export beside the canonical table must not alter cohort membership."""
    mod = _load(); kit = _kit(tmp_path)
    of, *_ = mod.load_cohort(tmp_path / "cohort.tsv")
    of["extra"] = "alpha"
    row = {"strain": "extra", "source": "isolate"}
    _tsv(kit / "out_KS" / "PCOA_old.tsv", [row])
    stray = kit / "out_unfinished"; stray.mkdir()
    _tsv(stray / "PCOA_old.tsv", [row])
    present, per_set = mod.cohort_roster(kit, of)
    assert "extra" not in present
    assert set(per_set) == {"KS", "RES01"}
    assert per_set["KS"] == set(of) - {"extra"}


def test_selected_run_hashes_unselected_denominator_source(tmp_path):
    """The unselected KS table contributes zero carriers to RES01's denominator and must be bound."""
    mod = _load(); kit = _kit(tmp_path); out = tmp_path / "selected"
    assert mod.main(["--kit", str(kit), "--cohort", str(tmp_path / "cohort.tsv"),
                     "--out", str(out), "--sets", "RES01", "--no-figures", "--permutations", "10"]) == 0
    inputs = {r["item"]: r["detail"] for r in _rows(out / "SOURCES.tsv") if r["kind"] == "input"}
    path = kit / "out_KS" / "PCOA_KS.tsv"
    assert inputs[str(path)] == mod.sha256(path)
    assert len([r for r in _rows(out / "SOURCES.tsv") if r["kind"] == "input" and r["item"] == str(path)]) == 1
