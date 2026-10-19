"""Synthetic supported-parser/handler controls; no biological inputs or subprocesses."""
import hashlib
import json

import pytest
from mamey import discover


def _args(root, *options):
    return discover._build_parser().parse_args([str(root), *map(str, options)])


@pytest.mark.parametrize("selected", ["json", "tsv"])
def test_incomplete_catalog_pair_refuses_before_report_mutation(tmp_path, capsys, selected):
    root = tmp_path / "empty_workspace"
    root.mkdir()
    report = tmp_path / "report.md"
    report.write_bytes(b"retained caller report\n")
    output = tmp_path / ("catalog." + selected)
    args = _args(root, "--emit-md", report, "--emit-source-catalog-" + selected, output)
    with pytest.raises(ValueError, match="both source-catalog output paths"):
        discover.discover_command(args)
    assert report.read_bytes() == b"retained caller report\n", "invalid options overwrote caller report"
    assert not output.exists()
    assert capsys.readouterr().out == "", "refused output request printed a success report"


def test_catalog_without_registry_refuses_before_report_mutation(tmp_path, capsys):
    root = tmp_path / "empty_workspace"
    root.mkdir()
    report = tmp_path / "report.md"
    report.write_bytes(b"retained caller report\n")
    first, second = tmp_path / "catalog.json", tmp_path / "catalog.tsv"
    args = _args(root, "--emit-md", report, "--emit-source-catalog-json", first,
                 "--emit-source-catalog-tsv", second)
    with pytest.raises(ValueError, match="source-catalog outputs require"):
        discover.discover_command(args)
    assert report.read_bytes() == b"retained caller report\n"
    assert not first.exists() and not second.exists()
    assert capsys.readouterr().out == ""


def test_ordinary_markdown_replacement_keeps_documented_contract(tmp_path, capsys):
    root = tmp_path / "empty_workspace"
    root.mkdir()
    report = tmp_path / "report.md"
    report.write_bytes(b"previous report\n")
    assert discover.discover_command(_args(root, "--emit-md", report)) == 0
    expected = discover._render(discover.run(root, 6))
    assert report.read_text() == expected
    assert "[wrote " in capsys.readouterr().out
    assert list(root.iterdir()) == []


def test_registered_catalog_pair_and_markdown_still_write(tmp_path, capsys):
    root = tmp_path / "empty_workspace"
    root.mkdir()
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"schema_version": "sapote-source-collection-registry-v1",
        "rules": [{"collection_type": "TOY_TEXT", "directory_regex": "toy",
                   "material_file_regex": "example.txt"}]}))
    bound = hashlib.sha256(registry.read_bytes()).hexdigest()
    first, second, report = tmp_path / "catalog.json", tmp_path / "catalog.tsv", tmp_path / "report.md"
    args = _args(root, "--source-collection-registry", registry,
                 "--expected-source-collection-registry-sha256", bound, "--source-root-id", "TOY",
                 "--emit-source-catalog-json", first, "--emit-source-catalog-tsv", second,
                 "--emit-md", report)
    assert discover.discover_command(args) == 0
    catalog = json.loads(first.read_text())
    assert catalog["status"] == "PASS_COMPLETE" and catalog["collections"] == []
    assert second.read_text().startswith("collection_id\t")
    assert "Workspace evidence collections" in report.read_text()
    assert "[wrote source catalog:" in capsys.readouterr().out
    assert hashlib.sha256(registry.read_bytes()).hexdigest() == bound


def test_plain_discovery_needs_no_catalog_options(tmp_path, capsys):
    assert discover.discover_command(_args(tmp_path, "--json")) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["packages"] == [] and "source_catalog" not in report
    assert list(tmp_path.iterdir()) == []
