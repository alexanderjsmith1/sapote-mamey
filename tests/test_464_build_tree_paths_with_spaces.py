"""Card 464_build_tree_paths_with_spaces: GToTree reads its genome list with `for file in $(cat ...)`.

That loop splits on whitespace, and the documented tree home has spaces in its path, so absolute list
entries broke late inside GToTree. The list now holds entries relative to the tree folder, and names
or a TMPDIR that cannot pass through are refused before any engine runs.
"""
import json,subprocess
from pathlib import Path
from ._python_fixture_launcher import write_python_fixture
from .test_447_build_tree_bound_retention import prepare

# A GToTree stand-in that resolves the list the way the real script does: one token per whitespace run.
SPLITTING_GTOTREE = """from pathlib import Path
import sys
listing=sys.argv[sys.argv.index('-f')+1]
tokens=Path(listing).read_text().split()
missing=[t for t in tokens if not Path(t).is_file()]
if missing:
    sys.stderr.write('Some fasta files specified cannot be found: %s\\n' % missing);raise SystemExit(0)
out=Path('gtotree');out.mkdir(exist_ok=True)
(out/'Aligned_SCGs.faa').write_text(''.join('>'+Path(t).stem+'\\nFAKE\\n' for t in tokens))
(out/'gtotree-runlog.txt').write_text('No genomes were removed due to having too few SCG hits')
"""


def _spaced(tmp_path):
    root=tmp_path/'AS Strain Master'/'tree home';root.mkdir(parents=True)
    tools,tree,env=prepare(root)
    write_python_fixture(root/'bin'/'GToTree',SPLITTING_GTOTREE)
    return tools,tree,env


def test_tree_folder_with_spaces_reaches_iqtree(tmp_path):
    tools,tree,env=_spaced(tmp_path)
    r=subprocess.run(['bash',str(tools/'build_tree.sh'),str(tree)],env=env,text=True,capture_output=True)
    assert r.returncode==0,r.stdout+r.stderr
    assert (tree/'iqtree_called').exists()
    assert (tree/'genome_list.txt').read_text().split()==['genomes/FIX_OUTGROUP.fna','genomes/QUERY.fna','genomes/REF.fna']
    binding=json.loads((tree/'tree_input_binding.json').read_text())
    assert len(binding['inputs'])==3
    assert json.loads((tree/'tree_retention_status.json').read_text())['status']=='TIPS_RETAINED'


def test_genome_name_with_whitespace_is_refused_before_engines(tmp_path):
    tools,tree,env=_spaced(tmp_path)
    (tree/'genomes'/'REF.fna').rename(tree/'genomes'/'REF copy.fna')
    r=subprocess.run(['bash',str(tools/'build_tree.sh'),str(tree)],env=env,text=True,capture_output=True)
    assert r.returncode!=0 and 'TREE_GENOME_NAME_HAS_WHITESPACE' in r.stderr and 'REF copy.fna' in r.stderr
    assert not (tree/'gtotree').exists() and not (tree/'iqtree_called').exists()


def test_tmpdir_with_whitespace_is_refused_before_engines(tmp_path):
    tools,tree,env=_spaced(tmp_path)
    spaced_tmp=tmp_path/'tmp with space';spaced_tmp.mkdir()
    env=dict(env,TMPDIR=str(spaced_tmp))
    r=subprocess.run(['bash',str(tools/'build_tree.sh'),str(tree)],env=env,text=True,capture_output=True)
    assert r.returncode==2 and 'TREE_TMPDIR_HAS_WHITESPACE' in r.stderr
    assert not (tree/'gtotree').exists()
