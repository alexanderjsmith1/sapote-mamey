"""Temporary refusal only: synthetic proteins/numeric fixtures, no replacement metric."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

TOOL = Path(__file__).resolve().parents[1] / 'tools/cluster_relate.py'


@pytest.fixture
def tool():
    spec = importlib.util.spec_from_file_location('t01_refusal', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def proteins(tool, monkeypatch, mapping):
    pytest.importorskip('Bio')
    monkeypatch.setattr(tool, '_genes', lambda name: mapping[name])


@pytest.mark.parametrize('threshold', [30, 100])
@pytest.mark.parametrize('names', [('copies', 'single'), ('single', 'copies'),
                                   ('copies', 'mixed'), ('mixed', 'copies')])
def test_repeated_copy_and_equal_size_order_cases_are_held(tool, monkeypatch, threshold, names):
    proteins(tool, monkeypatch, {'copies':['A'*20]*2, 'single':['A'*20], 'mixed':['A'*20,'W'*20]})
    with pytest.raises(ValueError, match='held:.*(outside|disagree)'):
        tool.pairwise_distances(list(names), list(names), min_id=threshold)


@pytest.mark.parametrize('mapping,expected', [
    ({'a':['A'*20,'W'*20], 'b':['A'*20,'W'*20]}, (0,1,2)),
    ({'a':['A'*20,'W'*20], 'b':['A'*20,'C'*20]}, (.5,.5,1)),
    ({'a':['A'*20], 'b':['W'*20]}, (1,0,0)),
    ({'a':['A'*20,'W'*20], 'b':['A'*20]}, (0,1,1)),
    ({'a':['A'*20]*2, 'b':['A'*20]*2}, (0,1,2)),
])
def test_admitted_results_preserve_legacy_shape_and_order(tool, monkeypatch, mapping, expected):
    proteins(tool, monkeypatch, mapping)
    d,s,count=expected
    for names in [('a','b'),('b','a')]:
        clusters,D,S,detail=tool.pairwise_distances(list(names),list(names),min_id=100)
        assert clusters == [mapping[x] for x in names]
        assert D == [[0,d],[d,0]]
        assert S == [[1,s],[s,1]]
        assert detail == {(0,1):(count,100.0 if count else 0)}


@pytest.mark.parametrize('identity', [float('nan'),float('inf'),-1,101])
def test_invalid_identity_cannot_silently_become_no_match(tool, monkeypatch, identity):
    monkeypatch.setattr(tool,'_genes',lambda name:['synthetic'])
    monkeypatch.setattr(tool,'_aligner',lambda:None)
    monkeypatch.setattr(tool,'_gid',lambda *args:identity)
    with pytest.raises(ValueError,match='global identity'):
        tool.pairwise_distances(['a','b'],['a','b'])


def test_unrounded_directional_mismatch_is_held(tool,monkeypatch):
    monkeypatch.setattr(tool,'_genes',lambda name:[name])
    monkeypatch.setattr(tool,'_aligner',lambda:None)
    monkeypatch.setattr(tool,'_gid',lambda al,a,b:50.00001 if a=='a' else 50.00002)
    with pytest.raises(ValueError,match='directional'):
        tool.pairwise_distances(['a','b'],['a','b'])


def test_equal_similarity_but_directional_details_differ_is_held(tool,monkeypatch):
    mapping={'a':['a0','a1','a2'],'b':['b0','b1']}
    values=[[100,100],[30,0],[70,0]]
    monkeypatch.setattr(tool,'_genes',lambda name:mapping[name])
    monkeypatch.setattr(tool,'_aligner',lambda:None)
    def identity(al,a,b):
        if a.startswith('b'): a,b=b,a
        return values[int(a[1])][int(b[1])]
    monkeypatch.setattr(tool,'_gid',identity)
    with pytest.raises(ValueError,match='directional'):
        tool.pairwise_distances(['a','b'],['a','b'])


@pytest.mark.parametrize('threshold',[float('nan'),float('inf'),-1,101])
def test_invalid_threshold_refused_before_reading_inputs(tool,monkeypatch,threshold):
    monkeypatch.setattr(tool,'_genes',lambda name:pytest.fail('input read before threshold check'))
    with pytest.raises(ValueError,match='min-id'):
        tool.pairwise_distances(['a','b'],['a','b'],min_id=threshold)


def test_label_count_mismatch_is_refused(tool):
    with pytest.raises(ValueError,match='one label'):
        tool.pairwise_distances(['a'],['a','b'])


@pytest.mark.parametrize('D', [[],[[0]],[[0,-1],[-1,0]],[[0,2],[2,0]],
    [[0,float('nan')],[float('nan'),0]],[[0,float('inf')],[float('inf'),0]],
    [[0,.2],[.3,0]],[[.1,0],[0,0]],[[0,.5],[.5]],[[0,'x'],['x',0]]])
@pytest.mark.parametrize('entry',['upgma_newick','make_dendrogram'])
def test_direct_output_helpers_refuse_invalid_matrix_before_rendering(tool,tmp_path,D,entry):
    args=(['a','b'],D) if entry=='upgma_newick' else (['a','b'],D,tmp_path,'Synthetic')
    with pytest.raises(ValueError,match='distance matrix'):
        getattr(tool,entry)(*args)
    assert not list(tmp_path.iterdir())


def test_valid_newick_stays_unchanged(tool):
    assert tool.upgma_newick(['a','b'],[[0,.4],[.4,0]])=='(a:0.2000,b:0.2000);'
    assert tool.upgma_newick(['a'],[[0]])=='a;'


@pytest.mark.parametrize('names',[('copies','single'),('copies','mixed')])
def test_main_refuses_before_writing_any_outputs(tool,monkeypatch,tmp_path,names):
    proteins(tool,monkeypatch,{'copies':['A'*20]*2,'single':['A'*20],'mixed':['A'*20,'W'*20]})
    monkeypatch.setattr(tool,'make_dendrogram',lambda *args:pytest.fail('render reached'))
    output=tmp_path/'new_output'
    argv=['--outdir',str(output)]
    for name in names:argv+=['--gbk',name+':'+name]
    with pytest.raises(SystemExit) as result:tool.main(argv)
    assert result.value.code==2
    assert not output.exists()


def test_refused_run_does_not_overwrite_existing_output(tool,monkeypatch,tmp_path):
    proteins(tool,monkeypatch,{'copies':['A'*20]*2,'single':['A'*20]})
    old=tmp_path/'distance_matrix.csv';old.write_text('prior output: requires prior receipt')
    with pytest.raises(SystemExit):
        tool.main(['--gbk','copies:copies','--gbk','single:single','--outdir',str(tmp_path)])
    assert old.read_text()=='prior output: requires prior receipt'
    assert not (tmp_path/'tree.nwk').exists()


def test_single_input_cli_refused_before_outputs(tool,tmp_path):
    with pytest.raises(SystemExit) as result:
        tool.main(['--gbk','a:not-read.gbk','--outdir',str(tmp_path/'output')])
    assert result.value.code==2
    assert not (tmp_path/'output').exists()


def test_prefilter_indices_are_reversed_without_replacing_engine(tool,monkeypatch):
    proteins(tool,monkeypatch,{'a':['A'*20,'W'*20],'b':['A'*20,'W'*20]})
    hits=[SimpleNamespace(query_index=0,target_index=2),SimpleNamespace(query_index=1,target_index=3)]
    monkeypatch.setitem(sys.modules,'pyswrd',SimpleNamespace(search=lambda *args,**kwargs:hits))
    clusters,D,S,detail=tool.pairwise_distances(['a','b'],['a','b'],engine='pyswrd')
    assert D==[[0,0],[0,0]] and detail=={(0,1):(2,100.0)}


def test_tiny_difference_across_output_rounding_boundary_is_held(tool,monkeypatch):
    monkeypatch.setattr(tool,'_genes',lambda name:[name])
    monkeypatch.setattr(tool,'_aligner',lambda:None)
    monkeypatch.setattr(tool,'_gid',lambda al,a,b:50.00500000000005 if a=='a' else 50.00499999999995)
    with pytest.raises(ValueError,match='directional'):
        tool.pairwise_distances(['a','b'],['a','b'])


@pytest.mark.parametrize('right',['single','mixed'])
def test_real_cli_reads_synthetic_gbks_and_refuses_before_outputs(tmp_path,right):
    import os,subprocess
    pytest.importorskip('Bio')
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature,FeatureLocation
    inputs={'copies':['A'*20]*2,'single':['A'*20],'mixed':['A'*20,'W'*20]}
    for name in ['copies',right]:
        rec=SeqRecord(Seq('N'*200),id='synthetic',name='synthetic',description='artificial refusal fixture')
        rec.annotations['molecule_type']='DNA'
        for i,aa in enumerate(inputs[name]):
            feature=SeqFeature(FeatureLocation(i*100,i*100+60),type='CDS')
            feature.qualifiers={'translation':[aa],'locus_tag':['toy'+str(i)]}
            rec.features.append(feature)
        SeqIO.write(rec,str(tmp_path/(name+'.gbk')),'genbank')
    output=tmp_path/'output'
    result=subprocess.run([sys.executable,str(TOOL),'--gbk','copies:'+str(tmp_path/'copies.gbk'),
        '--gbk',right+':'+str(tmp_path/(right+'.gbk')),'--outdir',str(output)],
        capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode==2 and 'cluster_relate held:' in result.stderr
    assert not output.exists()


@pytest.mark.parametrize('labels', [['dup','dup'],['','b'],['   ','b'],[None,'b'],[7,'b']])
def test_invalid_labels_refused_before_input_reads(tool,monkeypatch,labels):
    monkeypatch.setattr(tool,'_genes',lambda name:pytest.fail('invalid label read an input'))
    with pytest.raises(ValueError,match='labels must be'):
        tool.pairwise_distances(labels,['a','b'])


@pytest.mark.parametrize('labels', [['dup','dup'],['','b'],['   ','b'],[None,'b']])
def test_direct_newick_rejects_ambiguous_labels(tool,labels):
    with pytest.raises(ValueError,match='labels must be'):
        tool.upgma_newick(labels,[[0,.4],[.4,0]])


def test_labels_are_preserved_without_silent_normalization(tool,monkeypatch):
    proteins(tool,monkeypatch,{'a':['A'*20],'b':['A'*20]})
    labels=['a',' a ']
    result=tool.pairwise_distances(labels,['a','b'])
    assert labels==['a',' a ']
    assert tool.upgma_newick(labels,result[1])=="(a:0.0000,' a ':0.0000);"


@pytest.mark.parametrize('labels',[['dup','dup'],['','b'],['   ','b']])
def test_invalid_cli_labels_create_no_outputs(tool,monkeypatch,tmp_path,labels):
    monkeypatch.setattr(tool,'_genes',lambda name:pytest.fail('invalid label read an input'))
    output=tmp_path/'output'
    argv=['--outdir',str(output)]
    for label in labels:argv+=['--gbk',label+':not_read.gbk']
    with pytest.raises(SystemExit) as result:tool.main(argv)
    assert result.value.code==2
    assert not output.exists()


@pytest.mark.parametrize('label',['a,b','a(b)','a:b','a;b','a[b]','a b',' a','a ',
    "O'Brien","ab''cd",'αβ sapote','naïve_Δ','123','a"b', 'a '+chr(92)])
def test_newick_special_labels_round_trip_exactly(tool,label):
    pytest.importorskip('Bio')
    import io
    from Bio import Phylo
    labels=[label,'plain']
    newick=tool.upgma_newick(labels,[[0,.4],[.4,0]])
    assert [leaf.name for leaf in Phylo.read(io.StringIO(newick),'newick').get_terminals()]==labels
    single=tool.upgma_newick([label],[[0]])
    assert [leaf.name for leaf in Phylo.read(io.StringIO(single),'newick').get_terminals()]==[label]


@pytest.mark.parametrize('label', ["'leading", "''leading", "'", "a\\'b"])
def test_parser_unsupported_label_spellings_refused_before_inputs(tool,monkeypatch,label):
    pytest.importorskip('Bio')
    monkeypatch.setattr(tool,'_genes',lambda name:pytest.fail('unsupported label read input'))
    with pytest.raises(ValueError,match='(round-trip|verified)'):
        tool.pairwise_distances([label,'plain'],['a','b'])


@pytest.mark.parametrize('label',['a\n','a\r','a\t','a\x00','a\x7f','a\x85','a\u200b','a\ud800'])
def test_control_format_surrogate_characters_refused_before_inputs(tool,monkeypatch,label):
    monkeypatch.setattr(tool,'_genes',lambda name:pytest.fail('invalid label read input'))
    with pytest.raises(ValueError,match='control, format or surrogate'):
        tool.pairwise_distances([label,'plain'],['a','b'])


def test_neighboring_quoted_labels_are_verified_in_complete_tree(tool,monkeypatch,tmp_path):
    labels=['a '+chr(92),'b c']
    with pytest.raises(ValueError,match='round-trip'):
        tool.upgma_newick(labels,[[0,.4],[.4,0]])
    proteins(tool,monkeypatch,{'a':['A'*20],'b':['A'*20]})
    output=tmp_path/'output'
    with pytest.raises(SystemExit) as result:
        tool.main(['--gbk',labels[0]+':a','--gbk',labels[1]+':b','--outdir',str(output)])
    assert result.value.code==2 and not output.exists()
