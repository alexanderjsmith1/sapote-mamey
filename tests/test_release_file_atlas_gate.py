"""Cut orchestration must regenerate and check the declared file atlas owner."""
import ast
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def test_atlas_owner_runs_before_maintenance_captures_document_bytes():
    text=(ROOT/'tools/release_cut.sh').read_text()
    prepare=text.split('prepare_release(){',1)[1].split('\n}\n',1)[0]
    atlas=prepare.find('tools/file_atlas.py --out docs/FILE_ATLAS.csv --md docs/FILE_ATLAS.md')
    assert atlas>=0
    assert atlas<prepare.index('tools/gen_tools_inventory.py --maintenance')


def test_prepare_stage_declares_both_atlas_mutations():
    tree=ast.parse((ROOT/'tools/release_workflow.py').read_text())
    value=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GENERATED_FILES' for t in n.targets))
    paths=ast.literal_eval(value)
    assert 'docs/FILE_ATLAS.csv' in paths and 'docs/FILE_ATLAS.md' in paths


def test_stale_or_unavailable_atlas_owner_cannot_advance_post_gates():
    text=(ROOT/'tools/release_cut.sh').read_text()
    function='post_test_gates(){'+text.split('\npost_test_gates(){',1)[1].split('\n}\n',1)[0]+'\n}\n'
    script='set -euo pipefail\nsay(){ :; }; die(){ printf "%s\\n" "$*" >&2; exit 1; }; assert_no_backup_debris(){ :; }; PYTHON=fixture_python; fixture_python(){ [[ "$*" != "tools/file_atlas.py --check" ]]; }; python3(){ fixture_python "$@"; };\n'+function+'\npost_test_gates\n'
    value=subprocess.run(['bash','-s'],input=script,capture_output=True,text=True,timeout=5)
    assert value.returncode!=0
    assert 'file atlas is stale or its freshness owner is unavailable' in value.stderr
