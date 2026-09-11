import inspect
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("modeb_export_theme_hook", ROOT / "mamey" / "modeb_export.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_export_functions_accept_explicit_theme():
    assert "theme" in inspect.signature(module.export_card_docx).parameters
    assert "theme" in inspect.signature(module.export_card_pdf).parameters
    assert "theme" in inspect.signature(module.export_card).parameters
    assert "theme" in inspect.signature(module.export_dir).parameters


def test_pdf_renderer_is_package_scoped_not_a_tools_path():
    source = (ROOT / "mamey" / "modeb_export.py").read_text(encoding="utf-8")
    assert (ROOT / "mamey" / "markdown_pdf.py").is_file()
    assert "from . import markdown_pdf" in source
    assert "tools/render_deliverable_pdf.py" not in source


def test_legacy_renderer_is_a_package_api_compatibility_bridge():
    legacy_path = ROOT / "tools" / "render_deliverable_pdf.py"
    spec = importlib.util.spec_from_file_location("legacy_renderer", legacy_path)
    legacy = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(legacy)
    assert callable(legacy.render)
    assert callable(legacy.parse)


def test_export_card_records_normalized_theme_without_rendering(tmp_path, monkeypatch):
    card = tmp_path / "card.md"
    card.write_text("# card\n", encoding="utf-8")
    seen = []

    def fake_docx(md_path, out_path, theme):
        seen.append(("docx", theme))
        return {"status": "WRITTEN", "theme": theme}

    def fake_pdf(md_path, out_path, theme):
        seen.append(("pdf", theme))
        return {"status": "WRITTEN", "theme": theme}

    monkeypatch.setattr(module, "export_card_docx", fake_docx)
    monkeypatch.setattr(module, "export_card_pdf", fake_pdf)
    result = module.export_card(card, outdir=tmp_path / "out", theme="field-notebook")

    assert result["theme"] == "field_notebook"
    assert seen == [("docx", "field_notebook"), ("pdf", "field_notebook")]


def test_unknown_theme_fails_before_renderer_call(tmp_path, monkeypatch):
    card = tmp_path / "card.md"
    card.write_text("# card\n", encoding="utf-8")
    monkeypatch.setattr(module, "export_card_docx", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    try:
        module.export_card(card, outdir=tmp_path / "out", theme="not-a-theme")
    except ValueError as exc:
        assert "unknown Sapote-Mamey report theme" in str(exc)
    else:
        raise AssertionError("unknown theme was accepted")
    assert not (tmp_path / "out").exists()


def test_cli_subcommand_exposes_and_forwards_theme():
    cli_text = (ROOT / "mamey" / "cli.py").read_text(encoding="utf-8")
    start = cli_text.index('mx = sub.add_parser("modeb-export"')
    end = cli_text.index("    # --- resume", start)
    block = cli_text[start:end]
    assert 'mx.add_argument("--theme"' in block
    assert '"--theme", a.theme' in block


def test_both_format_requires_both_outputs(tmp_path, monkeypatch, capsys):
    card = tmp_path / "card.md"
    card.write_text("# card\n", encoding="utf-8")
    monkeypatch.setattr(module, "export_card", lambda *args, **kwargs: {
        "md": str(card),
        "theme": "evidence_dossier",
        "docx": {"status": "SKIPPED_NO_DOCX", "path": None},
        "pdf": {"status": "WRITTEN", "path": str(tmp_path / "card.pdf")},
    })
    rc = module.main([str(card), "--format", "both"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "requires both DOCX and PDF outputs" in captured.err
