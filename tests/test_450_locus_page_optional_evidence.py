"""Optional evidence must remain distinct from missing paths and biological absence.

Reuse tiny synthetic package/ledger fixtures; no searches or native renderers run.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_449_locus_reading_pages import lrp, fx, _argv, S, ID1, STEM1, STEM2


@pytest.fixture(autouse=True)
def no_external_searches(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("No external search is allowed in optional-evidence fixtures")
    monkeypatch.setattr(lrp.subprocess, "run", refuse)


def _snapshot(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()} if path.exists() else None


@pytest.mark.parametrize("field", ["gene_table_inventory", "gecco"])
@pytest.mark.parametrize("kind", ["missing", "directory", "broken_symlink"])
@pytest.mark.parametrize("existing_out", [False, True])
def test_supplied_nonfile_evidence_refuses_before_any_output(tmp_path, monkeypatch, field, kind, existing_out):
    table = tmp_path / "optional.tsv"
    if kind == "directory":
        table.mkdir()
    elif kind == "broken_symlink":
        table.symlink_to(tmp_path / "absent_target")
    out = tmp_path / "out"
    if existing_out:
        out.mkdir()
        (out / "prior.md").write_bytes(b"prior evidence remains intact\n")
    before = _snapshot(out)
    def no_begin(*args, **kwargs):
        raise AssertionError("Invalid optional inputs must refuse before beginning an output attempt")
    monkeypatch.setattr(lrp, "_page_begin_run", no_begin)
    opts = SimpleNamespace(out=str(out), bgc="BGC001", gene_table_inventory=None, gecco=None)
    setattr(opts, field, str(table))
    with pytest.raises(ValueError, match="PAGE_OPTIONAL_INPUT_NOT_FILE.*--" + field.replace("_", "-")):
        lrp.build(opts)
    assert _snapshot(out) == before
    assert not (out / "_page_searches").exists()


def _without(argv, *flags):
    result = list(argv)
    for flag in flags:
        index = result.index(flag)
        del result[index:index + 2]
    return result


@pytest.mark.parametrize("flag", ["--gene-table-inventory", "--gecco"])
@pytest.mark.parametrize("existing_out", [False, True])
def test_explicit_empty_optional_path_refuses_before_any_output(fx, tmp_path, monkeypatch, flag, existing_out):
    out = tmp_path / "out"
    if existing_out:
        out.mkdir()
        (out / "prior.md").write_bytes(b"prior evidence remains intact\n")
    before = _snapshot(out)
    argv = _argv(fx, out)
    argv[argv.index(flag) + 1] = ""

    def no_begin(*args, **kwargs):
        raise AssertionError("An explicitly empty path must refuse before an output attempt")

    monkeypatch.setattr(lrp, "_page_begin_run", no_begin)
    with pytest.raises(ValueError, match="PAGE_OPTIONAL_INPUT_NOT_FILE: " + flag):
        lrp.main(argv)
    assert _snapshot(out) == before
    assert not (out / "_page_searches").exists()


def test_omitted_comparison_inputs_are_not_provided_in_each_page(fx, tmp_path):
    out = tmp_path / "out"
    argv = _without(_argv(fx, out), "--gene-table-inventory", "--gecco")
    assert lrp.main(argv) == 0
    for stem in (STEM1, STEM2):
        page = (out / S / (stem + ".md")).read_text()
        assert "- **Gene table:** NOT_PROVIDED; comparison evidence was not supplied." in page
        assert "- **GECCO:** NOT_PROVIDED; comparison evidence was not supplied." in page
        assert "- Gene table: NOT_PROVIDED; comparison evidence was not supplied." in page
        assert "- GECCO: NOT_PROVIDED; comparison evidence was not supplied." in page
        assert "No MIBiG cluster met the gene-table threshold" not in page
        assert "no GECCO cluster on these contigs" not in page
    assert f"# {ID1}:" in (out / S / (STEM1 + ".md")).read_text()


@pytest.mark.parametrize("contents", ["empty", "header_only"])
def test_supplied_genuinely_empty_tables_have_evidence_scoped_wording(fx, tmp_path, contents):
    for name in ("INVENTORY.tsv", "gecco.tsv"):
        path = fx / name
        header = path.read_text().splitlines(keepends=True)[0]
        path.write_text(header if contents == "header_only" else "")
    out = tmp_path / "out"
    assert lrp.main(_argv(fx, out)) == 0
    for stem in (STEM1, STEM2):
        page = (out / S / (stem + ".md")).read_text()
        assert "- **Gene table:** no pair for this locus is recorded in the supplied inventory." in page
        assert "- **GECCO:** no cluster for these contigs is recorded in the supplied table." in page
        assert "- Gene table: no pair for this locus is recorded in the supplied inventory." in page
        assert "- GECCO: no cluster for the region contig is recorded in the supplied table." in page
        assert "**Gene table:** NOT_PROVIDED" not in page and "**GECCO:** NOT_PROVIDED" not in page


def test_supplied_tables_preserve_positive_pairs_and_scope_other_loci(fx, tmp_path):
    out = tmp_path / "out"
    assert lrp.main(_argv(fx, out)) == 0
    first = (out / S / (STEM1 + ".md")).read_text()
    second = (out / S / (STEM2 + ".md")).read_text()
    assert "**Gene table (BGC0000001, alpha cluster):**" in first
    assert "**GECCO:** Polyketide cluster" in first
    assert "**Gene table:** no pair for this locus is recorded in the supplied inventory." in second
    assert "**GECCO:** no cluster for these contigs is recorded in the supplied table." in second
    assert "**Gene table:** NOT_PROVIDED" not in first + second
    assert "**GECCO:** NOT_PROVIDED" not in first + second
    assert "- Gene table: no pair for this locus is recorded in the supplied inventory." in second
    assert "- GECCO: no cluster for the region contig is recorded in the supplied table." in second


def test_optional_table_regular_symlinks_preserve_valid_inputs(fx, tmp_path):
    inventory, gecco = tmp_path / "inventory_link.tsv", tmp_path / "gecco_link.tsv"
    inventory.symlink_to(fx / "INVENTORY.tsv")
    gecco.symlink_to(fx / "gecco.tsv")
    argv = _argv(fx, tmp_path / "out")
    argv[argv.index("--gene-table-inventory") + 1] = str(inventory)
    argv[argv.index("--gecco") + 1] = str(gecco)
    assert lrp.main(argv) == 0
    first = (tmp_path / "out" / S / (STEM1 + ".md")).read_text()
    assert "**Gene table (BGC0000001, alpha cluster):**" in first
    assert "**GECCO:** Polyketide cluster" in first


def test_auto_summary_legacy_positional_calls_keep_scoped_supplied_defaults():
    summary = lrp.auto_summary([], "BGC001", {"Products": "test class", "Boundary": "Interior"}, [], [], [])
    assert "0 genes in the region, 0 called core biosynthetic" in summary
    assert "- Gene table: no pair for this locus is recorded in the supplied inventory." in summary
    assert "- GECCO: no cluster for the region contig is recorded in the supplied table." in summary
    assert "NOT_PROVIDED" not in summary
