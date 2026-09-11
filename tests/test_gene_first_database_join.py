"""Generic sequence, geometry, history and pin mutation checks."""
import csv
import hashlib
import json
import sqlite3
import zlib
from pathlib import Path

import pytest
from tests import test_tool_database_reader as fixtures
from mamey.mode_b.gene_first_database import ADAPTERS
from mamey.mode_b.gene_first_explore import run_gene_first_exploration, GeneFirstHold

ID = ("TEST-1", "contig_complete_001", "region001", "BGC001")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(package, selection):
    manifest = json.loads((package / "manifest.json").read_text())
    manifest["files"] = [{"path": p.name, "sha256": digest(p)} for p in package.iterdir() if p.name != "manifest.json"]
    (package / "manifest.json").write_text(json.dumps(manifest))
    if selection.exists():
        s = json.loads(selection.read_text()); s["package_manifest_sha256"] = digest(package / "manifest.json")
        selection.write_text(json.dumps(s))


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "ID", ID); monkeypatch.setattr(fixtures, "DISPLAY", " / ".join(ID))
    package = tmp_path / "package"; package.mkdir()
    genes = [{"bgc_id": ID[3], "locus_tag": "gene"+str(i), "contig": ID[1], "aa_length": 200,
              "cds_start": 1, "cds_end": 600, "strand": "+", "product_qualifier": "",
              "gene_function_inference": "", "sec_met_domains": ""} for i in range(4)]
    with (package / "genes_gene_by_gene_all_bgcs.csv").open("w", newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(genes[0]));w.writeheader();w.writerows(genes)
    (package / (ID[0]+"_proteins.faa")).write_text("".join(f">gene{i} bgc={ID[3]}\n"+aa*200+"\n" for i,aa in enumerate("MCDE")))
    (package / "manifest.json").write_text(json.dumps({"strain_id":ID[0],"bgcs":[{"bgc_id":ID[3],"contig":ID[1],"region_number":1,"start":0,"end":600}]}))
    selection=tmp_path/"selection.json"
    pins={}
    for channel, adapter in ADAPTERS.items():
        root=tmp_path/channel
        if channel=="census":fixtures.fixture_db(root)
        else:fixtures.blastp_fixture(root,adapter)
        c=sqlite3.connect(root/"evidence.sqlite")
        if channel=="census":
            c.execute("ALTER TABLE locus ADD COLUMN region_start_1based INTEGER DEFAULT 1")
            c.execute("ALTER TABLE locus ADD COLUMN region_end_1based INTEGER DEFAULT 600")
            c.execute("UPDATE gene SET cds_end=600,protein_length=200,hold=NULL")
            for i,aa in enumerate("MCD"):
                c.execute("UPDATE gene SET protein_sha256=? WHERE locus_tag=?",(hashlib.sha256((aa*200).encode()).hexdigest(),"gene"+str(i)))
        else:
            if channel=="local_swissprot":c.execute("UPDATE binding SET binding_state='SEQUENCE_BOUND_CURRENT_LOCUS_PROJECTION'")
            for table in [x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
                if "query_sha256" in [x[1] for x in c.execute('PRAGMA table_info("'+table+'")')]:
                    for old,aa in zip("abc","MCD"):
                        c.execute('UPDATE "'+table+'" SET query_sha256=? WHERE query_sha256=?',(hashlib.sha256((aa*200).encode()).hexdigest(),old*64))
        c.commit();c.close()
        if channel=="census":fixtures.update_manifest(root)
        else:fixtures.blastp_manifest(root,adapter)
        pins[channel]={"root":channel,"manifest":"RELEASE_MANIFEST.json","manifest_sha256":digest(root/"RELEASE_MANIFEST.json")}
    selection.write_text(json.dumps({"schema":"mamey.gene-first-database-selection/1","databases":pins}))
    seal(package,selection)
    return tmp_path,package,selection


def run(case,**kw):
    root,package,selection=case
    return run_gene_first_exploration(package=package,strain=ID[0],full_node=ID[1],region=ID[2],bgc_alias=ID[3],out=root,database_selection=selection,**kw)


def test_conservation_separate_channels_complete_mixed_history(case):
    receipt=run(case); bridge=receipt["database_bridge"]
    assert receipt["gene_count"]==4 and len(bridge["genes"])==12
    rows={(x["gene"],x["channel"]):x for x in bridge["genes"]}
    assert rows["gene0","nr"]["state"]=="VERIFIED_MIXED_OUTCOMES"
    assert [x["search_id"] for x in rows["gene0","nr"]["search_history"]]==[1,2]
    assert rows["gene0","nr"]["search_history"][1]["representative"] is None
    assert rows["gene0","local_swissprot"]["state"]=="VERIFIED_HITS"
    assert all(rows["gene3",ch]["state"]=="UNAVAILABLE_IN_SELECTED_DATABASE" for ch in ADAPTERS if ch!="census")
    assert "never searched" not in bridge["rendered_markdown"].lower()
    assert all(sum(counts.values())==4 for counts in bridge["channel_tallies"].values())


@pytest.mark.parametrize("target",["package","database","manifest"])
def test_mutated_pins_hold_before_output(case,target):
    root,package,selection=case
    p={"package":package/"TEST-1_proteins.faa","database":root/"nr/evidence.sqlite","manifest":root/"nr/RELEASE_MANIFEST.json"}[target]
    with p.open("ab") as f:f.write(b" ")
    with pytest.raises(GeneFirstHold):run(case)
    assert not (root/"__".join(ID)).exists()


@pytest.mark.parametrize("mutation,state",[("sequence","PACKAGE_SEQUENCE_UNBOUND"),("geometry","PACKAGE_GENE_GEOMETRY_UNBOUND")])
def test_same_tag_changed_sequence_or_geometry_preserved_unbound(case,mutation,state):
    root,package,selection=case
    if mutation=="sequence":
        p=package/"TEST-1_proteins.faa";p.write_text(p.read_text().replace("M"*200,"A"*200))
    else:
        p=package/"genes_gene_by_gene_all_bgcs.csv";p.write_text(p.read_text().replace(",1,600,+,",",2,600,+,"))
    seal(package,selection)
    bridge=run(case)["database_bridge"]
    assert [g for g in bridge["genes"] if g["gene"]=="gene0" and g["state"]==state]
    assert len(bridge["genes"])==12


def test_empty_roster_refused(case):
    root,package,selection=case;p=package/"genes_gene_by_gene_all_bgcs.csv";p.write_text(p.read_text().splitlines()[0]+"\n");seal(package,selection)
    with pytest.raises(GeneFirstHold,match="no gene rows"):run(case)


def test_channel_conflict_refused(case):
    root,package,selection=case;s=json.loads(selection.read_text());s["databases"]["nr"]=s["databases"]["clusterednr"];selection.write_text(json.dumps(s))
    with pytest.raises(GeneFirstHold,match="VARIANT_MISMATCH"):run(case)


def test_duplicate_protein_refused(case):
    root,package,selection=case;p=package/"TEST-1_proteins.faa";p.write_text(p.read_text()+">gene0\nM\n");seal(package,selection)
    with pytest.raises(GeneFirstHold,match="DUPLICATE_OR_EMPTY"):run(case)


def test_rank_is_per_search_and_raw_coverage_not_relabeled(case):
    root,package,selection=case;c=sqlite3.connect(root/"nr/evidence.sqlite")
    e=json.loads(zlib.decompress(c.execute("SELECT all_evidence_zlib FROM hit").fetchone()[0]));e["source_rank"]=7;e["query_union_coverage_pct"]=109.45
    c.execute("UPDATE hit SET source_rank=7,all_evidence_zlib=?",(zlib.compress(json.dumps(e).encode()),));c.commit();c.close();fixtures.blastp_manifest(root/"nr","blastp-nr-v1")
    s=json.loads(selection.read_text());s["databases"]["nr"]["manifest_sha256"]=digest(root/"nr/RELEASE_MANIFEST.json");selection.write_text(json.dumps(s))
    bridge=run(case)["database_bridge"];row=next(g for g in bridge["genes"] if g["gene"]=="gene0" and g["channel"]=="nr")
    representative=row["search_history"][0]["representative"]
    assert representative["source_rank"]==7 and representative["query_union_coverage_pct"]==109.45
    assert "not reference coverage or percent identity" in bridge["rendered_markdown"]


def test_region_boundary_change_refused(case):
    root,package,selection=case;p=package/"manifest.json";m=json.loads(p.read_text());m["bgcs"][0]["start"]=1;p.write_text(json.dumps(m));seal(package,selection)
    with pytest.raises(GeneFirstHold,match="REGION_GEOMETRY"):run(case)


def test_external_index_conflicts_with_selected_database_channels(case):
    root,package,selection=case;p=root/"index.tsv"
    with p.open("w",newline="") as f:
        w=csv.writer(f,delimiter="\t");w.writerow(["channel","strain","full_node","region","bgc_alias","gene","evidence_state","source_locator","source_sha256","note"])
        w.writerow(["nr",*ID,"gene0","UNBOUND","","","external"])
    with pytest.raises(GeneFirstHold,match="DATABASE_INDEX_CHANNEL_CONFLICT"):run(case,evidence_index=p)


def test_whole_locus_missing_is_not_never_searched(case):
    root,package,selection=case
    for channel,adapter in ADAPTERS.items():
        if channel=="census":continue
        c=sqlite3.connect(root/channel/"evidence.sqlite");c.execute("DELETE FROM partition");c.execute("DELETE FROM binding");c.commit();c.close()
        fixtures.blastp_manifest(root/channel,adapter)
    s=json.loads(selection.read_text())
    for channel in ADAPTERS:s["databases"][channel]["manifest_sha256"]=digest(root/channel/"RELEASE_MANIFEST.json")
    selection.write_text(json.dumps(s))
    bridge=run(case)["database_bridge"]
    assert len(bridge["genes"])==12
    assert {g["state"] for g in bridge["genes"]}=={"UNAVAILABLE_IN_SELECTED_DATABASE"}
