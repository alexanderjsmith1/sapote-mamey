from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
from mamey.phylo_evidence import PHYLO_EVIDENCE_SCHEMA
import pytest

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow
ROOT=Path(__file__).parents[1]
CLI=ROOT/"tools"/"figure_factory_next.py"
def item(path,root): return {"logical_locator":path.relative_to(root).as_posix(),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
def write(root,name,text):
    p=root/name;p.write_text(text,encoding="utf-8");return item(p,root)
def evidence(root,name,tree,roster_tips="A\nB\nOUT\n",signoff_status="PASS"):
    tool,version,model,seed,out="iqtree","3.0","MFP","12345","OUT"
    tree_item=write(root,name+".tree",tree);alignment_item=write(root,name+".aln",">x\nAAAA\n")
    roster=roster_tips.strip().splitlines()
    fixture_strains={"A":"DEMO-001","B":"REF-001","C":"REF-002","OUT":"OUT-001"}
    join_rows=[{"tree_tip":tip,"canonical_tip":tip,"role":"REFERENCE","strain_id":fixture_strains.get(tip,tip),"manifest_sha256":None,"host_label":"","host_provenance":"NOT_APPLICABLE_REFERENCE"} for tip in roster]
    signoff={"schema_version":PHYLO_EVIDENCE_SCHEMA,"status":signoff_status,"tree_sha256":tree_item["sha256"],"alignment_sha256":alignment_item["sha256"],"outgroup_tip":out,"gtotree":{"name":"GToTree","version":"2.0.0","sha256":"1"*64},"iqtree":{"name":"IQ-TREE","version":"3.1.2","sha256":"2"*64},"marker_set":{"name":"Actinobacteria 138-SCG","count":138,"sha256":"3"*64},"outgroup_registry":{"row_sha256":"4"*64},"support":{"label":"SH-aLRT/UFBoot","node_count":2},"reference_dedup":{"state":"ONE_PER_SPECIES","species_column":"species","kept":3,"dropped":0},"n_tips":len(roster),"assembly_quality_flags":[],"comparator_provenance":{"status":"PASS"},"package_tree_join":{"crosswalk_sha256":"5"*64,"host_table_sha256":"6"*64,"host_table_sheet":None,"rows":join_rows}}
    return {"tree":tree_item,"alignment":alignment_item,"tool_receipt":write(root,name+".tool","{}\n"),"signoff_receipt":write(root,name+".signoff",json.dumps(signoff)+"\n"),"roster":write(root,name+".roster","tree_tip\n"+roster_tips),"tool_name":tool,"tool_version":version,"tool_sha256":hashlib.sha256((tool+"\n"+version).encode()).hexdigest(),"model":model,"model_sha256":hashlib.sha256(model.encode()).hexdigest(),"seed":seed,"seed_sha256":hashlib.sha256(seed.encode()).hexdigest(),"outgroup_tip":out,"outgroup_sha256":hashlib.sha256(out.encode()).hexdigest()}
def track(root,channel): return {"channel":channel,**write(root,channel+".tsv","strain_id\tfeature_id\tcount\tcount_missingness\nDEMO-001\tfeatureA\t1\tPRESENT\nREF-001\tfeatureA\t0\tPRESENT\nOUT-001\tavailability\t\tNOT_RUN\n")}
def test_track_adapter_is_hash_bound_and_tree_build_free(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_annotation_tracks_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO001","tree_evidence":evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);"),"tip_strain_crosswalk":write(ext,"cross.tsv","tree_tip\tstrain_id\ttip_missingness\tstrain_missingness\nA\tDEMO-001\tPRESENT\tPRESENT\nB\tREF-001\tPRESENT\tPRESENT\nOUT\tOUT-001\tPRESENT\tPRESENT\n"),"tracks":[track(ext,c) for c in ("BGC_ANNOTATION","DOMAIN","CASSETTE","ANI","MODEB_JUDGMENT")]}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    receipt=json.loads((tmp_path/"out"/"FFPHYLO001_phylogeny_figure_factory_receipt.json").read_text())
    assert receipt["status"]=="PASS_FIGURE_FACTORY_DATA_READY" and receipt["tip_count"]==3
def test_concordance_reports_sampling_not_topology(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    rows=[("MLSA","A","DEMO-001","SHARED"),("MLSA","B","REF-001","MLSA_ONLY"),("MLSA","OUT","OUT-001","SHARED"),("CORE_GENOME","A","DEMO-001","SHARED"),("CORE_GENOME","C","REF-002","CORE_GENOME_ONLY"),("CORE_GENOME","OUT","OUT-001","SHARED")]
    cross="tree_kind\ttree_tip\tstrain_id\ttip_missingness\tstrain_missingness\tdisposition\treason\n"+"".join("\t".join((r[0],r[1],r[2],"PRESENT","PRESENT",r[3],"CURATED_ROSTER"))+"\n" for r in rows)
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_shared_tip_concordance_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"diagnostic_id":"FFPHYLO002","mlsa_tree_evidence":evidence(ext,"mlsa","((A:0.1,B:0.1):0.2,OUT:0.3);"),"core_tree_evidence":evidence(ext,"core","((A:0.1,C:0.1):0.2,OUT:0.3);","A\nC\nOUT\n"),"shared_tip_crosswalk":write(ext,"shared.tsv",cross)}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    receipt=json.loads((tmp_path/"out"/"FFPHYLO002_phylogeny_figure_factory_receipt.json").read_text())
    assert receipt["shared_tip_count"]==2 and receipt["mlsa_only_count"]==1 and receipt["core_genome_only_count"]==1
    assert "no topology-equivalence statistic" in (tmp_path/"out"/"FFPHYLO002_caption_methods.md").read_text()


def test_concordance_crosswalks_must_match_each_admitted_join(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    mlsa=evidence(ext,"mlsa","((A:0.1,B:0.1):0.2,OUT:0.3);")
    core=evidence(ext,"core","((A:0.1,C:0.1):0.2,OUT:0.3);","A\nC\nOUT\n")
    signoff=ext/core["signoff_receipt"]["logical_locator"]
    payload=json.loads(signoff.read_text())
    next(row for row in payload["package_tree_join"]["rows"] if row["tree_tip"]=="C")["strain_id"]="WRONG-002"
    signoff.write_text(json.dumps(payload)+"\n")
    core["signoff_receipt"]=item(signoff,ext)
    rows=[("MLSA","A","DEMO-001","SHARED"),("MLSA","B","REF-001","MLSA_ONLY"),("MLSA","OUT","OUT-001","SHARED"),("CORE_GENOME","A","DEMO-001","SHARED"),("CORE_GENOME","C","REF-002","CORE_GENOME_ONLY"),("CORE_GENOME","OUT","OUT-001","SHARED")]
    cross="tree_kind\ttree_tip\tstrain_id\ttip_missingness\tstrain_missingness\tdisposition\treason\n"+"".join("\t".join((r[0],r[1],r[2],"PRESENT","PRESENT",r[3],"CURATED_ROSTER"))+"\n" for r in rows)
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_shared_tip_concordance_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"diagnostic_id":"FFPHYLO011","mlsa_tree_evidence":mlsa,"core_tree_evidence":core,"shared_tip_crosswalk":write(ext,"shared.tsv",cross)}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==2
    assert "PHYLO_PACKAGE_TREE_JOIN_MISMATCH" in run.stderr
    assert not (tmp_path/"out"/"FFPHYLO011_shared_tip_concordance.tsv").exists()
def test_track_adapter_refuses_duplicate_crosswalk(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_annotation_tracks_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO003","tree_evidence":evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);"),"tip_strain_crosswalk":write(ext,"cross.tsv","tree_tip\tstrain_id\ttip_missingness\tstrain_missingness\nA\tDEMO-001\tPRESENT\tPRESENT\nB\tDEMO-001\tPRESENT\tPRESENT\nOUT\tOUT-001\tPRESENT\tPRESENT\n"),"tracks":[track(ext,c) for c in ("BGC_ANNOTATION","DOMAIN","CASSETTE","ANI","MODEB_JUDGMENT")]}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode!=0 and "one-to-one mapping" in run.stderr


def test_track_crosswalk_must_match_admitted_package_tree_join(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    ev=evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);")
    signoff=ext/ev["signoff_receipt"]["logical_locator"]
    payload=json.loads(signoff.read_text())
    payload["package_tree_join"]["rows"][0]["strain_id"]="WRONG-001"
    signoff.write_text(json.dumps(payload)+"\n")
    ev["signoff_receipt"]=item(signoff,ext)
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_annotation_tracks_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO010","tree_evidence":ev,"tip_strain_crosswalk":write(ext,"cross.tsv","tree_tip\tstrain_id\ttip_missingness\tstrain_missingness\nA\tDEMO-001\tPRESENT\tPRESENT\nB\tREF-001\tPRESENT\tPRESENT\nOUT\tOUT-001\tPRESENT\tPRESENT\n"),"tracks":[track(ext,c) for c in ("BGC_ANNOTATION","DOMAIN","CASSETTE","ANI","MODEB_JUDGMENT")]}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==2
    assert "PHYLO_PACKAGE_TREE_JOIN_MISMATCH" in run.stderr
    assert not (tmp_path/"out"/"FFPHYLO010_annotation_tracks.tsv").exists()


def test_failed_signoff_is_a_typed_refusal(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_evidence_receipt_widget_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO004","tree_evidence":evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);",signoff_status="FAIL")}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==2
    assert "PHYLO_SIGNOFF_HOLD" in run.stderr
    assert not (tmp_path/"out"/"FFPHYLO004_phylogeny_evidence_widget.html").exists()


def test_signoff_must_bind_the_exact_tree(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    ev=evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);")
    signoff=ext/ev["signoff_receipt"]["logical_locator"]
    payload=json.loads(signoff.read_text());payload["tree_sha256"]="0"*64;signoff.write_text(json.dumps(payload)+"\n")
    ev["signoff_receipt"]=item(signoff,ext)
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_evidence_receipt_widget_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO005","tree_evidence":ev}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==2 and "PHYLO_SIGNOFF_MISMATCH" in run.stderr


def test_evidence_widget_surfaces_phylogeny_provenance(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_evidence_receipt_widget_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO006","title":"Synthetic phylogeny evidence","tree_evidence":evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);")}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    widget=(tmp_path/"out"/"FFPHYLO006_phylogeny_evidence_widget.html").read_text()
    assert all(text in widget for text in ("Actinobacteria 138-SCG","SH-aLRT","UFBoot","Reference dedup","Assembly quality","Package/tree join","OUT","iqtree 3.0"))
    receipt=json.loads((tmp_path/"out"/"FFPHYLO006_phylogeny_figure_factory_receipt.json").read_text())
    assert receipt["status"]=="PASS_EVIDENCE_WIDGET_READY"
    assert receipt["outputs"][0]["bytes"]>0
    join=receipt["bound_inputs"]["tree_evidence"]["admitted_signoff"]["package_tree_join"]
    assert join["row_count"]==3 and join["reference_count"]==3


def test_package_tree_join_must_exactly_cover_admitted_tree(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    ev=evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);")
    signoff=ext/ev["signoff_receipt"]["logical_locator"]
    payload=json.loads(signoff.read_text())
    payload["package_tree_join"]["rows"][0]["tree_tip"]="NOT_IN_TREE"
    payload["package_tree_join"]["rows"][0]["canonical_tip"]="NOT_IN_TREE"
    signoff.write_text(json.dumps(payload)+"\n")
    ev["signoff_receipt"]=item(signoff,ext)
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_evidence_receipt_widget_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO008","tree_evidence":ev}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==2
    assert "PHYLO_PACKAGE_TREE_JOIN_INCOMPLETE" in run.stderr
    assert not (tmp_path/"out"/"FFPHYLO008_phylogeny_evidence_widget.html").exists()


def test_package_tree_join_rejects_untyped_package_provenance(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    ev=evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);")
    signoff=ext/ev["signoff_receipt"]["logical_locator"]
    payload=json.loads(signoff.read_text())
    row=payload["package_tree_join"]["rows"][0]
    row.update({"role":"PACKAGE","manifest_sha256":"7"*64,"host_label":"synthetic host","host_provenance":"UNVERIFIED"})
    signoff.write_text(json.dumps(payload)+"\n")
    ev["signoff_receipt"]=item(signoff,ext)
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_evidence_receipt_widget_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO009","tree_evidence":ev}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode==2
    assert "PHYLO_PACKAGE_TREE_JOIN_INVALID" in run.stderr
    assert not (tmp_path/"out"/"FFPHYLO009_phylogeny_evidence_widget.html").exists()


def test_duplicate_track_channel_is_refused(tmp_path):
    ext=tmp_path/"ext";ext.mkdir()
    tracks=[track(ext,c) for c in ("BGC_ANNOTATION","DOMAIN","CASSETTE","ANI","MODEB_JUDGMENT")]
    tracks.append({**tracks[0]})
    config={"schema_version":"sapote.phylogeny-figure-factory.v1","figure_kind":"phylogeny_annotation_tracks_v1","external_data_root":str(ext),"output_dir":str(tmp_path/"out"),"figure_id":"FFPHYLO007","tree_evidence":evidence(ext,"core","((A:0.1,B:0.1):0.2,OUT:0.3);"),"tip_strain_crosswalk":write(ext,"cross.tsv","tree_tip\tstrain_id\ttip_missingness\tstrain_missingness\nA\tDEMO-001\tPRESENT\tPRESENT\nB\tREF-001\tPRESENT\tPRESENT\nOUT\tOUT-001\tPRESENT\tPRESENT\n"),"tracks":tracks}
    cp=tmp_path/"cfg.json";cp.write_text(json.dumps(config))
    run=subprocess.run([sys.executable,str(CLI),"--config",str(cp)],capture_output=True,text=True)
    assert run.returncode!=0 and "exactly five unique" in run.stderr
