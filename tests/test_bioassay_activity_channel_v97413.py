"""BC4 .413 — tools/bioassay_to_activity_channel.py emits engine-admissible, claim-safe measured bioactivity."""
import csv, importlib.util, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "bioassay_to_activity_channel.py")


def _load_tool():
    spec = importlib.util.spec_from_file_location("b2ac", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def _tiny_recon(tmp_path):
    p = tmp_path / "recon.csv"
    cols = ["fractionation_event_id","culture_batch_id","strain_id","fraction_sample_key","fraction_plate_num",
            "source_96_well","fraction_label","organism","inhibition_120ug_ml","inhibition_60ug_ml",
            "inhibition_30ug_ml","inhibition_15ug_ml","concentration_count","max_inhibition_raw",
            "concentrations_at_or_above_50pct","concentrations_at_or_above_80pct","spearman_concentration_response",
            "max_lower_dose_inversion_pp","screening_pattern","screening_priority","pattern_is_biological_replication",
            "analysis_group","host","location","genus_16s","paper_analysis_include","raw_source_file","raw_source_sheet"]
    rows = [
        # AS-T1: a credible dose-consistent hit -> MEASURED_POSITIVE
        dict(strain_id="AS-T1", fraction_sample_key="FP001-A1", fraction_plate_num="1", source_96_well="A1",
             fraction_label="F1", organism="MRSA", inhibition_120ug_ml="100.5", inhibition_60ug_ml="80.0",
             inhibition_30ug_ml="40.0", inhibition_15ug_ml="20.0", max_inhibition_raw="100.5",
             concentrations_at_or_above_50pct="2", spearman_concentration_response="1.0",
             screening_pattern="STRONG_DOSE_CONSISTENT"),
        # AS-T2: screened, nothing credible -> MEASURED_NEGATIVE
        dict(strain_id="AS-T2", fraction_sample_key="FP002-B2", fraction_plate_num="2", source_96_well="B2",
             fraction_label="F2", organism="E. coli", inhibition_120ug_ml="8.0", inhibition_60ug_ml="4.0",
             inhibition_30ug_ml="2.0", inhibition_15ug_ml="1.0", max_inhibition_raw="8.0",
             concentrations_at_or_above_50pct="0", spearman_concentration_response="1.0",
             screening_pattern="NO_50PCT_OBSERVATION"),
    ]
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in cols})
    return str(p)


def test_objects_are_admitted_by_engine_and_claim_safe(tmp_path):
    tool = _load_tool()
    objs = tool.build(_tiny_recon(tmp_path))
    assert set(objs) == {"AS-T1", "AS-T2"}
    # engine admission gate
    from mamey.bioactivity_metadata import normalize_bioactivity
    for s, o in objs.items():
        normalize_bioactivity(o)  # raises if not admissible
        assert o["schema_version"] == "bioactivity_metadata_v1"
        assert o["usage_scope"] == "PRODUCTION"
        assert o["compound_linkage"] == "NOT_ESTABLISHED"      # never links a compound/BGC
        assert isinstance(o["assays"], list) and o["assays"]
        assert o["warnings"], "screening-not-validated caveat must travel with the data"
        # claim-safety: no BGC / cluster attribution anywhere in the assays
        blob = str(o["assays"]).lower()
        assert "bgc" not in blob and "cluster" not in blob and "region" not in blob
    assert objs["AS-T1"]["metadata_state"] == "MEASURED_POSITIVE"
    assert objs["AS-T2"]["metadata_state"] == "MEASURED_NEGATIVE"


def test_min_hit_threshold_controls_positive(tmp_path):
    tool = _load_tool()
    # raise threshold above the 100.5 hit -> still POSITIVE only if tier credible AND >= min_hit
    objs = tool.build(_tiny_recon(tmp_path), min_hit=101.0)
    assert objs["AS-T1"]["metadata_state"] == "MEASURED_NEGATIVE"


def test_af_dossier_shape(tmp_path):
    tool = _load_tool()
    rows = tool.build_af_dossier(_tiny_recon(tmp_path))
    by = {r["strain"]: r for r in rows}
    assert set(by["AS-T1"]) == {"strain", "anti_Candida", "anti_MRSA", "host", "genus"}
    assert by["AS-T1"]["anti_MRSA"] == "positive"      # credible MRSA hit
    assert by["AS-T1"]["anti_Candida"] == "negative"   # no candida row
    assert by["AS-T2"]["anti_MRSA"] == "negative"
