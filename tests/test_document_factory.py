from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest
import yaml

from mamey.document_factory import (
    DocumentFactoryError, build_project, check_project, init_project,
)
from mamey.sapote_markdown import parse_path


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "token_light_documents"


@pytest.fixture(scope="session")
def pilot_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """v9.7.412: build the pilot INTO A TEMP DIR. The fixture used to run the builder against the shipped
    `pilot_project/`, rewriting release assets on every suite run (the PNG is not byte-stable across hosts,
    so `verify_release_identity` flipped after a run in another environment)."""
    root = tmp_path_factory.mktemp("token_light") / "pilot_project"
    subprocess.run([sys.executable, str(EXAMPLE / "build_pilot_inputs.py"), "--out", str(root)], check=True)
    return root / "sapote-documents.yml"


def test_pilot_builder_never_writes_into_shipped_examples(tmp_path: Path) -> None:
    """Regression guard: a redirected build leaves every shipped pilot file byte-identical."""
    shipped = EXAMPLE / "pilot_project"
    before = {p.relative_to(shipped): p.read_bytes() for p in shipped.rglob("*") if p.is_file()}
    subprocess.run([sys.executable, str(EXAMPLE / "build_pilot_inputs.py"), "--out", str(tmp_path / "pp")], check=True)
    after = {p.relative_to(shipped): p.read_bytes() for p in shipped.rglob("*") if p.is_file()}
    assert after == before, "a redirected pilot build must not touch the shipped pilot_project/"
    assert (tmp_path / "pp" / "sapote-documents.yml").is_file()


def test_check_preflights_all_ten_documents(pilot_project: Path) -> None:
    result = check_project(pilot_project)
    assert result["status"] == "PASS"
    assert result["document_count"] == 10
    assert len(result["normalized_sha256"]) == 10


def test_ten_document_build_is_complete_and_token_light(
    pilot_project: Path, tmp_path: Path,
) -> None:
    pytest.importorskip("docx")
    pytest.importorskip("lxml")
    pytest.importorskip("reportlab")
    outdir = tmp_path / "rendered"
    result = build_project(pilot_project, outdir=outdir)
    assert result["status"] == "PASS"
    assert result["document_count"] == 10
    assert result["template_count"] == 4
    assert len(result["outputs"]) == 20
    assert result["token_light_metrics"]["reuse_multiple"] > 2
    assert all(Path(item["path"]).is_file() for item in result["outputs"])
    assert (outdir / "DOCUMENT_FACTORY_RECEIPT.json").is_file()

    normalized = outdir / "normalized" / "modeb_alpha" / "modeb_alpha.md"
    model = parse_path(normalized)
    section_headings = [
        block for block in model.blocks
        if block.kind == "heading" and block.data["level"] == 2
    ]
    assert len(section_headings) == 48
    assert model.meta.exact_locus.display == (
        "DEMO-ALPHA / demo_contig_alpha_length_80000 / region001 / BGC001"
    )
    matrix = next(block for block in model.blocks if block.kind == "table")
    assert len(matrix.data["rows"][0]) == 11

    render_receipt = json.loads(
        (outdir / "documents" / "modeb_alpha" / "modeb_alpha.render_receipt.json").read_text(encoding="utf-8")
    )
    assert str(outdir) in render_receipt["input_path"]
    assert ".sapote-doc-build-" not in json.dumps(render_receipt)

    report_docx = outdir / "documents" / "report_evidence" / "report_evidence.docx"
    with zipfile.ZipFile(report_docx) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert 'descr="Four synthetic evidence-state bars"' in document_xml
    assert 'title="Figure evidence"' in document_xml

    guide_docx = outdir / "documents" / "guide_quickstart" / "guide_quickstart.docx"
    with zipfile.ZipFile(guide_docx) as archive:
        guide_xml = archive.read("word/document.xml").decode("utf-8")
    assert 'w:pStyle w:val="ListParagraph"' in guide_xml
    assert "1." in guide_xml and "2." in guide_xml and "3." in guide_xml
    assert 'w:pStyle w:val="ListNumber"' not in guide_xml


def test_project_preflight_failure_publishes_no_output(
    pilot_project: Path, tmp_path: Path,
) -> None:
    project_root = tmp_path / "bad_project"
    shutil.copytree(pilot_project.parent, project_root)
    manifest_path = project_root / "sapote-documents.yml"
    project = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    project["documents"][0]["variables"].pop("lead")
    manifest_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    output = tmp_path / "must_not_exist"
    with pytest.raises(DocumentFactoryError, match="TEMPLATE_VARIABLES_MISSING"):
        build_project(manifest_path, outdir=output)
    assert not output.exists()


def test_existing_output_root_is_never_overwritten(
    pilot_project: Path, tmp_path: Path,
) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "owner.txt"
    marker.write_text("preserve\n", encoding="utf-8")
    with pytest.raises(DocumentFactoryError, match="OUTPUT_ROOT_ALREADY_EXISTS"):
        build_project(pilot_project, outdir=output)
    assert marker.read_text(encoding="utf-8") == "preserve\n"


def test_init_creates_minimal_project_without_overwriting(tmp_path: Path) -> None:
    root = tmp_path / "starter"
    created = init_project(root)
    assert len(created) == 2
    assert check_project(root / "sapote-documents.yml")["document_count"] == 1
    with pytest.raises(DocumentFactoryError, match="INIT_DIRECTORY_NOT_EMPTY"):
        init_project(root)
