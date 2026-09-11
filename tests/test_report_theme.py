import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("report_theme_patch", ROOT / "mamey" / "report_theme.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

THEME_NAME = module.THEME_NAME
format_locus_identity = module.format_locus_identity
section_accent = module.section_accent
section_role = module.section_role
status_badge = module.status_badge
status_fill = module.status_fill
theme_variant = module.theme_variant


def test_theme_is_presentation_only_and_statuses_are_typed():
    assert THEME_NAME == "sapote-evidence-dossier"
    assert status_fill("PASS") == "DDEFEF"
    assert status_fill("NOT_SCORED") == "F5F1E7"
    assert status_fill("unrecognized") == "F5F1E7"
    assert section_role(4) == "evidence"
    assert section_accent(6) == "gold"
    assert status_badge("hold")["label"] == "HOLD"
    assert format_locus_identity("AS-TEST", "NODE_1", "region001", "BGC001") == "AS-TEST / NODE_1 / region001 / BGC001"
    selected = theme_variant("minimal-clinical")
    assert selected["density"] == "quiet"
    assert selected["tokens"]["colors"]["navy"] == "263238"
    try:
        theme_variant("not-a-theme")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown theme variant was accepted")


def test_theme_variant_returns_isolated_tokens():
    selected = theme_variant("field_notebook")
    selected["colors"]["navy"] = "000000"
    selected["tokens"]["status_fills"]["HOLD"] = "000000"
    fresh = theme_variant("field_notebook")
    assert fresh["colors"]["navy"] == "284B3B"
    assert fresh["tokens"]["status_fills"]["HOLD"] == "F5F1E7"
