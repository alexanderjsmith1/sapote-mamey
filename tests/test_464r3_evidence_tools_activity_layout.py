"""The activity adapter records its fixed layout as a template assumption, not an observed condition."""
import importlib.util
import json
from pathlib import Path
import pytest

TOOL = Path(__file__).parents[1] / "tools" / "bioassay_to_activity_channel.py"
spec = importlib.util.spec_from_file_location("bioassay_to_activity_channel_464r3", TOOL)
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)


def _csv(tmp_path, header="strain_id,organism,screening_pattern,max_inhibition_raw"):
    path = tmp_path / "screen.csv"
    path.write_text(header + "\nEXAMPLE,Target alpha,STRONG_DOSE_CONSISTENT,92.5\n")
    return path


def test_undeclared_layout_is_a_hold_and_template_basis_is_stated(tmp_path):
    assay = tool.build(_csv(tmp_path))["EXAMPLE"]["assays"][0]
    assert assay["layout_declaration_state"] == "UNDECLARED_HOLD_LAYOUT_ASSUMED_FROM_TEMPLATE"
    assert assay["doses_ugml_basis"] == "ADAPTER_TEMPLATE_NOT_READ_FROM_INPUT"
    assert assay["assay_label_basis"] == "ADAPTER_TEMPLATE_NOT_READ_FROM_INPUT"
    assert assay["template_dose_columns_state"] == "TEMPLATE_DOSE_COLUMNS_ABSENT"


def test_declared_layout_is_recorded_but_not_called_verified(tmp_path):
    out = tmp_path / "out"
    assert tool.main(["--recon", str(_csv(tmp_path)), "--out", str(out),
                      "--declare-layout", "fraction_screen_multidose_48h"]) == 0
    obj = json.loads((out / "EXAMPLE_bioactivity_metadata.json").read_text())
    assert obj["assays"][0]["layout_declaration_state"] == "OPERATOR_DECLARED_NOT_SOFTWARE_VERIFIED"
    assert any(w.startswith("LAYOUT_TEMPLATE_NOT_VERIFIED") for w in obj["warnings"])
    assert json.loads((out / "MANIFEST.json").read_text())["layout_declaration_state"] == \
        "OPERATOR_DECLARED_NOT_SOFTWARE_VERIFIED"


def test_other_layout_declaration_is_refused(tmp_path):
    with pytest.raises(ValueError, match="handles only"):
        tool.build(_csv(tmp_path), declared_layout="other_layout")


def test_output_still_passes_the_metadata_validator(tmp_path):
    from mamey.bioactivity_metadata import normalize_bioactivity
    normalize_bioactivity(tool.build(_csv(tmp_path))["EXAMPLE"])
