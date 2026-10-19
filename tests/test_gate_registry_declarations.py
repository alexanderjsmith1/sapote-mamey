"""Record classification controls must not become the gate's own wiring proof."""
import importlib.util
import os
from pathlib import Path
import re
ROOT=Path(os.environ.get('LANE08_SOURCE_ROOT',Path(__file__).resolve().parents[1]))
TARGET='_'.join(('synthetic','id','registry','guard'))
WRAPPER='_'.join(('verify','export','registry'))
SPEC=importlib.util.spec_from_file_location('lane08_gate_record_meta',ROOT/'tests/test_gate_wiring_invariant.py')
meta=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(meta)

def test_declared_record_is_wired_unique_and_has_real_runtime_chain():
    for tool in (TARGET,WRAPPER):
        rows=[line.split('\t') for line in (ROOT/'tools/gate_registry.tsv').read_text().splitlines() if line.split('\t')[0]==tool]
        assert len(rows)==1 and rows[0][1]=='WIRED'
        assert tool in meta._gate_tools() and meta._is_referenced(tool)
    release=(ROOT/'tools/release_cut.sh').read_text();export=(ROOT/'tools/make_public_tier.sh').read_text();wrapper=(ROOT/'tools'/(WRAPPER+'.py')).read_text()
    assert '--synthetic-registry' in release and WRAPPER+'.py' in export
    assert TARGET+'.py' in wrapper and 'module.audit(' in wrapper


def test_record_controls_do_not_count_as_target_wiring():
    for tool in (TARGET,WRAPPER):
        assert re.search(r'\b'+re.escape(tool)+r'\b',Path(__file__).read_text()) is None


def test_lost_reference_still_produces_wired_orphan(tmp_path):
    tests=tmp_path/'tests';tools=tmp_path/'tools';tests.mkdir();tools.mkdir();reference=tests/'test_direct_reference.py'
    reference.write_text('import '+TARGET+'\n')
    registry={TARGET:('WIRED','fixture-only classification')}
    assert meta.find_wired_orphans(registry=registry,tests_dir=tests,tools_dir=tools)==[]
    reference.write_text('# unrelated fixture after reference loss\n')
    assert meta.find_wired_orphans(registry=registry,tests_dir=tests,tools_dir=tools)==[{'tool':TARGET,'code':'WIRED_ORPHAN'}]
