"""Constructed material identity/level and denominator controls; no biological data."""
import csv
import pytest
from mamey.evidence_registry import REQUIRED_HEADERS,validate_evidence_registry,EvidenceRegistryError

def row(rid,kind="material",mid="SYN-MAT-1",level="crude_extract",strain="SYNTHETIC-CASE-ONE"):
    r=dict.fromkeys(REQUIRED_HEADERS,"SYNTHETIC-NOT-APPLICABLE")
    r.update(record_id=rid,strain_id=strain,material_id=mid,parent_material_id="ROOT",preparation_event_id=mid,evidence_type=kind,material_level=level,assay_state="NOT_SCREENED",source_locator="evidence://synthetic/"+rid,claim_ceiling="Availability only; no assay result")
    return r

def validate(tmp_path,rows):
    path=tmp_path/"synthetic_registry.tsv"
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=REQUIRED_HEADERS,delimiter="\t");w.writeheader();w.writerows(rows)
    return validate_evidence_registry(path)

def test_assay_cannot_relabel_crude_material_as_hplc(tmp_path):
    with pytest.raises(EvidenceRegistryError,match="assay material_level"):
        validate(tmp_path,[row("material"),row("assay",kind="assay",level="hplc_fraction")])

def test_same_strain_does_not_supply_missing_material(tmp_path):
    with pytest.raises(EvidenceRegistryError,match="no material record"):
        validate(tmp_path,[row("material"),row("assay",kind="assay",mid="SYN-MAT-ABSENT")])

def test_denominators_count_explicit_records_and_materials(tmp_path):
    rows=[row("genome1",kind="genome",mid="SYN-ASSEMBLY-1",level="genome"),row("genome2",kind="genome",mid="SYN-ASSEMBLY-2",level="genome"),row("material1"),row("material2",mid="SYN-MAT-2"),row("assay1",kind="assay"),row("assay2",kind="assay",mid="SYN-MAT-2"),row("material3",mid="SYN-MAT-3",strain="SYNTHETIC-CASE-TWO")]
    result=validate(tmp_path,rows)
    assert (result["record_count"],result["strain_count"],result["material_count"],result["assay_record_count"])==(7,2,3,2)
    assert result["by_strain"]["SYNTHETIC-CASE-ONE"]["genome"]==2
    assert "do not establish activity" in result["claim_ceiling"]
