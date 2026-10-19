"""Real two-file toy partition/convergence; no bundle cut or broader suite."""
from pathlib import Path
import sys
from tests.test_release_partition_manifest import modules,source_fixture,digest

def test_selected_wrapper_binds_real_baseline_convergence_and_readonly_final(modules,tmp_path):
    runner,manifest=modules
    wrapper=tmp_path/'selected wrapper';wrapper.write_text('#!'+sys.executable+'\nimport os,sys\nos.execv('+repr(sys.executable)+',['+repr(sys.executable)+',*sys.argv[1:]])\n');wrapper.chmod(0o755)
    source=source_fixture(tmp_path)
    measured=runner.PartitionRunner(source,tmp_path/'baseline',str(wrapper),files_per_partition=2,baseline=True).run()
    assert measured['totals']['main_counts']=={'failed':1,'passed':2,'skipped':1}
    baseline=tmp_path/'baseline/partition.json';before=runner.source_digest(source)
    args=['--root',str(source),'--fixed-point','--partition-baseline',str(baseline),
          '--partition-receipt-sha256',digest(baseline),'--partition-admission',str(tmp_path/'bad-selection')]
    assert manifest.main([*args,'--python',sys.executable])==2
    assert runner.source_digest(source)==before
    args[args.index(str(tmp_path/'bad-selection'))]=str(tmp_path/'bound-selection')
    assert manifest.main([*args,'--python',str(wrapper)])==0
    assert 'PASS (3 passed, 2 skipped; receipt-bound partitioned profile)' in (source/'RELEASE_MANIFEST.md').read_text()
    final=tmp_path/'final';green=runner.PartitionRunner(source,final,str(wrapper),files_per_partition=2).run()
    assert green['totals']['main_counts']=={'passed':3,'skipped':1}
    receipt=final/'partition.json';before=runner.source_digest(source)
    assert manifest.main(['--root',str(source),'--check','--python',str(wrapper),'--partition-receipt',str(receipt),
        '--partition-receipt-sha256',digest(receipt),'--partition-admission',str(tmp_path/'final-admission')])==0
    assert runner.source_digest(source)==before
