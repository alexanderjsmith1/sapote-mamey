"""Disk sampler: a file listed and then removed before stat() is counted, never fatal.

Synthetic files and fake process interfaces only; nothing native runs.
Fail-before: the .463 disk_size raised FileNotFoundError and the run ended as SUPERVISOR_ERROR.
"""
import hashlib,importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('disk_sampler_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a);m=a.owned_module('ripper_lifecycle');PROFILE=json.loads((ROOT/'tools/ripper_source_profile.json').read_text())
TRANSIENT='SYNTHETIC_VOLUME.00.nsq'


class FakeError(Exception):pass
class FakeNoSuch(FakeError):pass
class FakeZombie(FakeError):pass
class FakeDenied(FakeError):pass


class Child:
    pid=918274
    def __init__(self):self.returncode=0
    def poll(self):return self.returncode
    def kill(self):self.returncode=-9
    def wait(self,timeout=None):return self.returncode


def walk_removing(target):
    """os.walk that removes target after it is listed and before the caller can stat it."""
    real=os.walk
    removed=[]
    def walk(top,*args,**kwargs):
        for here,dirs,files in real(top,*args,**kwargs):
            if target in files and (Path(here)/target).exists():
                (Path(here)/target).unlink();removed.append(str(Path(here)/target))
            yield here,dirs,files
    return walk,removed


class DiskSamplerVanishingFiles(unittest.TestCase):
    def setUp(self):
        self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())))

    def test_disk_size_counts_a_file_removed_between_listing_and_stat(self):
        root=self.work/'run';(root/'blastdb').mkdir(parents=True)
        (root/'kept.tsv').write_bytes(b'x'*7);(root/'blastdb'/TRANSIENT).write_bytes(b'y'*100)
        walk,removed=walk_removing(TRANSIENT);observations={'vanished_file_samples':0}
        with patch.object(m.os,'walk',walk):total=m.disk_size(root,observations)
        self.assertEqual(len(removed),1)
        self.assertEqual(total,7)
        self.assertEqual(observations['vanished_file_samples'],1)

    def test_disk_size_without_observations_still_survives_the_race(self):
        root=self.work/'run';root.mkdir()
        (root/'kept.tsv').write_bytes(b'x'*3);(root/TRANSIENT).write_bytes(b'y'*50)
        walk,removed=walk_removing(TRANSIENT)
        with patch.object(m.os,'walk',walk):total=m.disk_size(root)
        self.assertEqual((len(removed),total),(1,3))

    def test_symlink_is_still_refused(self):
        root=self.work/'run';root.mkdir();(root/'link').symlink_to(self.work)
        with self.assertRaisesRegex(ValueError,'RUNNER_OUTPUT_SYMLINK_REFUSED'):m.disk_size(root,{'vanished_file_samples':0})

    def test_lifecycle_records_the_vanished_file_and_keeps_the_stub_outcome(self):
        roles={}
        for role in ('python_runtime','stub_script','config'):
            p=self.work/role;p.write_text('SYNTHETIC_FAKE_PROCESS_ONLY\n');roles[role]=p
        roles['python_runtime'].chmod(0o700)
        spec={'schema_version':'ripper-lifecycle-spec/1','mode':'synthetic_stub','profile_id':PROFILE['id'],'source_revision':PROFILE['revision'],
              'files':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in roles.items()},
              'limits':{'wall_seconds':1,'rss_bytes':1024**2,'disk_bytes':2*1024**2,'poll_seconds':0.01}}
        spec_path=self.work/'spec.json';spec_path.write_text(json.dumps(spec));root=self.work/'run';child=Child()
        def launch(*args,**kwargs):
            (root/'result.tsv').write_text('\t'.join(PROFILE['headers'])+'\n');(root/TRANSIENT).write_bytes(b'z'*64);return child
        def kill_group(*args):raise ProcessLookupError('SYNTHETIC_GROUP_ABSENT')
        proc=lambda pid:SimpleNamespace(children=lambda recursive:[],memory_info=lambda:SimpleNamespace(rss=1))
        psutil=SimpleNamespace(__version__='SYNTHETIC_FAKE_PROCESS',Process=proc,Error=FakeError,NoSuchProcess=FakeNoSuch,ZombieProcess=FakeZombie,AccessDenied=FakeDenied)
        walk,removed=walk_removing(TRANSIENT)
        with patch.dict(sys.modules,{'psutil':psutil}),patch.object(m.subprocess,'Popen',launch),patch.object(m.os,'killpg',kill_group),patch.object(m.os,'walk',walk):
            d=m.lifecycle(a.binding_api(),spec_path,[k+'='+str(p) for k,p in roles.items()],root,execute_stub=True)
        self.assertEqual(len(removed),1)
        self.assertNotEqual(d.get('reason'),'SUPERVISOR_ERROR',d.get('error'))
        self.assertEqual(d['status'],'NO_HIT')
        self.assertEqual(d['disk_sampling_observations']['vanished_file_samples'],1)
        self.assertNotIn(TRANSIENT,d['retained_outputs'])
        self.assertEqual(json.loads((root/'TERMINAL.json').read_text())['disk_sampling_observations']['vanished_file_samples'],1)
        self.assertFalse(d['biological_absence_inferred'])


if __name__=='__main__':
    unittest.main()
