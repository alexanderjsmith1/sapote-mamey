from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

import mamey.document_export as document_export
from mamey.document_export import export_document
from mamey.sapote_markdown import parse_path, validate_model


SHIPPED_EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "document_rendering"


@pytest.fixture(scope="session")
def EXAMPLES(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """v9.7.412: a temp COPY of examples/document_rendering with the figure assets re-rendered INTO THE
    COPY. The previous autouse fixture ran the builder against the shipped assets/ dir, so every full
    suite run rewrote release files in place (not byte-stable across hosts -> identity FAIL after a
    run). Nothing under the shipped examples/ is written by this module any more."""
    import shutil
    root = tmp_path_factory.mktemp("document_rendering")
    dest = root / "document_rendering"
    shutil.copytree(SHIPPED_EXAMPLES, dest)
    subprocess.run([sys.executable, str(dest / "build_fixture_images.py"), "--out", str(dest / "assets")], check=True)
    return dest


def test_fixture_builder_never_writes_into_shipped_examples(tmp_path: Path) -> None:
    """Regression guard for the .409-seal finding: rendering must be redirectable and the shipped
    assets must be untouched by a render into another directory."""
    before = {p.name: p.read_bytes() for p in (SHIPPED_EXAMPLES / "assets").glob("*.png")}
    out = tmp_path / "assets"
    subprocess.run([sys.executable, str(SHIPPED_EXAMPLES / "build_fixture_images.py"), "--out", str(out)], check=True)
    assert {p.name for p in out.glob("*.png")} == set(before), "render into --out produced a different file set"
    after = {p.name: p.read_bytes() for p in (SHIPPED_EXAMPLES / "assets").glob("*.png")}
    assert after == before, "a redirected render must not touch the shipped assets"
    import ast
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    autouse = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
               for d in n.decorator_list if isinstance(d, ast.Call)
               for k in d.keywords if k.arg == "autouse" and getattr(k.value, "value", None) is True]
    assert not autouse, f"no autouse fixture may write into the shipped tree: {autouse}"


@pytest.mark.parametrize(
    ("name", "document_type"),
    [
        ("HUMAN_GUIDE_FIXTURE.md", "human_guide"),
        ("ANALYSIS_REPORT_FIXTURE.md", "analysis_report"),
        ("MODEB_48_FIXTURE.md", "mode_b_card"),
    ],
)
def test_representative_fixtures_validate(name: str, document_type: str, EXAMPLES: Path) -> None:
    model = parse_path(EXAMPLES / name)
    result = validate_model(model, require_assets=True)
    assert result.ok, result.issues
    assert model.meta.document_type == document_type


def test_modeb_fixture_is_complete_48_and_exact_bound(EXAMPLES: Path) -> None:
    model = parse_path(EXAMPLES / "MODEB_48_FIXTURE.md")
    headings = [
        block.data["text"] for block in model.blocks
        if block.kind == "heading" and block.data["level"] == 2
    ]
    assert len(headings) == 48
    assert headings[0].startswith("§1 ")
    assert headings[-1].startswith("§48 ")
    assert model.meta.exact_locus.display == (
        "DEMO-STRAIN / demo_contig_0001_length_80000 / region001 / BGC001"
    )
    matrix = next(block for block in model.blocks if block.kind == "table")
    assert matrix.data["id"] == "governed_gene_matrix"
    assert len(matrix.data["rows"][0]) == 11
    assert matrix.data["layout"] == "landscape"


def test_both_export_writes_docx_pdf_and_receipt(tmp_path: Path, EXAMPLES: Path) -> None:
    pytest.importorskip("docx")
    pytest.importorskip("lxml")
    pytest.importorskip("reportlab")
    source = EXAMPLES / "ANALYSIS_REPORT_FIXTURE.md"
    receipt = export_document(source, outdir=tmp_path, output_format="both")
    assert receipt.status == "PASS"
    assert {item["format"] for item in receipt.outputs} == {"docx", "pdf"}
    for item in receipt.outputs:
        path = Path(item["path"])
        assert path.is_file()
        assert path.stat().st_size == item["bytes"] > 0
    receipt_path = tmp_path / "ANALYSIS_REPORT_FIXTURE.render_receipt.json"
    saved = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert saved["model_sha256"] == receipt.model_sha256


def test_both_export_publishes_neither_output_on_backend_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, EXAMPLES: Path,
) -> None:
    pytest.importorskip("docx")
    pytest.importorskip("lxml")
    pytest.importorskip("reportlab")

    def fail_pdf(*args: object, **kwargs: object) -> Path:
        raise RuntimeError("synthetic PDF backend failure")

    monkeypatch.setattr(document_export, "export_pdf", fail_pdf)
    source = EXAMPLES / "HUMAN_GUIDE_FIXTURE.md"
    with pytest.raises(RuntimeError, match="synthetic PDF backend failure"):
        export_document(source, outdir=tmp_path, output_format="both")
    assert not (tmp_path / "HUMAN_GUIDE_FIXTURE.docx").exists()
    assert not (tmp_path / "HUMAN_GUIDE_FIXTURE.pdf").exists()
    assert not (tmp_path / "HUMAN_GUIDE_FIXTURE.render_receipt.json").exists()


def test_modeb_gap_fails_closed(tmp_path: Path, EXAMPLES: Path) -> None:
    source = (EXAMPLES / "MODEB_48_FIXTURE.md").read_text(encoding="utf-8")
    broken = source.replace("## §48 Cross-cohort synthesis & claim ceiling\n", "")
    path = tmp_path / "broken.md"
    path.write_text(broken, encoding="utf-8")
    with pytest.raises(ValueError, match="MODEB_SECTIONS_1_48_REQUIRED"):
        parse_path(path)


def test_unmarked_wide_table_fails_closed(tmp_path: Path, EXAMPLES: Path) -> None:
    source = (EXAMPLES / "HUMAN_GUIDE_FIXTURE.md").read_text(encoding="utf-8")
    source = source.replace("layout=portrait", "layout=auto")
    source = source.replace(
        "| Stage | Tool responsibility | Reader decision |",
        "| A | B | C | D | E | F | G |",
    ).replace(
        "|---|---|---|", "|---|---|---|---|---|---|---|", 1
    ).replace(
        "| Inspect | Preview inputs and likely package structure | Confirm the intended strain and source files |",
        "| 1 | 2 | 3 | 4 | 5 | 6 | 7 |",
    ).replace(
        "| Extract | Parse regions, scans, scores, and provenance deterministically | Check source and gate states |",
        "| 1 | 2 | 3 | 4 | 5 | 6 | 7 |",
    ).replace(
        "| Interpret | Present evidence for governed post-extraction judgment | Decide what is supported, held, or experimentally testable |",
        "| 1 | 2 | 3 | 4 | 5 | 6 | 7 |",
    )
    path = tmp_path / "wide.md"
    path.write_text(source, encoding="utf-8")
    with pytest.raises(ValueError, match="WIDE_TABLE_LAYOUT_REQUIRED"):
        parse_path(path)
