"""Native handoff scope and the user-facing exception contract; synthetic bytes only."""
from pathlib import Path
import csv,zipfile
import pytest
from mamey.handoff import build_handoff
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize("case",["all_blank","no_crosswalk","partial_crosswalk"])
def test_handoff_scope_exception_is_documented(tmp_path,case):
    package=tmp_path/"package";package.mkdir()
    with (package/"fixture_4_triage_board.csv").open("w",newline="") as f:
        writer=csv.writer(f);writer.writerow(["BGC_ID","Corrected_rank","Rank"])
        writer.writerows([["BGC001","" if case=="all_blank" else "1","1"],["BGC002","" if case=="all_blank" else "2","2"]])
    if case!="no_crosswalk":
        with (package/"fixture_2b_bgc_crosswalk.csv").open("w",newline="") as f:
            writer=csv.writer(f);writer.writerow(["bgc_id","source_gbk"]);writer.writerow(["BGC001","SYNTHETIC_1.region001.gbk"])
    source=tmp_path/"source.zip"
    with zipfile.ZipFile(source,"w") as archive:
        for i in (1,2,3):archive.writestr(f"SYNTHETIC_{i}.region001.gbk",f"nonbiological fixture {i}")
    output=tmp_path/"handoff.zip";result=build_handoff(package,source,output,top_n=2)
    with zipfile.ZipFile(output) as archive:members=[v for v in archive.namelist() if v.startswith("region_gbks/")]
    page=" ".join((ROOT/"docs/FILES_STORAGE_AND_HANDOFF.md").read_text().split())
    if case=="all_blank":
        assert result["selected_bgcs"]==[] and len(members)==3
        assert "including when no IDs were selected" in page
    elif case=="no_crosswalk":
        assert result["selected_bgcs"]==["BGC001","BGC002"] and len(members)==3
        assert "falls back to all region GBKs" in page
    else:
        assert result["selected_bgcs"]==["BGC001","BGC002"] and len(members)==1
        assert "With a partial crosswalk it includes only mapped selected regions and can omit the others" in page
