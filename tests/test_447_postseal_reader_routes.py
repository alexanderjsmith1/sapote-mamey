"""Reader commands preserve synthetic source-package bytes and symlink boundaries."""
import hashlib,json,importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
from mamey import postseal_output as route
from mamey import compile_report as cr
from mamey import assembly_line as al
from mamey import compound_family_report as cf
from mamey import lead_pages as lp


def package(tmp_path):
    p=tmp_path/'SYN-1'/'package';p.mkdir(parents=True)
    (p/'manifest.json').write_text(json.dumps({'strain_id':'SYN-1','locus_maps':'off'}))
    (p/'SYN-1_domains.csv').write_text('bgc_id,locus_tag,feature_type,domain,substrate,start\nBGC001,ctg_1,aSDomain,PKS_KS,,1\n')
    (p/'SYN-1_4_triage_board.csv').write_text('BGC_ID,Lead_tier_auto,Class,Boundary\nBGC001,High,NRPS,Interior\n')
    (p/'SYN-1_2_inventory.csv').write_text('BGC_ID,Contig,Region,Class\nBGC001,ctg,region001,NRPS\n')
    digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    (p/'checksums_sha256.txt').write_text(''.join(f'{digest(f)}  {f.name}\n' for f in sorted(p.iterdir())))
    return p

@pytest.mark.parametrize('command',['compile-report','compound-families','assembly-line','lead-pages','gecco-crosscheck'])
def test_output_admission_refuses_direct_and_symlink_package(tmp_path,command):
    p=package(tmp_path);link=tmp_path/'alias';link.symlink_to(p,target_is_directory=True)
    for target in [p,p/'new',link/'new']:
        with pytest.raises(ValueError,match='INSIDE_PACKAGE'):route.output_directory(p,command,target)
    assert route.output_directory(p,command)==p.parent/'post_seal'/command

@pytest.mark.parametrize('command',['compound-families','assembly-line','lead-pages'])
def test_actual_reader_commands_preserve_all_package_bytes(tmp_path,monkeypatch,command):
    p=package(tmp_path);before=route.package_binding(p)
    if command=='compound-families': rc=cf.compound_families_command(SimpleNamespace(package=str(p),out=None,no_structures=True))
    elif command=='assembly-line':rc=al.assembly_line_command(SimpleNamespace(package=str(p),out=None))
    else:
        # Keep optional cross-cohort readers on empty fixture channels; exercise
        # the real lead-page renderer and all four identity components.
        monkeypatch.setattr(lp,'WCA',None);monkeypatch.setattr(lp,'ROOT',None)
        rc=lp.lead_pages_command(SimpleNamespace(package=str(p),out=None,bgc='ALL',all_tiers=True))
    assert rc==0 and route.package_binding(p)==before
    assert list(route.output_directory(p,command).rglob('*'))


def test_compile_twice_external_snapshot_and_waiver_writes_never_touch_package(tmp_path,monkeypatch):
    p=package(tmp_path);before=route.package_binding(p)
    import mamey.validate as valid,mamey.blastp_gate as bg,mamey.claim_safety_gate as cs
    monkeypatch.setattr(valid,'validate_package',lambda p:{'identity_binding':'PASS','manifest_parse':'PASS','checksum_integrity':'PASS'})
    def gate(source,strain,**kw):
        assert Path(source)==p and kw['waiver'] is None
        return {'blocked':True,'message':'synthetic gap','missing':[]}
    def record(view,strain,reason,missing):
        assert Path(view)!=p
        m=Path(view)/'manifest.json';data=json.loads(m.read_text());data['synthetic_waiver']='reason';m.write_text(json.dumps(data));return True
    monkeypatch.setattr(bg,'record_waiver',record)
    monkeypatch.setattr(bg,'gate',gate);monkeypatch.setattr(cs,'lint_text',lambda text:[])
    seen=[]
    def build(view,generate_figures,**kw):
        seen.append(generate_figures);assert Path(view)!=p
        (Path(view)/'generated.txt').write_text('reader-only')
        return '# SYN-1\n\nComplete synthetic report.\n'
    monkeypatch.setattr(cr,'build_report',build)
    args=SimpleNamespace(package_dir=str(p),out=None,pdf=False,strict=False,no_figures=False,toc_depth=1,blastp_waiver='reason')
    for _ in range(2):assert cr.compile_report_command(args)==0
    out=route.output_file(p,'compile-report','SYN-1_compiled_report.md');receipt=json.loads(out.with_suffix('.source_receipt.json').read_text())
    assert receipt['source_unchanged'] and receipt['source']==before and seen==[False,False]
    from mamey import sapote_workflow as workflow
    assert route.current_compiled_report(p)==out
    assert workflow.s7_compile(str(p),None,{})[0]==workflow.PASS
    out.write_text('changed external content')
    assert workflow.s7_compile(str(p),None,{})[0]==workflow.PENDING
    assert route.package_binding(p)==before


def test_external_output_tree_cannot_hide_writer_symlink_into_package(tmp_path):
    p=package(tmp_path);outside=tmp_path/'output';outside.mkdir()
    (outside/'COMPOUND_FAMILIES').symlink_to(p,target_is_directory=True)
    with pytest.raises(ValueError,match='OUTPUT_SYMLINK'):
        cf.run(p,outside,with_structures=False)


def test_pdf_sidecar_symlink_cannot_write_into_package(tmp_path):
    p=package(tmp_path);out=tmp_path/'report.md';out.with_suffix('.pdf').symlink_to(p/'report.pdf')
    with pytest.raises(ValueError,match='INSIDE_PACKAGE'):
        cr.compile_report_command(SimpleNamespace(package_dir=str(p),out=str(out)))
