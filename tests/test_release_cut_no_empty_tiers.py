"""No selected tier means no completed cut, even when all prior gates were green."""
import os
from pathlib import Path
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]


def _run(tmp_path,tiers,child=None):
    text=(ROOT/'tools/release_cut.sh').read_text()
    function='build_tiers(){'+text.split('\nbuild_tiers(){',1)[1].split('\n}\n',1)[0]+'\n}\n'
    source=tmp_path/'source';(source/'tools').mkdir(parents=True)
    output=tmp_path/'out';output.mkdir()
    temp=tmp_path/'temp';temp.mkdir()
    if child is not None:(source/'tools/make_public_tier.sh').write_text(child)
    script='set -euo pipefail\nsay(){ printf "=== %s ===\\n" "$*"; }; die(){ printf "ABORT: %s\\n" "$*" >&2; exit 1; }\nregistry_preflight(){ :; }\nREGISTRY_ARGS=(fixture-only-binding)\nrm(){ :; }\n'+function+'\nVER=0.0.1; STAMP=synthetic; SRC="$1"; OUT="$2"; cd "$SRC"; build_tiers\n'
    env=dict(os.environ,CUT_TIERS=tiers,TMPDIR=str(temp),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run(['bash','-s','--',str(source),str(output)],input=script,text=True,capture_output=True,env=env,timeout=5)
    return result,output


@pytest.mark.parametrize('tiers',[' ','\t',' \t '])
def test_empty_tier_selection_cannot_report_completion(tmp_path,tiers):
    result,output=_run(tmp_path,tiers)
    assert result.returncode!=0
    assert 'CUT_TIERS must select at least one tier' in result.stderr
    assert 'done' not in result.stdout
    assert not (output/'SHA256SUMS.txt').exists()


@pytest.mark.parametrize('child',['echo synthetic-prerequisite-refusal; exit 7\n','kill -INT $$\n'])
def test_failed_or_interrupted_tier_child_never_reports_done(tmp_path,child):
    result,output=_run(tmp_path,'code',child)
    assert result.returncode!=0
    assert 'done' not in result.stdout
    assert (output/'code/_cutlog.txt').exists()
    assert not (output/'SHA256SUMS.txt').exists()
