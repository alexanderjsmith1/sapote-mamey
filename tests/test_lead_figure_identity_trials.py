import csv,json
from types import SimpleNamespace
import pytest
from mamey.chatgpt_commands import render_figures_command


def run(tmp_path,monkeypatch,change=None,style='chatgpt-node-first'):
    from matplotlib.figure import Figure
    pkg=tmp_path/'misleading_folder'/'package';pkg.mkdir(parents=True)
    (pkg/'manifest.json').write_text(json.dumps({'strain_id':'TEST-01'}))
    row={'BGC_ID':'BGC001','Contig':'NODE_1_length_12345_cov_20.5','Node_ID':'NODE_1_length_12345_cov_20','Region':'1','antiSMASH_Region':'region001','AB_auto':'55','AF_auto':'30'}
    if change:row.update(change)
    with (pkg/'TEST-01_4_triage_board.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
    seen=[];original=Figure.savefig
    def capture(fig,*a,**k):
        ax=fig.axes[0];seen.append({'title':ax.get_title(),'labels':[t.get_text() for t in ax.get_yticklabels()],'values':[p.get_width() for p in ax.patches]});return original(fig,*a,**k)
    monkeypatch.setattr(Figure,'savefig',capture)
    rc=render_figures_command(SimpleNamespace(package=str(pkg),outdir=str(tmp_path/'out'),top_n=1,style=style))
    return rc,seen


@pytest.mark.parametrize('style',['chatgpt-node-first','default'])
def test_title_and_full_locus(tmp_path,monkeypatch,style):
    rc,seen=run(tmp_path,monkeypatch,style=style)
    assert rc==0 and len(seen)==2
    assert all('TEST-01' in s['title'] and 'misleading_folder' not in s['title'] for s in seen)
    assert all(s['labels']==['TEST-01 / NODE_1_length_12345_cov_20.5 / region001 / BGC001'] for s in seen)
    assert [s['values'] for s in seen]==[[55],[30]]


@pytest.mark.parametrize('change',[{'Contig':''},{'Node_ID':'NODE_2'},{'Region':'2'}])
def test_conflicts_refused(tmp_path,monkeypatch,change):
    rc,seen=run(tmp_path,monkeypatch,change)
    assert rc!=0 and not seen


@pytest.mark.parametrize('column',['AB_auto','AF_auto'])
@pytest.mark.parametrize('value',['','not-a-score','NaN','Infinity','-Infinity'])
def test_invalid_scores_not_rendered_as_zero(tmp_path,monkeypatch,value,column):
    rc,seen=run(tmp_path,monkeypatch,{column:value})
    assert rc!=0 and not seen


def test_real_zero_score_preserved(tmp_path,monkeypatch):
    rc,seen=run(tmp_path,monkeypatch,{'AB_auto':'0'})
    assert rc==0 and seen[0]['values']==[0]
