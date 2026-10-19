"""Named ambiguous contigs add review context, never rescue evidence or join geometry."""
from pathlib import Path
from copy import deepcopy
import sys,importlib.util,json,csv,hashlib,zipfile
import pytest
pytest.importorskip("matplotlib")
pytest.importorskip("Bio")
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"tools")]
import gap_rescue_locus_map as glm
import gap_directed_rescue as gdr

LABEL="SYN_REVIEW"
IDENTITY=LABEL+" / NODE_CONTEXT_FULL_123 / region002 / BGC002"

@pytest.fixture
def case():
    prot=lambda tag,ctg,start:dict(tag=tag,contig=ctg,start=start,end=start+300,strand=1,contig_len=7000,aa="M"+"A"*99)
    prots={"q1":prot("CORE_1","core",1000),"q2":prot("CTX_1","NODE_CONTEXT_FULL_123",2000),
           "q3":prot("CTX_2","NODE_CONTEXT_FULL_123",2500)}
    core=dict(contig="core",start=500,end=4000,identity=LABEL+" / core / region001 / BGC001")
    region=dict(contig="NODE_CONTEXT_FULL_123",start=1500,end=5000,identity=IDENTITY)
    rows=[dict(i=1,name="synA",status="PRESENT_IN_CORE",best_protein="q1",best_locus="CORE_1",best_identity_pct="80",reciprocal_best=True,partner_verdict=""),
          dict(i=2,name="synB",status="MISSING_FOUND_AMBIGUOUS",best_protein="q2",best_locus="CTX_1",best_identity_pct="45",reciprocal_best=False,partner_verdict="PARALOG_FAMILY"),
          dict(i=3,name="synC",status="MISSING_NOT_FOUND",best_protein="",best_locus="",best_identity_pct="",reciprocal_best=False,partner_verdict="")]
    return dict(prots=prots,core=core,regions=[core,region],rows=rows)

def select(case,ids=None):
    return glm.named_ambiguous_contexts([IDENTITY] if ids is None else ids,LABEL,case["prots"],case["regions"],case["rows"],[(0,"q1",80.)],"core")

def test_selection_preserves_ambiguous_rows_counts_and_models(case):
    before=deepcopy(case);counts=glm.count_summary(case["rows"])
    windows,records=select(case)
    assert list(windows)==["NODE_CONTEXT_FULL_123"]
    assert records[0]["identity"]==IDENTITY and records[0]["display_state"]=="AMBIGUOUS"
    assert records[0]["candidates"][0]["status"]=="MISSING_FOUND_AMBIGUOUS"
    assert records[0]["candidates"][0]["partner_verdict"]=="PARALOG_FAMILY"
    assert counts==glm.count_summary(case["rows"]) and case==before
    assert select(case,[])==({},[])

@pytest.mark.parametrize("bad",["NODE_CONTEXT_FULL_123",LABEL+" / NODE_CONTEXT / region002 / BGC002",IDENTITY.replace(LABEL,"OTHER"),
    IDENTITY.replace("region002","region999"),IDENTITY.replace("BGC002","IDENTITY_HOLD"),IDENTITY+" / extra"])
def test_incomplete_conflicting_or_shortened_identity_refused(case,bad):
    with pytest.raises(ValueError,match="NAMED_CONTIG_IDENTITY_HOLD"):select(case,[bad])

def test_duplicate_contig_refused(case):
    with pytest.raises(ValueError,match="DUPLICATE"):select(case,[IDENTITY,IDENTITY])

def test_conflicting_exact_region_records_refused(case):
    case["regions"].append(deepcopy(case["regions"][1]))
    with pytest.raises(ValueError,match="IDENTITY_HOLD"):select(case)

@pytest.mark.parametrize("change",["clear","missing_locus","wrong_locus","outside_region"])
def test_unknown_or_nonambiguous_candidate_cannot_be_promoted(case,change):
    if change=="clear":case["rows"][1]["status"]="MISSING_FOUND_CLEAR"
    elif change=="missing_locus":case["rows"][1]["best_locus"]=""
    elif change=="wrong_locus":case["rows"][1]["best_locus"]="DIFFERENT"
    else:case["prots"]["q2"].update(start=6000,end=6300)
    with pytest.raises(ValueError,match="NAMED_CONTIG_(EVIDENCE|PROTEIN_BINDING)_HOLD"):select(case)

def test_explicit_non_bgc_context_has_typed_absence_without_fake_alias(case):
    case["regions"]=case["regions"][:1]
    ident=LABEL+" / NODE_CONTEXT_FULL_123 / NO_ANTISMASH_REGION / NO_BGC_ALIAS"
    _,records=select(case,[ident])
    assert records[0]["identity_state"]=="NO_CALLED_REGION_IN_SUPPLIED_INPUT"
    case["regions"].append(dict(contig="NODE_CONTEXT_FULL_123",start=1500,end=5000,identity=IDENTITY))
    with pytest.raises(ValueError,match="has an antiSMASH region"):select(case,[ident])

def test_already_drawn_contig_is_not_duplicated(case):
    with pytest.raises(ValueError,match="ALREADY_DRAWN"):
        glm.named_ambiguous_contexts([IDENTITY],LABEL,case["prots"],case["regions"],case["rows"],[(0,"q1",80.),(1,"q2",45.)],"core")

@pytest.fixture
def saved_run(tmp_path,case):
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature,FeatureLocation
    from Bio import SeqIO
    refdir=tmp_path/"references";refdir.mkdir();ref=refdir/"BGC_SYN.gbk"
    record=SeqRecord(Seq("ATG"+"GCT"*499),id="SYN_REFERENCE",description="Synthetic comparator")
    record.annotations["molecule_type"]="DNA"
    for i,name in enumerate(["synA","synB","synC"]):
        record.features.append(SeqFeature(FeatureLocation(100+400*i,400+400*i,strand=1),type="CDS",qualifiers=dict(gene=[name],locus_tag=[name],translation=["M"+"A"*99],gene_kind=["biosynthetic"])))
    SeqIO.write(record,ref,"genbank")
    folder=tmp_path/"saved";folder.mkdir()
    (folder/"gap_rescue_receipt.json").write_text(json.dumps(dict(label=LABEL,core=case["core"]["identity"],reference=ref.name,reference_name="Synthetic comparator")))
    with (folder/"gap_rescue.tsv").open("w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(case["rows"][0]),delimiter="\t");w.writeheader();w.writerows(case["rows"])
    (folder/"gap_rescue_split_genes.tsv").write_text("reference_gene\tname\tsplit_call\n")
    archive=tmp_path/"synthetic_genome.zip"
    with zipfile.ZipFile(archive,"w") as z:z.writestr("FIXTURE_README.txt","Synthetic model constructed in the test; no historical search is claimed.")
    return folder,refdir,archive

def test_real_synthetic_redraw_adds_ambiguous_context_and_preserves_inputs(saved_run,case,tmp_path):
    PdfReader=pytest.importorskip("pypdf").PdfReader
    folder,refs,archive=saved_run;before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    model_before=deepcopy(case);counts=glm.count_summary(case["rows"])
    out=tmp_path/"review"
    rec=gdr.redraw(folder,case["prots"],case["regions"],LABEL,refs,out,print_width="double",panel=True,key=False,named_contigs=[IDENTITY],genome_zip=archive)
    assert rec["contigs_drawn"]==["core","NODE_CONTEXT_FULL_123"]
    assert rec["split_gaps"]==[] and rec["link_drawn"] is False
    assert rec["named_contig_contexts"][0]["candidates"][0]["status"]=="MISSING_FOUND_AMBIGUOUS"
    assert rec["min_font_pt"]>=8 and rec["text_overlaps"]==0
    pdftext=" ".join(p.extract_text() for p in PdfReader(out/"gap_rescue.pdf").pages)
    assert "AMBIGUOUS" in pdftext and "NODE_CONTEXT_FULL_123" in pdftext
    receipt=json.loads((out/"named_contig_review.json").read_text())
    assert receipt["scope"]=="REVIEW_CONTEXT_ONLY" and receipt["historical_alignment_binding"]=="NOT_ESTABLISHED_BY_REDRAW"
    assert {"gap_rescue.png","gap_rescue.pdf","gap_rescue_footnote.txt","gap_rescue_key.json"}<={x["path"] for x in receipt["outputs"]}
    for x in receipt["outputs"]:assert hashlib.sha256((out/x["path"]).read_bytes()).hexdigest()==x["sha256"]
    assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before}
    assert case==model_before and counts==glm.count_summary(case["rows"])
    (out/"fixture_validation.json").write_text(json.dumps(dict(model="synthetic operator-supplied model",counts=counts,no_gene_join=True,visible_state="AMBIGUOUS"),indent=2))

@pytest.mark.parametrize("badout",["none","source","child","existing","symlink","dangling_symlink"])
def test_named_context_requires_fresh_disjoint_output(saved_run,case,tmp_path,badout):
    folder,refs,archive=saved_run
    out={"none":None,"source":folder,"child":folder/"child","existing":tmp_path/"existing",
         "symlink":tmp_path/"out_link","dangling_symlink":tmp_path/"out_dangling"}[badout]
    if badout=="existing":out.mkdir()
    if badout in ("symlink","dangling_symlink"):
        target=tmp_path/("link_target" if badout=="symlink" else "absent_target")
        if badout=="symlink":target.mkdir()
        out.symlink_to(target,target_is_directory=True)
    with pytest.raises(ValueError,match="OUTPUT_HOLD"):
        gdr.redraw(folder,case["prots"],case["regions"],LABEL,refs,out,named_contigs=[IDENTITY],genome_zip=archive)
    if badout=="dangling_symlink":assert not target.exists() and out.is_symlink()

def test_invalid_selection_fails_before_output_creation(saved_run,case,tmp_path):
    folder,refs,archive=saved_run;out=tmp_path/"refused"
    with pytest.raises(ValueError,match="IDENTITY_HOLD"):
        gdr.redraw(folder,case["prots"],case["regions"],LABEL,refs,out,named_contigs=["bad"],genome_zip=archive)
    assert not out.exists()

def test_named_option_cannot_trigger_new_analysis(tmp_path):
    with pytest.raises(SystemExit,match="needs --redraw"):
        gdr.main(["--zip",str(tmp_path/"not_read.zip"),"--label",LABEL,"--named-contig",IDENTITY,"--core","core.region001","--out",str(tmp_path/"out")])
    assert not (tmp_path/"out").exists()

def test_default_redraw_does_not_add_keyword_or_receipt(saved_run,case,tmp_path,monkeypatch):
    folder,refs,archive=saved_run;seen=[]
    monkeypatch.setattr(gdr,"draw_locus_map",lambda *a,**k: seen.append(k) or {"default":"unchanged"})
    out=tmp_path/"default"
    assert gdr.redraw(folder,case["prots"],case["regions"],LABEL,refs,out)=={"default":"unchanged"}
    assert "named_contigs" not in seen[0] and not (out/"named_contig_review.json").exists()


def test_cli_identity_hold_is_nonzero_without_success_or_traceback(saved_run,case,tmp_path,monkeypatch,capsys):
    folder,refs,archive=saved_run;out=tmp_path/"refused_cli"
    monkeypatch.setattr(gdr,"load_genome",lambda *_: (case["prots"],case["regions"]))
    status=gdr.main(["--zip",str(archive),"--label",LABEL,"--redraw",str(folder),"--mibig-dir",str(refs),
                    "--out",str(out),"--named-contig","bad"])
    captured=capsys.readouterr()
    assert status==2 and "NAMED_CONTIG_IDENTITY_HOLD" in captured.out
    assert "redrew" not in captured.out and "Traceback" not in captured.err and not out.exists()


def test_source_change_during_render_refuses_final_receipt(saved_run,case,tmp_path,monkeypatch):
    folder,refs,archive=saved_run;out=tmp_path/"changed_attempt"
    def mutate(*args,**kwargs):
        (out/"gap_rescue.png").write_bytes(b"partial png")
        (out/"gap_rescue.pdf").write_bytes(b"partial pdf")
        with (folder/"gap_rescue.tsv").open("a") as h:h.write("\n")
        return {"named_contig_contexts":[]}
    monkeypatch.setattr(gdr,"draw_locus_map",mutate)
    with pytest.raises(ValueError,match="NAMED_CONTIG_INPUT_CHANGED"):
        gdr.redraw(folder,case["prots"],case["regions"],LABEL,refs,out,named_contigs=[IDENTITY],genome_zip=archive)
    assert (out/"gap_rescue.png").exists() and not (out/"named_contig_review.json").exists()


@pytest.mark.parametrize("badcore",[LABEL+" /  / region001 / BGC001","OTHER / core / region001 / BGC001"])
def test_unresolved_core_identity_holds_the_named_context(saved_run,case,tmp_path,badcore):
    folder,refs,archive=saved_run;case["core"]["identity"]=badcore
    receipt=json.loads((folder/"gap_rescue_receipt.json").read_text());receipt["core"]=badcore
    (folder/"gap_rescue_receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match="core four-part identity"):
        gdr.redraw(folder,case["prots"],case["regions"],LABEL,refs,tmp_path/"held_core",named_contigs=[IDENTITY],genome_zip=archive)
    assert not (tmp_path/"held_core").exists()


def test_third_contig_is_additive_to_core_and_supported_partner(case):
    ref=[dict(name="syn"+x,product="biosynthetic enzyme",kind="biosynthetic",s=i,e=i+.5) for i,x in enumerate("ABCD")]
    case["prots"]["q4"]=dict(tag="SUPPORTED_1",contig="supported",start=1000,end=1300,strand=1,contig_len=7000)
    case["rows"].append(dict(i=4,name="synD",status="MISSING_FOUND_CLEAR",best_protein="q4",best_locus="SUPPORTED_1",
                             best_identity_pct="75",reciprocal_best=True,partner_verdict="SUPPORTED"))
    before=deepcopy(case);counts=glm.count_summary(case["rows"])
    drawn,split,order,notdrawn,secondary=glm.choose(ref,case["rows"],[],case["prots"],"core")
    assert order==["core","supported"]
    ctx,records=glm.named_ambiguous_contexts([IDENTITY],LABEL,case["prots"],case["regions"],case["rows"],drawn,"core")
    assert order+list(ctx)==["core","supported","NODE_CONTEXT_FULL_123"]
    assert {pid for _,pid,_ in drawn}=={"q1","q4"} and "q2" not in {pid for _,pid,_ in drawn}
    assert records[0]["display_state"]=="AMBIGUOUS" and counts==glm.count_summary(case["rows"]) and case==before


def test_named_region_identity_cannot_hide_a_different_contig(case):
    case["regions"][1]["contig"]="different_contig"
    with pytest.raises(ValueError,match="identity node differs"):
        select(case)


def test_core_identity_cannot_hide_a_different_contig(saved_run,case,tmp_path):
    folder,refs,archive=saved_run
    case["core"]["contig"]="different_core"
    with pytest.raises(ValueError,match="core identity node differs"):
        gdr.redraw(folder,case["prots"],case["regions"],LABEL,refs,tmp_path/"held_core_node",named_contigs=[IDENTITY],genome_zip=archive)
    assert not (tmp_path/"held_core_node").exists()


@pytest.fixture
def parsed_run(saved_run,case):
    """True small GenBank ZIP parsed by the production loader; no search/fitting."""
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature,FeatureLocation
    from Bio import SeqIO
    import io
    folder,refs,archive=saved_run
    records=[]
    for i,region in enumerate(case["regions"],1):
        rec=SeqRecord(Seq("ATG"+"GCT"*2332+"A"),id=region["contig"],name=region["contig"],description="Synthetic fixed genome")
        rec.annotations["molecule_type"]="DNA"
        rec.features.append(SeqFeature(FeatureLocation(region["start"],region["end"]),type="region",
                         qualifiers=dict(region_number=[str(i)],product=["synthetic-test"])))
        for prot in case["prots"].values():
            if prot["contig"]==region["contig"]:
                rec.features.append(SeqFeature(FeatureLocation(prot["start"],prot["end"],strand=1),type="CDS",
                         qualifiers=dict(locus_tag=[prot["tag"]],translation=[prot["aa"]],gene_kind=["biosynthetic"])))
        records.append(rec)
    buf=io.StringIO();SeqIO.write(records,buf,"genbank")
    with zipfile.ZipFile(archive,"w") as z:z.writestr("synthetic.gbk",buf.getvalue())
    prots,regions=gdr.load_genome(archive,LABEL)
    assert [r["identity"] for r in regions]==[r["identity"] for r in case["regions"]]
    assert {p["tag"] for p in prots.values()}=={"CORE_1","CTX_1","CTX_2"}
    pid_by_tag={p["tag"]:pid for pid,p in prots.items()}
    for row in case["rows"]:
        if row["best_locus"]:row["best_protein"]=pid_by_tag[row["best_locus"]]
    with (folder/"gap_rescue.tsv").open("w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(case["rows"][0]),delimiter="\t");w.writeheader();w.writerows(case["rows"])
    return folder,refs,archive,prots,regions


@pytest.mark.parametrize("when",["during_parse","before_redraw"])
def test_cli_zip_mutation_during_or_after_real_parse_is_held(parsed_run,tmp_path,monkeypatch,capsys,when):
    folder,refs,archive,prots,regions=parsed_run;out=tmp_path/"zip_changed"
    real_load=gdr.load_genome;seen=[]
    def mutate():
        with zipfile.ZipFile(archive,"a") as z:z.writestr("CHANGED_AFTER_PARSE.txt","Mutation regression")
    def load(*args):
        result=real_load(*args);assert result==(prots,regions);seen.append("real_parse")
        if when=="during_parse":mutate()
        return result
    monkeypatch.setattr(gdr,"load_genome",load)
    if when=="before_redraw":
        def names(*args,**kwargs):mutate();return {}
        monkeypatch.setattr(gdr,"load_gene_names",names)
    def forbidden_draw(*args,**kwargs):pytest.fail("changed parse input must not render")
    monkeypatch.setattr(gdr,"draw_locus_map",forbidden_draw)
    status=gdr.main(["--zip",str(archive),"--label",LABEL,"--redraw",str(folder),"--mibig-dir",str(refs),
                    "--out",str(out),"--named-contig",IDENTITY])
    captured=capsys.readouterr()
    assert seen==["real_parse"] and status==2 and "NAMED_CONTIG_INPUT_CHANGED" in captured.out
    assert "redrew" not in captured.out and "Traceback" not in captured.err and not out.exists()


def test_cli_receipt_binds_actual_zip_parse_input(parsed_run,tmp_path):
    folder,refs,archive,prots,regions=parsed_run;out=tmp_path/"parsed_review"
    bound=hashlib.sha256(archive.read_bytes()).hexdigest()
    assert gdr.main(["--zip",str(archive),"--label",LABEL,"--redraw",str(folder),"--mibig-dir",str(refs),
                     "--out",str(out),"--named-contig",IDENTITY,"--panel","--no-key"])==0
    receipt=json.loads((out/"named_contig_review.json").read_text())
    assert receipt["genome_parse_binding"]==dict(state="ZIP_HASH_VERIFIED_BEFORE_AND_AFTER_PARSE",sha256=bound)
    assert receipt["inputs"][0]["sha256"]==bound==hashlib.sha256(archive.read_bytes()).hexdigest()
    assert receipt["historical_alignment_binding"]=="NOT_ESTABLISHED_BY_REDRAW"
    assert receipt["selections"][0]["display_state"]=="AMBIGUOUS"
