"""Actual shell wrapper with synthetic files and mocked external engine executables."""
import importlib.util,json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_bound',ROOT/'tools/build_tree_retention.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def prepare(tmp_path,drop_query=False,drop_ref=False,allow_ref=False,final_drop=False):
    repo=tmp_path/'repo';tools=repo/'tools';tools.mkdir(parents=True)
    for name in ('build_tree.sh','build_tree_retention.py','gtotree_execution_gate.py','_gtotree_versions.py'):
        shutil.copy2(ROOT/'tools'/name,tools/name)
    (tools/'phylo_preflight.py').write_text('raise SystemExit(0)\n')
    (tools/'gtotree_env.sh').write_text('export GToTree_HMM_dir="fixture-unused"\ngtotree_preflight() { return 0; }\n')
    py=repo/'miniconda3/envs/phylo/bin';py.mkdir(parents=True);(py/'python').symlink_to(sys.executable)
    binaries=tmp_path/'bin';binaries.mkdir()
    def executable(name,text):
        p=binaries/name;p.write_text('#!'+sys.executable+'\n'+text);p.chmod(0o755)
    executable('GToTree',"""from pathlib import Path
import os
out=Path('gtotree');out.mkdir(exist_ok=True)
names=['QUERY','REF','FIX_OUTGROUP']
if os.environ.get('DROP_QUERY'):names.remove('QUERY')
if os.environ.get('DROP_REF'):names.remove('REF')
(out/'Aligned_SCGs.faa').write_text(''.join('>'+n+'\\nFAKE\\n' for n in names))
(out/'gtotree-runlog.txt').write_text('No genomes were removed due to having too few SCG hits')
""")
    executable('iqtree',"""from pathlib import Path
import os
Path('iqtree_called').write_text('mock')
tips=[l[1:] for l in Path('gtotree/Aligned_SCGs.faa').read_text().splitlines() if l.startswith('>')]
if os.environ.get('FINAL_DROP'):tips.remove('QUERY')
tree='('+','.join(n+':1' for n in tips)+')99:1;'
Path('iqtree.treefile').write_text(tree);Path('iqtree.contree').write_text(tree)
Path('iqtree.log').write_text('Total wall-clock time: mock only')
""")
    tree=tmp_path/'tree';genomes=tree/'genomes';genomes.mkdir(parents=True)
    for n in ['QUERY','REF','FIX_OUTGROUP']:(genomes/(n+'.fna')).write_text('synthetic input '+n)
    (tree/'TREE_SPEC.json').write_text(json.dumps({'queries':['QUERY'],'allow_reference_drop':allow_ref}))
    env=dict(os.environ,PROJECT_ROOT=str(repo),PATH=str(binaries)+os.pathsep+os.environ['PATH'],PYTHONPATH=str(ROOT),PYTHONDONTWRITEBYTECODE='1')
    for key,value in [('DROP_QUERY',drop_query),('DROP_REF',drop_ref),('FINAL_DROP',final_drop)]:
        if value:env[key]='1'
        else:env.pop(key,None)
    return tools,tree,env

@pytest.mark.parametrize('drop_query,drop_ref,allow_ref,final_drop,expected',[(False,False,False,False,'TIPS_RETAINED'),(True,False,False,False,'QUERY_TIP_DROPPED'),(False,True,False,False,'REFERENCE_TIP_DROPPED'),(False,True,True,False,'REFERENCE_TIP_DROPPED_ALLOWED'),(False,False,False,True,'QUERY_TIP_DROPPED')])
def test_actual_shell_refuses_dropped_query_before_iqtree_and_checks_final(tmp_path,drop_query,drop_ref,allow_ref,final_drop,expected):
    tools,tree,env=prepare(tmp_path,drop_query,drop_ref,allow_ref,final_drop)
    r=subprocess.run(['bash',str(tools/'build_tree.sh'),str(tree)],env=env,text=True,capture_output=True)
    status=json.loads((tree/'tree_retention_status.json').read_text())
    assert status['status']==expected,r.stdout+r.stderr
    accepted=expected in ('TIPS_RETAINED','REFERENCE_TIP_DROPPED_ALLOWED')
    assert (r.returncode==0)==accepted
    if drop_query or (drop_ref and not allow_ref):assert not (tree/'iqtree_called').exists()
    if final_drop:assert (tree/'iqtree_called').exists() and 'tree complete' not in r.stdout
    if drop_query or drop_ref or final_drop:assert (tree/'DROPPED_BY_QC.tsv').exists()
    binding=json.loads((tree/'tree_input_binding.json').read_text());assert len(binding['inputs'])==3 and binding['queries']==['QUERY']

@pytest.mark.parametrize('override',['-f','-fother','-o','--output=elsewhere','-aother','-gother'])
def test_extra_args_cannot_replace_bound_inputs_or_output(tmp_path,override):
    tools,tree,env=prepare(tmp_path)
    r=subprocess.run(['bash',str(tools/'build_tree.sh'),str(tree),override],env=env,text=True,capture_output=True)
    assert r.returncode==2 and 'INPUT_OVERRIDE_REFUSED' in r.stderr and not (tree/'gtotree').exists()


def test_gate_missing_is_typed_refusal_before_engines(tmp_path):
    tools,tree,env=prepare(tmp_path);(tools/'gtotree_execution_gate.py').unlink()
    r=subprocess.run(['bash',str(tools/'build_tree.sh'),str(tree)],env=env,text=True,capture_output=True)
    assert r.returncode==3 and not (tree/'gtotree').exists()
    receipt=json.loads((tree/'tree_retention_status.json').read_text());assert receipt['status']=='TREE_RETENTION_GATE_REFUSED' and 'UNAVAILABLE' in receipt['error']


def test_source_mutation_refuses_postflight_even_when_tip_names_match(tmp_path):
    tools,tree,env=prepare(tmp_path)
    listing=tree/'genome_list.txt';listing.write_text(''.join(str(p)+'\n' for p in sorted((tree/'genomes').glob('*.fna'))))
    binding=tree/'tree_input_binding.json';gate=mod.load_gate(ROOT/'tools/gtotree_execution_gate.py')
    binding.write_text(json.dumps(mod.input_binding(listing,tree/'TREE_SPEC.json',gate)))
    out=tree/'gtotree';out.mkdir();(out/'Aligned_SCGs.faa').write_text('>QUERY\nFAKE\n>REF\nFAKE\n>FIX_OUTGROUP\nFAKE\n')
    (tree/'genomes/QUERY.fna').write_text('changed synthetic bytes')
    assert mod.check(binding,listing,tree/'TREE_SPEC.json',out,gate)['status']=='TREE_INPUT_BINDING_CHANGED'


def test_unexpected_alignment_tip_is_refused_even_without_missing_tips(tmp_path):
    tools,tree,env=prepare(tmp_path)
    listing=tree/'genome_list.txt';listing.write_text(''.join(str(p)+'\n' for p in sorted((tree/'genomes').glob('*.fna'))))
    binding=tree/'tree_input_binding.json';gate=mod.load_gate(ROOT/'tools/gtotree_execution_gate.py')
    binding.write_text(json.dumps(mod.input_binding(listing,tree/'TREE_SPEC.json',gate)))
    out=tree/'gtotree';out.mkdir();(out/'Aligned_SCGs.faa').write_text('>QUERY\nFAKE\n>REF\nFAKE\n>FIX_OUTGROUP\nFAKE\n>EXTRA\nFAKE\n')
    result=mod.check(binding,listing,tree/'TREE_SPEC.json',out,gate)
    assert result['status']=='TREE_TIP_UNEXPECTED' and result['unexpected']==['EXTRA']
