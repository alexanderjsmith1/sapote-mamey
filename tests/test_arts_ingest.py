"""arts-ingest (M7): ARTS2 tables -> per-BGC self-resistance lead-priority signal. Hermetic."""
import importlib.util, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("arts_ingest", ROOT/"tools"/"arts_ingest.py")
ai = importlib.util.module_from_spec(_s); _s.loader.exec_module(ai)

def _write(d):
    t = Path(d)/"tables"; t.mkdir(parents=True)
    (t/"bgctable.tsv").write_text(
        "#Cluster\tType\tSource\tLocation\tCore hits\tOther hits\tGenelist\n"
        "cluster-6_1\tNRPS\tscaffold_6\t0 - 5000\t1\t0\t"
        "[['1','TIGR01048',100,200,'Core','lysA: diaminopimelate decarboxylase','Amino acid biosynthesis']]\n")
    (t/"coretable.tsv").write_text(
        "#Core_gene\tDescription\tFunction\tDuplication\tBGC_Proximity\tPhylogeny\tKnown_target\n"
        "TIGR01048\tlysA\tAmino acid\tYes\tYes\t-\t-\n")
    (t/"duptable.tsv").write_text(
        "#Core_gene\tCount\tRef_median\tRef_stdev\tRef_RSD\tRef_ubiquity\t[Hits]\tDescription\n"
        "TIGR01048\t2.0\t1.0\t0.4\t0.7\t0.9\t[..]\tlysA\n")
    (t/"knownhits.tsv").write_text(
        "#Model\tDescription\tSequence id\tevalue\tbitscore\tSequence description\n"
        "RF0002\tAAC3\t6296\t1e-53\t179\tlcl|x\n")

def test_self_resistance_lead_and_mapping():
    with tempfile.TemporaryDirectory() as d:
        _write(d)
        per_bgc, summary = ai.analyze(d, strain="AS-TEST")
        assert summary["n_bgc_with_arts_hits"] == 1
        assert summary["n_self_resistance_leads"] == 1          # lysA is dup + BGC-proximal
        assert summary["n_knownhits"] == 1
        assert per_bgc[0]["node"] == "NODE_6" and per_bgc[0]["region"] == "region001"
