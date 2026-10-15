"""BiG-SCAPE ingest describes a family without a MIBiG member as such; unknown TSV status stays unknown."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("ingest_status", ROOT / "tools/bigscape_ingest_to_mamey.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_tsv_status_mapping():
    m = _load()
    assert m._tsv_status("KNOWN") == "KNOWN"
    assert m._tsv_status("NOVEL") == "NO_MIBIG_MEMBER"
    assert m._tsv_status("") == "UNKNOWN"
    assert m._tsv_status(None) == "UNKNOWN"
    assert m._tsv_status("anything else") == "UNKNOWN"


def _ctx(status):
    return {"status": status, "family_id": "7", "qualified_family_id": "bigscape-gcf:v1/run/1/cutoff/0.3/family/7",
            "n_strains": 2, "mibig": [], "nearest_mibig": None, "cross_strain_members": []}


def test_card_text_scopes_absence_to_the_loaded_panel():
    text = _load().render_block(_ctx("NO_MIBIG_MEMBER"))
    assert "NOVEL" not in text
    assert "reference panel loaded for this run" in text
    assert "no characterized analog at this cutoff" not in text


def test_unknown_status_says_unknown():
    text = _load().render_block(_ctx("UNKNOWN"))
    assert "unknown in the supplied export" in text
