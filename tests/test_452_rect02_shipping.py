"""Renderer and parser-contract fixtures; identifiers are synthetic reserved IDs."""
import shutil
import csv
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
Phylo = pytest.importorskip("Bio.Phylo")
from tools import placement_display as display, graft_integrity as gi
from tools import tree_sanity_check as sanity
ROOT=Path(__file__).resolve().parents[1]


def toy_run(tmp_path, monkeypatch):
    run=tmp_path/'run';run.mkdir(); ref=run/'refpkg';ref.mkdir()
    names=['Example_alpha_NR_999970.1','Example_beta_NR_999971.1','Example_gamma_NR_999972.1','Example_delta_NR_999973.1','Other_epsilon_NR_999974.1_outgroup']
    a,b,c,d,og=names; q1,q2='AS-977','AS-971'
    backbone=f'(({a}:0.02{{0}},{b}:0.02{{1}}):0.02{{2}},({c}:0.02{{3}},{d}:0.02{{4}}):0.02{{5}},{og}:0.04{{6}}){{7}};'
    raw=f'(({a}:0.02,({b}:0.01,{q1}:0.01):0.01):0.02,(({c}:0.01,{q2}:0.01):0.01,{d}:0.02):0.02,{og}:0.04);'
    sources={'jplace':run/'epa_result.jplace','reference_tree':ref/'ref.tree','reference_alignment':ref/'ref.aln.fasta','query_alignment':run/'query.aligned.fasta','model':ref/'ref.bestModel','placement_provenance':run/'_provenance.json','reference_provenance':ref/'_provenance.json'}
    sources['reference_tree'].write_text(f'(({a}:.02,{b}:.02)91:.02,({c}:.02,{d}:.02)92:.02,{og}:.04);')
    sources['jplace'].write_text(json.dumps({'tree':backbone,'fields':['edge_num','likelihood','like_weight_ratio','distal_length','pendant_length'],'placements':[{'n':[q1],'p':[[1,-1,1,.01,.01]]},{'n':[q2],'p':[[3,-1,1,.01,.01]]}]}))
    sources['reference_alignment'].write_text(''.join(f'>{name}\n'+('ACGT'*150)+'\n' for name in names))
    sources['query_alignment'].write_text(''.join(f'>{name}\n'+('ACGT'*150)+'\n' for name in [q1,q2]))
    sources['model'].write_text('GTR+G')
    for role in ['placement_provenance','reference_provenance']:sources[role].write_text('{"group":"Example","molecule":"nucleotide"}')
    with monkeypatch.context() as mp:
        def external(argv,**kwargs):
            assert argv[1:3]==['examine','graft']
            Path(argv[argv.index('--out-dir')+1],'epa_result.newick').write_text(raw)
            return SimpleNamespace(returncode=0)
        mp.setattr(gi.subprocess,'run',external)
        admission=gi.produce_graft_length_evidence(sources,run,'synthetic-gappa')
    (run/'hosts.tsv').write_text('strain\thost\tlocation\tgenbank_accession\tgenus\n'+f'{q1}\tsoil\tCanada\tPP999970.1\tExample\n{q2}\tsoil\tCanada\tPP999971.1\tExample\n')
    with (run/'hosts.tsv').open('a') as handle:
        handle.write('AS-972\tsoil\tCanada\tPP999972.1\tUnrelated\n')
    (run/'bio.tsv').write_text(f'strain\tanti_Candida\tanti_MRSA\n{q1}\tpositive\tnegative\n{q2}\tnot_tested\tpositive\n')
    with sqlite3.connect(run/'refs.sqlite') as db:
        db.execute('CREATE TABLE record(acc_base TEXT,isolation_source TEXT,country TEXT,definition TEXT,designation TEXT,is_type INTEGER)')
        for i,name in enumerate(names):db.execute('INSERT INTO record VALUES(?,?,?,?,?,?)',(f'NR_{999970+i}','soil','Canada',name.replace('_',' ').split(' NR ')[0]+' 16S ribosomal RNA','synthetic',0))
    return run, admission


def test_root_preservation_and_support_transfer(tmp_path):
    from tools import transfer_supports_to_graft as support
    graft=tmp_path/'g.nwk';ref=tmp_path/'r.nwk';out=tmp_path/'out.nwk'
    graft.write_text('((A:.03,(B:.01,Q:.02):.02):.04,(C:.03,D:.03):.04,OG_outgroup:.07);')
    ref.write_text('((A:.03,B:.03)91:.04,(C:.03,D:.03)92:.04,OG_outgroup:.07);')
    original=graft.read_bytes(); copied=tmp_path/'copy.nwk'
    display.root_on_outgroup(graft,copied)
    assert copied.read_bytes()==original
    support.transfer_preserving_root(graft,ref,out)
    assert support.rooted_signature(Phylo.read(graft,'newick'))[1:]==support.rooted_signature(Phylo.read(out,'newick'))[1:]
    assert sorted(n.confidence for n in Phylo.read(out,'newick').get_nonterminals() if n.confidence)==[91,92]
    assert graft.read_bytes()==original


def test_strict_root_stem_and_other_failures_remain(tmp_path):
    p=tmp_path/'tree.nwk';p.write_text('((A:.01,B:.01,C:.01):.8,O_outgroup:.1);')
    ok,msg=sanity.check(p); assert not ok and 'DOMINATING_BRANCH' in msg and 'stem-exemption' not in msg
    p.write_text('(((A:.01,B:.01):.8,C:.01):.01,O_outgroup:.1);')
    assert not sanity.check(p)[0]
    p.write_text('((A:.9,B:.01,C:.01):.8,O_outgroup:.1);')
    ok,msg=sanity.check(p);assert not ok and 'LONG_TERMINAL' in msg


def test_family_selection_refuses_then_keeps_true_nearest(tmp_path):
    groups=[]
    for i,g in enumerate(['Alpha','Beta','Gamma']):
        refs=','.join(f'{g}_species{i}{j}_NR_{999970+i*3+j}.1:.01' for j in range(3))
        query=f',AS-{970+i}:.01' if i<2 else ''
        groups.append(f'({refs}{query}):.1')
    tree=tmp_path/'toy.nwk';tree.write_text('('+','.join(groups)+',Other_species_NR_999999.1_outgroup:.2);')
    out=tmp_path/'result';cmd=[sys.executable,str(ROOT/'tools/build_placement_ggtree_inputs.py'),'--graft',str(tree),'--neighbors','3','--out-prefix',str(out)]
    bad=subprocess.run(cmd,capture_output=True,text=True);assert bad.returncode!=0 and '--family-level' in bad.stderr
    good=subprocess.run(cmd+['--family-level'],capture_output=True,text=True);assert good.returncode==0,good.stderr
    rows=list(csv.DictReader(Path(str(out)+'_reference_selection.tsv').open(),delimiter='\t'))
    for i,g in enumerate(['Alpha','Beta']):
        selected=[r for r in rows if r['query_tip']==f'AS-{970+i}']
        assert len(selected)==3 and all(r['reference_tip'].startswith(g+'_') for r in selected)
        assert [r['true_neighbor_rank'] for r in selected]==['1','2','3']
        assert all(r['true_nearest_reference']==selected[0]['reference_tip'] for r in selected)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_flat_admitted_run_renders_strips_end_to_end(tmp_path,monkeypatch):
    run,admission=toy_run(tmp_path,monkeypatch)
    out=tmp_path/'display'
    args=[str(run),'--name','toy','--group','Example','--host-table',str(run/'hosts.tsv'),'--ref-source-db',str(run/'refs.sqlite'),'--strip-set','activity','--bioassay-table',str(run/'bio.tsv'),'--isolate-emphasis','bold','--label-style','short','--keep-all-references','--out',str(out)]
    assert display.main(args)==0
    assert 'Unrelated' not in (out/'CAPTION.md').read_text()
    receipt=json.loads((out/'placement_display_receipt.json').read_text())
    assert receipt['length_admission']['state']=='PASS_LENGTH_QA'
    assert receipt['root_policy']=='display_rooted_split'
    assert receipt['root_variants']['split_gate_pass'] is True
    assert (out/'toy.rooted_split.newick').is_file()
    assert (out/'rooted.nwk').read_bytes()==Path(admission['selected']['restored']).read_bytes()
    assert len(Phylo.read(out/'toy_display.nwk','newick').get_terminals())==7
    from tools.check_figure_provenance import stamp
    for ext in ['png','pdf']:
        assert stamp(out/f'toy_rect02.{ext}')[0]=='PASS'
    audit=list(csv.DictReader((out/'toy_rect02.annotation_audit.tsv').open(),delimiter='\t'))
    assert len(audit)==7
    assert sum(r['value']=='active (≥80%)' for r in audit)==1


def render_direct(tmp_path, n=7, long_label=False, **extra):
    tree=tmp_path/'input.nwk';meta=tmp_path/'meta.tsv';prefix=tmp_path/'figure'
    tips=[f'SYN-{970+i}' if i<30 else f'Reference_{i:03d}' for i in range(n-1)]+['Reference_outgroup']
    tree.write_text('((' + ','.join(f'{tip}:0.01' for tip in tips[:-1]) + '):0.01,' + tips[-1] + ':0.03);')
    with meta.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['tip','label','role','category','source'],delimiter='\t');writer.writeheader()
        for i,tip in enumerate(tips):
            label=tip
            if i==0 and long_label:label='Example species SYN-970 (+12 grouped; max 1 nt differences; min 600 shared sites)'
            writer.writerow(dict(tip=tip,label=label,role='query' if i<2 else 'reference',category='active (≥80%)' if i<2 else '',source='tested, inactive' if i<2 else ''))
    env=dict(os.environ,SAPOTE_PYTHON=sys.executable,GG_PRINT_WIDTH='7.2',GG_STRIPS='2',GG_STRIP_KIND='activity',GG_BLANK_MISSING='1',GG_STRIP1_TITLE='Activity A',GG_STRIP2_TITLE='Activity B')
    env.update(extra)
    proc=subprocess.run(['Rscript',str(ROOT/'tools/ggtree_rect_heatmap.R'),str(tree),str(meta),str(prefix)],env=env,text=True,capture_output=True)
    assert proc.returncode==0,proc.stdout+proc.stderr
    return prefix,tips


def read_pdf(path):
    python=os.environ.get('PDF_CHECK_PYTHON',sys.executable)
    code='import json,pdfplumber,sys;\np=pdfplumber.open(sys.argv[1]);print(json.dumps([dict(width=x.width,height=x.height,chars=x.chars,text=x.extract_text(),lines=x.lines,words=x.extract_words()) for x in p.pages]))'
    proc=subprocess.run([python,'-c',code,str(path)],text=True,capture_output=True)
    assert proc.returncode==0,proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_long_grouped_label_default_has_no_clipped_glyphs(tmp_path):
    prefix,tips=render_direct(tmp_path,long_label=True)
    pages=read_pdf(prefix.with_suffix('.pdf'))
    assert '600 shared sites)' in pages[0]['text']
    assert all(0<=c['x0']<=c['x1']<=pages[0]['width'] for c in pages[0]['chars'])
    from PIL import Image
    with Image.open(prefix.with_suffix('.png')) as im:assert min(im.info['dpi'])>=299
