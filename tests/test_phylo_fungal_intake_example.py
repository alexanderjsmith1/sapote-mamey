import json
from pathlib import Path
import subprocess
import sys


def test_unedited_fungal_example_is_valid_json_but_not_an_admitted_roster():
    root = Path(__file__).resolve().parents[1]
    example = root / 'examples/phylo_fungal_intake.example.json'
    manifest = json.loads(example.read_text())
    assert manifest['group'] == 'fungi'
    assert set(manifest['fungal_registry']['selection']) == {'tree_scope', 'ingroup_taxon', 'accession'}
    result = subprocess.run([sys.executable, str(root/'tools/phylo_crossgroup_intake.py'), str(example), '--allow-root', str(root)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 2
    assert json.loads(result.stdout)['status'] == 'ERROR'
