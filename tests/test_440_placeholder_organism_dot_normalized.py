"""A FASTA-submitted region GBK carries `ORGANISM  .` (truthy '.'), not a blank. detect_and_stage
must normalise that to None so the taxonomy fallback engages; otherwise the engine is handed "."
and rejects the whole FASTA cohort. Black Cherry 2 / session 88fdad06, v9.7.440."""
import importlib.util, sys, zipfile
from pathlib import Path
BUNDLE = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(BUNDLE))
spec = importlib.util.spec_from_file_location("ih_uut", BUNDLE/"tools"/"intake_harness.py")
ih = importlib.util.module_from_spec(spec); spec.loader.exec_module(ih)
from mamey.cohort_resolver import is_placeholder_taxonomy

GBK = """LOCUS       NODE_1  1000 bp    DNA     linear   UNK
DEFINITION  NODE_1_length_1000_cov_1.0.
SOURCE      .
  ORGANISM  .
FEATURES             Location/Qualifiers
     region          1..1000
                     /product="terpene"
ORIGIN
//
"""

def _zip(tmp):
    z = tmp/"AS-TEST.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("AS-TEST/NODE_1.region001.gbk", GBK)
    return z

def test_dot_organism_is_normalized_to_none(tmp_path):
    kind, izip, cb, organism = ih.detect_and_stage(str(_zip(tmp_path)), str(tmp_path/"stage"), "AS-TEST")
    assert kind == "ANTISMASH"
    assert organism is None, f"'.' ORGANISM must normalise to None, got {organism!r}"

def test_resolved_taxonomy_is_accepted_by_the_engine(tmp_path):
    _, _, _, organism = ih.detect_and_stage(str(_zip(tmp_path)), str(tmp_path/"stage"), "AS-TEST")
    tax = organism or "not verified"
    assert not is_placeholder_taxonomy(tax), f"harness would pass {tax!r}, which the engine rejects"
    assert tax == "not verified"
