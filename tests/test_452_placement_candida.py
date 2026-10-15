import shutil
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from tools import placement_display as display

@pytest.fixture
def activity():
    from tools import _placement_activity
    return _placement_activity
from .test_452_rect02_shipping import toy_run, read_pdf


def test_profile_and_four_states_preserve_blank(tmp_path,activity):
    config=tmp_path/'layouts.json';config.write_text('{"synthetic":{"split_candida":true},"pooled":{}}')
    assert activity.profile('synthetic',config)['split_candida']
    assert not activity.profile('pooled',config).get('split_candida',False)
    assert activity.profile()=={}
    assert [activity.state(x) for x in ['+','-','n.t.','']]==['+','−','n.t.','']
    for bad in ['unknown','nan','inf']:
        with pytest.raises(ValueError):activity.state(bad)


def test_long_table_keeps_species_and_material_separate(tmp_path,activity):
    p=tmp_path/'table.tsv'
    p.write_text('strain\torganism\tmaterial\tbest_pct\nSYN-970\tCandida albicans\tCrude extract\t+\nSYN-970\tCandida auris\tCrude extract\t-\nSYN-970\tCandida (species not named)\tCrude extract\tn.t.\nSYN-970\tCandida albicans\tFraction\t95\n')
    records,strips=activity.load(p)
    assert [s['label'] for s in strips]==list(activity.LABELS)
    assert list(records['SYN-970'].values())==['+','−','n.t.']
    p.write_text(p.read_text()+'SYN-970\tCandida albicans\tCrude extract\t80\n')
    with pytest.raises(ValueError,match='DUPLICATE'):activity.load(p)


def test_blank_unknown_column_does_not_make_an_extra_strip(tmp_path,activity):
    p=tmp_path/'table.tsv';p.write_text('strain\tC. albicans\tC. auris\tanti_Candida_unspecified\nSYN-970\t+\t-\t\n')
    records,strips=activity.load(p)
    assert [s['label'] for s in strips]==list(activity.LABELS[:2])


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_three_species_strips_plus_mrsa_render_and_replay(tmp_path,monkeypatch,activity):
    run,admission=toy_run(tmp_path,monkeypatch)
    # Reserved IDs come from the parser-contract fixture in the shipping card.
    ids=[line[1:] for line in (run/'query.aligned.fasta').read_text().splitlines() if line.startswith('>')]
    (run/'split.tsv').write_text('strain\tC. albicans\tC. auris\tanti_Candida_unspecified\tanti_MRSA\n'+f'{ids[0]}\t+\t-\tn.t.\t+\n{ids[1]}\t\t+\t-\t\n')
    config=run/'layouts.json';config.write_text('{"synthetic":{"split_candida":true}}')
    out=tmp_path/'split'
    args=[str(run),'--name','toy','--group','Example','--host-table',str(run/'hosts.tsv'),'--ref-source-db',str(run/'refs.sqlite'),'--strip-set','activity','--bioassay-table',str(run/'split.tsv'),'--layout','synthetic','--layout-config',str(config),'--isolate-emphasis','bold','--label-style','short','--keep-all-references','--out',str(out)]
    assert display.main(args)==0
    audit=list(csv.DictReader((out/'toy_rect02.activity_audit.tsv').open(),delimiter='\t'))
    assert len(audit)==7*4
    joined={(r['tip'],r['strip']):r['value'] for r in audit}
    assert [joined[(ids[0],label)] for label in activity.LABELS]==['+','−','n.t.']
    assert [joined[(ids[1],label)] for label in activity.LABELS]==['','+','−']
    assert all(r['value']=='' for r in audit if r['tip'] not in ids)
    pdf=read_pdf(out/'toy_rect02.pdf')[0]
    assert pdf['width']==pytest.approx(518.4,abs=.01)
    assert min(c['size'] for c in pdf['chars'] if c['text'].strip())>=7.99
    assert all(0<=c['x0']<=c['x1']<=pdf['width'] for c in pdf['chars'])
    package=out/'standalone_R_package'
    env=dict(os.environ,SAPOTE_PYTHON=sys.executable,PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH'])
    proc=subprocess.run(['sh','toy_rerender_captioned.sh'],cwd=package,env=env,capture_output=True,text=True)
    assert proc.returncode==0,proc.stdout+proc.stderr
    replay=list(csv.DictReader((package/'toy_captioned.activity_audit.tsv').open(),delimiter='\t'))
    assert replay==audit
    from tools.check_figure_provenance import stamp
    assert stamp(package/'toy_captioned.pdf')[0]=='PASS'
