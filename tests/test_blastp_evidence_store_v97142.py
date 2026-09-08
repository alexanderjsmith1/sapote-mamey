import csv
from pathlib import Path

import pytest

from mamey.blastp_evidence_store import ingest_blastp_round, rebuild_cumulative_tables, sha256_file


def _write_hit(path: Path, query: str, subject: str, title_safe_subject="WP_1.1"):
    path.write_text(f"{query},{subject},99.0,100,1,0,1,100,1,100,0.0,200,99.0\n", encoding="utf-8")


def test_store_preserves_raw_files_and_writes_manifest(tmp_path):
    q = "AS168|BGC019|ctg26_64|aa=100|products=RRE-containing;_RiPP;_azole-containing-RiPP"
    hit = tmp_path / "hit.csv"
    _write_hit(hit, q, "WP_412103922.1")
    xml = tmp_path / "x.xml"
    xml.write_text("""<?xml version="1.0"?><BlastXML2 xmlns="http://www.ncbi.nlm.nih.gov"><BlastOutput2><report><Report><results><Results><search><Search><query-title>AS168|BGC019|ctg26_64|aa=100|products=RRE-containing;_RiPP;_azole-containing-RiPP</query-title><query-len>100</query-len><hits><Hit><description><HitDescr><id>WP_412103922.1</id><accession>WP_412103922</accession><title>lantibiotic dehydratase [Streptomyces californicus]</title><taxid>67351</taxid><sciname>Streptomyces californicus</sciname></HitDescr></description><len>100</len><hsps><Hsp><bit-score>200</bit-score><evalue>0</evalue><identity>99</identity><positive>99</positive><align-len>100</align-len></Hsp></hsps></Hit></hits></Search></search></Results></results></Report></report></BlastOutput2></BlastXML2>""", encoding="utf-8")
    store = tmp_path / "store"
    summary = ingest_blastp_round(store, strain="AS168", round_id="RID1", hit_table_csv=hit, xml2=xml, purpose="test")
    assert summary["query_count"] == 1
    assert (store / "raw_ncbi_downloads" / "RID1" / "hit.csv").exists()
    assert (store / "raw_ncbi_downloads" / "RID1" / "x.xml").exists()
    import json
    manifest_rows = [json.loads(line) for line in (store / "BLASTP_round_manifest.jsonl").read_text().splitlines() if line.strip()]
    assert sum(1 for row in manifest_rows if row.get("round_id") == "RID1") == 1
    rows = list(csv.DictReader((store / "cumulative" / "BLASTP_top_hits_by_query_all_rounds.csv").open()))
    assert rows[0]["evidence_tier"] == "TIER_A_CLASS_DEFINING"
    assert rows[0]["next_action"] == "RETAIN_FOR_CLASS_PROOF_TABLE"


def test_store_rejects_duplicate_round_id_by_default(tmp_path):
    q = "AS168|BGC005|ctg13_34|aa=100|products=phosphonate"
    hit = tmp_path / "hit.csv"
    _write_hit(hit, q, "WP_229318425.1")
    store = tmp_path / "store"
    ingest_blastp_round(store, strain="AS168", round_id="RID_DUP", hit_table_csv=hit)
    with pytest.raises(ValueError):
        ingest_blastp_round(store, strain="AS168", round_id="RID_DUP", hit_table_csv=hit)


def test_store_allow_update_replaces_round_without_duplicate_manifest(tmp_path):
    q = "AS168|BGC005|ctg13_34|aa=100|products=phosphonate"
    hit = tmp_path / "hit.csv"
    _write_hit(hit, q, "WP_229318425.1")
    store = tmp_path / "store"
    ingest_blastp_round(store, strain="AS168", round_id="RID_UPD", hit_table_csv=hit)
    ingest_blastp_round(store, strain="AS168", round_id="RID_UPD", hit_table_csv=hit, allow_update=True)
    import json
    manifest_rows = [json.loads(line) for line in (store / "BLASTP_round_manifest.jsonl").read_text().splitlines() if line.strip()]
    assert sum(1 for row in manifest_rows if row.get("round_id") == "RID_UPD") == 1


def test_store_rebuilds_cumulative_bgc_summary_across_rounds(tmp_path):
    store = tmp_path / "store"
    hit1 = tmp_path / "hit1.csv"; hit2 = tmp_path / "hit2.csv"
    _write_hit(hit1, "AS168|BGC005|ctg13_34|aa=100|products=phosphonate", "WP_A.1")
    _write_hit(hit2, "AS168|BGC019|ctg26_64|aa=100|products=RiPP", "WP_B.1")
    ingest_blastp_round(store, strain="AS168", round_id="R1", hit_table_csv=hit1)
    ingest_blastp_round(store, strain="AS168", round_id="R2", hit_table_csv=hit2)
    rows = list(csv.DictReader((store / "cumulative" / "BLASTP_BGC_summary_all_rounds.csv").open()))
    assert {r["bgc_id"] for r in rows} == {"BGC005", "BGC019"}
    assert (store / "README_BLASTP_EVIDENCE_STORE.md").exists()
