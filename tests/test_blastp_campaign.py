"""blastp_campaign: hermetic tests for the pure parse functions (no NCBI calls)."""
import importlib.util, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("blastp_campaign", ROOT/"tools"/"blastp_campaign.py")
bc = importlib.util.module_from_spec(_s); _s.loader.exec_module(bc)

def test_parse_faa_locus_from_header():
    with tempfile.NamedTemporaryFile("w", suffix=".faa", delete=False) as f:
        f.write(">AS-932|BGC005|slot=1|role=core|gene=ctg12_56|node=NODE_12|region=region002|aa=406|reason=p450\nMKTAYIAKQR\n")
        f.write(">AS-678|BGC014|slot=2|role=context|gene=ctg2_256|aa=229|reason=tetr\nMQERLVK\n")
        path = f.name
    prots = bc._parse_faa(path)
    assert prots[0][0] == "AS-932|BGC005|ctg12_56" and prots[0][1] == "MKTAYIAKQR"
    assert prots[1][0] == "AS-678|BGC014|ctg2_256"

def test_top_hits_parses_identity_and_sciname():
    xml = ("<Hit><Hit_def>cytochrome P450 family protein [Nocardia uniformis]</Hit_def>"
           "<Hsp_bit-score>768.0</Hsp_bit-score><Hsp_evalue>0</Hsp_evalue>"
           "<Hsp_identity>371</Hsp_identity><Hsp_align-len>399</Hsp_align-len></Hit>")
    hits = bc._top_hits(xml, top_n=3)
    assert len(hits) == 1
    assert hits[0]["sciname"] == "Nocardia uniformis"
    assert hits[0]["pct_identity"] == round(100*371/399, 1)   # 93.0
    assert "cytochrome P450" in hits[0]["subject_desc"]
