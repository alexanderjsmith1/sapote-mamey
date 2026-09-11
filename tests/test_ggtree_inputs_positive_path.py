from pathlib import Path
import os
import subprocess
import sys


def test_valid_tree_still_writes_outputs(tmp_path):
    from Bio import Phylo
    tree = tmp_path / 'input.nwk'
    tree.write_text('((RefA:0.1,RefB:0.2):0.3,outgroup_X:0.4);\n')
    hosts = tmp_path / 'hosts.tsv'
    hosts.write_text('strain\thost_raw\n')
    prefix = tmp_path / 'result'
    tool = Path(__file__).resolve().parents[1] / 'tools/build_placement_ggtree_inputs.py'
    result = subprocess.run([sys.executable, str(tool), '--graft', str(tree), '--host-table', str(hosts),
                             '--out-prefix', str(prefix), '--keep-all-refs'], cwd=tmp_path,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert len(Phylo.read(str(prefix) + '_pruned.nwk', 'newick').get_terminals()) == 3
    assert len(Path(str(prefix) + '_ggtree_annotation.tsv').read_text().splitlines()) == 4
