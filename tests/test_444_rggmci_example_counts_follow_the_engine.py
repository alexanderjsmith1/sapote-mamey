import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_generated_counts_match_engine(tmp_path):
    out=tmp_path/'repo'
    subprocess.run([sys.executable,str(ROOT/'packaging/rggmci/make_repo_candidate.py'),'--bundle',str(ROOT),'--out',str(out)],check=True,capture_output=True)
    expected=next((out/'examples').glob('*_expected_engine.json'))
    result=json.loads(expected.read_text())['result']
    claim=f"It gives {result['pairs_total']} scored pairs, {result['high_pairs']} of them HIGH."
    assert claim in (out/'examples/README.md').read_text()
