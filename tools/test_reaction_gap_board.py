import copy, importlib.util, unittest, tempfile, json
from types import SimpleNamespace
from pathlib import Path
s=importlib.util.spec_from_file_location('board',Path(__file__).with_name('reaction_gap_board.py'));b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
def fixture():
    ids={a:f'TEST / contig_{a} / region001 / {a}' for a in ('A','B')}
    pair=dict(bgc_a='A',bgc_b='B',exact_identity_a=ids['A'],exact_identity_b=ids['B'],shared_product_tokens='nrps',good_geometry_references=1,complementary_disjoint_refs=1,supporting_references=2)
    return {'input':{'identity_map':ids,'input_bgcs':[dict(bgc_id=a,contig='contig_'+a,antismash_region='region001',start=1,end=100,contig_length=100) for a in ids]},'result':{'ranked_pairs':[pair]}}
class Tests(unittest.TestCase):
    def test_good_boundary(self):b.validate_partition(fixture(),'TEST')
    def test_identity_missing(self):
        with self.assertRaises(ValueError):b.identity('TEST / A')
    def test_wrong_assembly(self):
        d=fixture();d['input']['input_bgcs'][0]['contig']='wrong'
        with self.assertRaises(ValueError):b.validate_partition(d,'TEST')
    def test_mixed_population(self):
        with self.assertRaises(ValueError):b.validate_partition(fixture(),'OTHER')
    def test_duplicate(self):
        d=fixture();d['result']['ranked_pairs']*=2
        with self.assertRaises(ValueError):b.validate_partition(d,'TEST')
    def test_unmeasured_not_zero(self):
        d=fixture();d['result']['ranked_pairs'][0]['good_geometry_references']=None
        with self.assertRaises(ValueError):b.validate_partition(d,'TEST')
    def test_denominator(self):
        d=fixture();d['result']['ranked_pairs'][0]['good_geometry_references']=3
        with self.assertRaises(ValueError):b.validate_partition(d,'TEST')
    def test_no_class_no_candidate(self):
        d=fixture();d['result']['ranked_pairs'][0]['shared_product_tokens']='';self.assertEqual(b.select(d),[])
    def test_boundary_overflow(self):
        d=fixture();d['input']['input_bgcs'][0]['end']=101
        with self.assertRaises(ValueError):b.validate_partition(d,'TEST')
    def test_no_auto_reaction_assignment(self):self.assertNotIn('reaction',b.select(fixture())[0][1])
    def test_dependency_tamper_refusals(self):
        for changed in ('manifest','database','reader'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as td:
                root=Path(td);(root/'methods_and_receipts').mkdir()
                db=root/'small.sqlite';db.write_bytes(b'generic fixture')
                reader=root/'methods_and_receipts/read_rggmci_database.py';reader.write_text('# fixture')
                manifest=root/'RELEASE_MANIFEST.json';manifest.write_text(json.dumps({'database':db.name,'database_sha256':b.sha(db),'files':[{'path':'methods_and_receipts/read_rggmci_database.py','sha256':b.sha(reader)}]}))
                pin=b.sha(manifest)
                target={'manifest':manifest,'database':db,'reader':reader}[changed]
                target.write_bytes(target.read_bytes()+b'changed')
                with self.assertRaisesRegex(ValueError,'hash mismatch'):
                    b.build(SimpleNamespace(source=root,manifest_sha256=pin,contract=root/'contract',output=root/'output',pilot=True,strain=None))
if __name__=='__main__':unittest.main()
