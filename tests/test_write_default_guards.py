"""Synthetic output-boundary controls. No reports, figures, sequences or network work."""
import importlib.util
import os
from pathlib import Path
import sys
import pytest
from mamey.path_safety import OutputInsideBundle
TARGET=Path(__file__).resolve().parents[1]


def load(relative,tmp_path,monkeypatch):
    workspace=tmp_path/'workspace';workspace.mkdir(exist_ok=True)
    monkeypatch.setenv('MAMEY_DATA_ROOT',str(workspace));monkeypatch.setenv('SAPOTE_WORKSPACE_ROOT',str(workspace))
    monkeypatch.setenv('RID_BASE','_SOFTWARE_GUARD');monkeypatch.setenv('RID_QUERIES','_SOFTWARE_QUERIES')
    path=TARGET/relative;spec=importlib.util.spec_from_file_location('guard_fixture_'+relative.split('/')[-1][:-3],path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    fake=tmp_path/'source_bundle';fake.mkdir(exist_ok=True);(fake/'BUILD_STAMP.txt').write_text('synthetic code marker\n')
    monkeypatch.setattr(mod,'__file__',str(fake/relative))
    return mod,fake,workspace


def compiler(tmp_path,monkeypatch):
    mod,fake,workspace=load('deliverable_tools/build_modeb_compilation.py',tmp_path,monkeypatch)
    called=[];monkeypatch.setattr(mod,'build',lambda strain:called.append(strain) or '# synthetic compilation\n')
    monkeypatch.setattr(mod,'guard_canonical_write',lambda *a,**k:None)
    return mod,fake,workspace,called


def test_compiler_default_bundle_target_refuses_before_mkdir_or_build(tmp_path,monkeypatch):
    mod,fake,_,called=compiler(tmp_path,monkeypatch);mod.MASTER=fake/'strain_data';mod.OUTDIR=mod.MASTER/'dated'
    monkeypatch.setattr(sys,'argv',['compiler','--strain','SOFTWARE','--no-docx'])
    with pytest.raises(OutputInsideBundle) as caught:mod.main()
    assert "MAMEY_DATA_ROOT" in str(caught.value)
    assert "SAPOTE_WORKSPACE_ROOT" not in str(caught.value)
    assert called==[] and not mod.MASTER.exists()


def test_compiler_preflights_all_strains_before_any_default_write(tmp_path,monkeypatch):
    mod,fake,workspace,called=compiler(tmp_path,monkeypatch);mod.MASTER=workspace/'master';mod.MASTER.mkdir();mod.OUTDIR=workspace/'dated'
    (mod.MASTER/'SECOND').symlink_to(fake/'protected',target_is_directory=True)
    monkeypatch.setattr(sys,'argv',['compiler','--strains','FIRST','SECOND','--no-docx'])
    with pytest.raises(OutputInsideBundle):mod.main()
    assert called==[] and not mod.OUTDIR.exists() and not (mod.MASTER/'FIRST').exists() and not (fake/'protected').exists()


def test_compiler_explicit_external_out_does_not_touch_default_bundle_targets(tmp_path,monkeypatch):
    mod,fake,workspace,called=compiler(tmp_path,monkeypatch);mod.MASTER=fake/'strain_data';mod.OUTDIR=mod.MASTER/'dated';out=workspace/'explicit'
    monkeypatch.setattr(sys,'argv',['compiler','--strain','SOFTWARE','--no-docx','--out',str(out)])
    assert mod.main()==0
    assert (out/'SOFTWARE_ModeB_compilation.md').read_text()=='# synthetic compilation\n'
    assert not mod.MASTER.exists() and called==['SOFTWARE']


def test_compiler_external_defaults_preserve_both_output_locations(tmp_path,monkeypatch):
    mod,_,workspace,_=compiler(tmp_path,monkeypatch);mod.MASTER=workspace/'master';mod.OUTDIR=workspace/'dated'
    monkeypatch.setattr(sys,'argv',['compiler','--strain','SOFTWARE','--no-docx'])
    assert mod.main()==0
    assert (mod.MASTER/'SOFTWARE/SOFTWARE_ModeB_compilation.md').is_file()
    assert (mod.OUTDIR/'SOFTWARE_ModeB_compilation.md').is_file()


def run_helper(mod,name):
    if name=='lane_owner':
        with mod.lane_owner():pass
    elif name=='log':mod.log('synthetic output-boundary control')
    else:mod.save_ledger({})


@pytest.mark.parametrize('name',['lane_owner','log','save_ledger'])
@pytest.mark.parametrize('symlink',[False,True])
def test_crawler_direct_helper_refuses_inside_bundle_before_files(tmp_path,monkeypatch,name,symlink):
    mod,fake,workspace=load('tools/blastp_crawl/nr_rid_runner.py',tmp_path,monkeypatch)
    base=fake/'lane'
    if symlink:
        link=workspace/'lane_link';link.symlink_to(base,target_is_directory=True);base=link
    mod.BASE=base;mod.LOG=base/'_run.log';mod.LEDGER=base/'_ledger.csv'
    with pytest.raises(OutputInsideBundle):run_helper(mod,name)
    assert not (fake/'lane').exists()


@pytest.mark.parametrize('name,attribute',[('log','LOG'),('save_ledger','LEDGER')])
def test_crawler_guards_actual_file_before_creating_lane(tmp_path,monkeypatch,name,attribute):
    mod,fake,workspace=load('tools/blastp_crawl/nr_rid_runner.py',tmp_path,monkeypatch)
    mod.BASE=workspace/'new_lane';protected=fake/'retained';protected.write_text('retained bytes');setattr(mod,attribute,protected)
    with pytest.raises(OutputInsideBundle):run_helper(mod,name)
    assert protected.read_text()=='retained bytes' and not mod.BASE.exists()


@pytest.mark.parametrize('name',['lane_owner','log','save_ledger'])
def test_crawler_direct_helpers_keep_external_io_behavior(tmp_path,monkeypatch,name):
    mod,_,workspace=load('tools/blastp_crawl/nr_rid_runner.py',tmp_path,monkeypatch)
    mod.BASE=workspace/'lane';mod.LOG=mod.BASE/'_run.log';mod.LEDGER=mod.BASE/'_ledger.csv'
    run_helper(mod,name)
    assert mod.BASE.is_dir()
    if name=='lane_owner':assert (mod.BASE/'_runner.lock').is_file()
    if name=='log':assert 'synthetic output-boundary control' in mod.LOG.read_text()
    if name=='save_ledger':assert mod.LEDGER.read_text().startswith('strain,bgc,file,')


def test_compiler_checks_default_file_symlink_before_build(tmp_path,monkeypatch):
    mod,fake,workspace,called=compiler(tmp_path,monkeypatch);mod.MASTER=workspace/'master';mod.OUTDIR=workspace/'dated'
    directory=mod.MASTER/'SOFTWARE';directory.mkdir(parents=True)
    protected=fake/'retained';protected.write_text('retained bytes')
    (directory/'SOFTWARE_ModeB_compilation.md').symlink_to(protected)
    monkeypatch.setattr(sys,'argv',['compiler','--strain','SOFTWARE','--no-docx'])
    with pytest.raises(OutputInsideBundle):mod.main()
    assert called==[] and protected.read_text()=='retained bytes' and not mod.OUTDIR.exists()


def test_compiler_checks_enabled_docx_destination_without_rendering(tmp_path,monkeypatch):
    mod,fake,workspace,called=compiler(tmp_path,monkeypatch);mod.MASTER=workspace/'master';mod.OUTDIR=workspace/'dated'
    directory=mod.MASTER/'SOFTWARE';directory.mkdir(parents=True);(directory/'SOFTWARE_ModeB_compilation.docx').symlink_to(fake/'new_docx')
    monkeypatch.setattr(sys,'argv',['compiler','--strain','SOFTWARE'])
    monkeypatch.setattr(mod,'to_docx',lambda *a,**k:pytest.fail('conversion must not be reached'))
    with pytest.raises(OutputInsideBundle):mod.main()
    assert called==[] and not mod.OUTDIR.exists() and not (fake/'new_docx').exists()


@pytest.mark.parametrize('name,attribute',[('log','LOG'),('save_ledger','LEDGER')])
def test_crawler_file_symlink_into_bundle_refused_early(tmp_path,monkeypatch,name,attribute):
    mod,fake,workspace=load('tools/blastp_crawl/nr_rid_runner.py',tmp_path,monkeypatch)
    mod.BASE=workspace/'new_lane';protected=fake/'retained';protected.write_text('retained bytes');link=workspace/'file_link';link.symlink_to(protected);setattr(mod,attribute,link)
    with pytest.raises(OutputInsideBundle):run_helper(mod,name)
    assert protected.read_text()=='retained bytes' and not mod.BASE.exists()


@pytest.mark.parametrize('command',['run','rebuild'])
def test_crawler_existing_cli_guard_still_blocks_before_dispatch(tmp_path,monkeypatch,command):
    mod,fake,_=load('tools/blastp_crawl/nr_rid_runner.py',tmp_path,monkeypatch);mod.BASE=fake/'lane'
    monkeypatch.setattr(mod,'cmd_run',lambda *a:pytest.fail('workflow dispatch must not be reached'))
    monkeypatch.setattr(mod,'cmd_rebuild',lambda *a:pytest.fail('workflow dispatch must not be reached'))
    monkeypatch.setattr(sys,'argv',['runner',command])
    with pytest.raises(OutputInsideBundle):mod.main()
    assert not mod.BASE.exists()


def test_crawler_status_dispatch_remains_read_only(tmp_path,monkeypatch):
    mod,fake,_=load('tools/blastp_crawl/nr_rid_runner.py',tmp_path,monkeypatch);mod.BASE=fake/'lane';called=[]
    monkeypatch.setattr(mod,'cmd_status',lambda:called.append('status'))
    monkeypatch.setattr(sys,'argv',['runner','status'])
    assert mod.main()==0 and called==['status'] and not mod.BASE.exists()


@pytest.mark.parametrize("alias", [False, True], ids=["direct", "symlink"])
def test_compiler_explicit_bundle_target_refused_before_build(tmp_path,monkeypatch,alias):
    mod,fake,workspace,called=compiler(tmp_path,monkeypatch);out=fake/"generated"
    if alias:
        link=workspace/"linked";link.symlink_to(fake,target_is_directory=True);out=link/"generated"
    monkeypatch.setattr(sys,"argv",["compiler","--strain","SOFTWARE","--no-docx","--out",str(out)])
    with pytest.raises(OutputInsideBundle) as caught:mod.main()
    assert "--out" in str(caught.value)
    assert called == [] and not (fake/"generated").exists()

def test_compiler_explicit_target_existing_file_symlink_refused_before_build(tmp_path,monkeypatch):
    mod,fake,workspace,called=compiler(tmp_path,monkeypatch);out=workspace/"out";out.mkdir();target=fake/"retained.md";target.write_text("retain")
    (out/"SOFTWARE_ModeB_compilation.md").symlink_to(target)
    monkeypatch.setattr(sys,"argv",["compiler","--strain","SOFTWARE","--no-docx","--out",str(out)])
    with pytest.raises(OutputInsideBundle):mod.main()
    assert called == [] and target.read_text()=="retain"
