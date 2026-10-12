"""Offline cohort-admission controls; all package/domain rows are synthetic."""
import csv
import json
from pathlib import Path

import pytest

from tools import build_domain_matrix as B


def _package(root, folder, strain, domains, genome_bp=5_000_000):
    package = root / folder / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({
        "strain_id": strain,
        "assembly": {"genome_bp": genome_bp, "assembly_tier": "GOOD"},
    }), encoding="utf-8")
    with (package / f"{strain}_gene_by_gene_all_bgcs.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["locus_tag", "sec_met_domains"])
        for index, domain in enumerate(domains, 1):
            writer.writerow([f"synthetic_{index}", domain])
    return package


def _two_packages(root):
    first = _package(root, "first", "SYNTH-A", ["PKS_KS", "halogenase"])
    second = _package(root, "second", "SYNTH-B", ["PKS_KS"], 10_000_000)
    return first, second


def test_repeated_cohort_root_loads_each_physical_package_once(tmp_path, monkeypatch):
    root = tmp_path / "cohort"
    first, second = _two_packages(root)
    original = B.load_strain
    calls = []

    def tracked(package):
        calls.append(Path(package).resolve())
        return original(package)

    monkeypatch.setattr(B, "load_strain", tracked)
    strains, _, split = B.build([str(root), str(root)], [])
    assert [row["strain"] for row in strains] == ["SYNTH-A", "SYNTH-B"]
    assert calls.count(first.resolve()) == calls.count(second.resolve()) == 1
    assert split["presence"] == {"PKS_KS": 2, "halogenase": 1}
    assert split["core"] == ["PKS_KS"]
    assert split["private"] == ["halogenase"]
    assert split["accessory"] == []


def test_overlapping_root_and_explicit_packages_preserve_outputs(tmp_path):
    root = tmp_path / "cohort"
    first, second = _two_packages(root)
    vocab = B._vocab()
    baseline = B.build([str(root)], vocab)
    repeated = B.build([str(root), str(first), str(second), str(root)], vocab)
    assert repeated == baseline
    plain_out, repeated_out = tmp_path / "plain", tmp_path / "repeated"
    expected = B.write_outputs(*baseline, vocab, str(plain_out))
    assert B.write_outputs(*repeated, vocab, str(repeated_out)) == expected
    assert expected == {"n_strains": 2, "n_domains": 2, "core": 1, "accessory": 0, "private": 1}
    names = {path.name for path in plain_out.iterdir()}
    assert names == {"domain_matrix_counts.csv", "domain_matrix_density_per_mbp.csv",
                     "domain_functional_rollup.csv", "Domain_Matrix.md"}
    assert all((plain_out / name).read_bytes() == (repeated_out / name).read_bytes()
               for name in names)
    with (plain_out / "domain_matrix_counts.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["domain", "function", "SYNTH-A", "SYNTH-B", "n_strains_present"]
        rows = {row["domain"]: row for row in reader}
    assert rows["halogenase"]["n_strains_present"] == "1"
    with (plain_out / "domain_matrix_density_per_mbp.csv").open(newline="", encoding="utf-8") as handle:
        density = {row["domain"]: row for row in csv.DictReader(handle)}
    assert density["PKS_KS"]["SYNTH-A"] == "0.2"
    assert density["PKS_KS"]["SYNTH-B"] == "0.1"


def test_symlinked_package_is_the_same_physical_input(tmp_path):
    root = tmp_path / "cohort"
    first, _ = _two_packages(root)
    alias = tmp_path / "package-alias"
    try:
        alias.symlink_to(first, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")
    assert B.build([str(root), str(alias)], []) == B.build([str(root)], [])


@pytest.mark.parametrize("same_root", [True, False])
def test_distinct_packages_with_one_strain_are_an_identity_hold(tmp_path, same_root):
    first_root = tmp_path / "first_root"
    second_root = first_root if same_root else tmp_path / "second_root"
    first = _package(first_root, "first", "SYNTH-A", ["PKS_KS"])
    second = _package(second_root, "second", "SYNTH-A", ["halogenase"])
    roots = [str(first_root)] if same_root else [str(first_root), str(second_root)]
    with pytest.raises(ValueError, match="DOMAIN_MATRIX_AMBIGUOUS_STRAIN") as error:
        B.build(roots, [])
    assert "SYNTH-A" in str(error.value)
    assert str(first.resolve()) in str(error.value)
    assert str(second.resolve()) in str(error.value)


@pytest.mark.parametrize("existing_output", [False, True])
def test_cli_identity_hold_precedes_any_output_write(tmp_path, monkeypatch, capsys, existing_output):
    root = tmp_path / "cohort"
    _package(root, "first", "SYNTH-A", ["PKS_KS"])
    _package(root, "second", "SYNTH-A", ["halogenase"])
    out = tmp_path / "out"
    if existing_output:
        out.mkdir()
        (out / "sentinel.txt").write_bytes(b"existing evidence\n")

    def unexpected_write(*args, **kwargs):
        pytest.fail("ambiguous strain must be refused before matrix writes")

    monkeypatch.setattr(B, "write_outputs", unexpected_write)
    with pytest.raises(SystemExit) as error:
        B.main(["--cohort-dir", str(root), "--out-dir", str(out)])
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "DOMAIN_MATRIX_AMBIGUOUS_STRAIN" in captured.err
    if existing_output:
        assert [path.name for path in out.iterdir()] == ["sentinel.txt"]
        assert (out / "sentinel.txt").read_bytes() == b"existing evidence\n"
    else:
        assert not out.exists()


@pytest.mark.parametrize("reverse", [False, True])
def test_multiple_gene_tables_refuse_independently_of_glob_order(tmp_path, monkeypatch, reverse):
    package = _package(tmp_path, "first", "SYNTH-A", ["PKS_KS"])
    first = package / "SYNTH-A_gene_by_gene_all_bgcs.csv"
    second = package / "OTHER_gene_by_gene_all_bgcs.csv"
    second.write_text("locus_tag,sec_met_domains\nsynthetic_2,halogenase\n", encoding="utf-8")
    paths = [str(first), str(second)]
    if reverse:
        paths.reverse()

    def synthetic_glob(pattern):
        assert pattern == str(package / "*_gene_by_gene_all_bgcs.csv")
        return paths

    monkeypatch.setattr(B.glob, "glob", synthetic_glob)
    with pytest.raises(ValueError, match="DOMAIN_MATRIX_AMBIGUOUS_GENE_TABLE") as error:
        B.load_strain(str(package))
    assert str(first) in str(error.value) and str(second) in str(error.value)


def test_missing_and_unique_gene_table_semantics_are_retained(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "manifest.json").write_text('{"strain_id":"SYNTH-EMPTY"}', encoding="utf-8")
    assert B.load_strain(str(empty)) is None
    package = _package(tmp_path, "unique", "SYNTH-A", ["PKS_KS", "halogenase"])
    row = B.load_strain(str(package))
    assert row == {"strain": "SYNTH-A", "mbp": 5.0, "tier": "GOOD", "genes": 2,
                   "domains": {"PKS_KS": 1, "halogenase": 1}}


@pytest.mark.parametrize("existing_output", [False, True])
def test_cli_ambiguous_gene_table_precedes_any_write(tmp_path, monkeypatch, capsys, existing_output):
    package = _package(tmp_path, "first", "SYNTH-A", ["PKS_KS"])
    (package / "OTHER_gene_by_gene_all_bgcs.csv").write_text(
        "locus_tag,sec_met_domains\nsynthetic_2,halogenase\n", encoding="utf-8"
    )
    out = tmp_path / "out"
    if existing_output:
        out.mkdir()
        (out / "sentinel.txt").write_bytes(b"existing evidence\n")

    def unexpected_write(*args, **kwargs):
        pytest.fail("ambiguous gene table must be refused before matrix writes")

    monkeypatch.setattr(B, "write_outputs", unexpected_write)
    with pytest.raises(SystemExit) as error:
        B.main(["--cohort-dir", str(package), "--out-dir", str(out)])
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "DOMAIN_MATRIX_AMBIGUOUS_GENE_TABLE" in captured.err
    if existing_output:
        assert [path.name for path in out.iterdir()] == ["sentinel.txt"]
        assert (out / "sentinel.txt").read_bytes() == b"existing evidence\n"
    else:
        assert not out.exists()
