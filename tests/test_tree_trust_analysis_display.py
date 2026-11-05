import hashlib
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

path = Path(__file__).resolve().parents[1]/'tools/tree_trust_audit.py'
spec = importlib.util.spec_from_file_location('candidate_tree_audit', path)
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)

class AuditIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'display.nwk').write_text('(A:0.1,B:0.1);')
        (self.root/'metadata.tsv').write_text('tip\tlabel\nA\tA\nB\tB\n')
        self.entry={'tree':'display.nwk','metadata':'metadata.tsv','outgroups':['B']}
    def binding(self,text):
        p=self.root/'analysis.nwk';p.write_text(text)
        return {'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    def check(self): return audit.audit(self.entry,self.root)['checks']
    def test_existing_contract_unchanged_when_absent(self):
        self.assertNotIn('analysis_display_roster',self.check())
    def test_exact_join_and_render_gate_hold(self):
        self.entry['analysis_tree']=self.binding('(A,B);')
        checks=self.check()
        self.assertEqual(checks['analysis_display_roster']['status'],'PASS')
        self.assertEqual(checks['gate']['status'],'UNVERIFIED')
        self.assertEqual(checks['render_binding']['status'],'UNVERIFIED')
    def test_gate_success_does_not_bind_manifest_outgroups(self):
        self.entry['analysis_tree']=self.binding('(A,B);')
        gate=self.root/'gate.py'; gate.write_text('raise SystemExit(0)\n')
        result=audit.audit(self.entry,self.root,gate_path=gate)
        self.assertEqual(result['checks']['outgroup_membership']['status'],'PASS')
        self.assertEqual(result['checks']['gate']['status'],'PASS')
        self.assertEqual(result['checks']['gate_outgroup_binding']['status'],'UNVERIFIED')
        self.assertEqual(result['verdict'],'UNVERIFIED')

    def test_display_subset_is_unverified(self):
        self.entry['analysis_tree']=self.binding('(A,B,C);')
        result=self.check()['analysis_display_roster']
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertEqual(json.loads(result['detail'])['analysis_missing_from_display'],['C'])
    def test_new_display_tip_is_fail(self):
        self.entry['analysis_tree']=self.binding('(A,C);')
        self.assertEqual(self.check()['analysis_display_roster']['status'],'FAIL')
    def test_missing_and_mismatched_binding_fail_closed(self):
        self.entry['analysis_tree']=self.binding('(A,B);');self.entry['analysis_tree']['sha256']='0'*64
        self.assertEqual(self.check()['analysis_display_roster']['status'],'FAIL')
        self.entry['analysis_tree']=None
        self.assertEqual(self.check()['analysis_display_roster']['status'],'UNVERIFIED')
    def test_display_change_during_roster_comparison_is_refused(self):
        self.entry['analysis_tree'] = self.binding('(A,B);')
        original = audit._tips_and_sha
        def parse_then_modify(path):
            result = original(path)
            Path(path).write_text('(A,C);')
            return result
        with patch.object(audit, '_tips_and_sha', side_effect=parse_then_modify):
            result = self.check()['analysis_display_roster']
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('changed during', result['detail'])
    def test_metadata_hash_binds_the_bytes_parsed_despite_change(self):
        metadata = self.root/'metadata.tsv'
        original_bytes = metadata.read_bytes()
        changed = b'tip\tlabel\nA\tchanged\nB\tB\n'
        render = self.root/'figure.png'; render.write_bytes(b'example render')
        receipt = {'tree_sha256':hashlib.sha256((self.root/'display.nwk').read_bytes()).hexdigest(),
                   'metadata_sha256':hashlib.sha256(changed).hexdigest(),
                   'render_sha256':hashlib.sha256(render.read_bytes()).hexdigest()}
        (self.root/'receipt.json').write_text(json.dumps(receipt))
        self.entry.update(render='figure.png', render_receipt='receipt.json')
        original_read = Path.read_bytes
        changed_once = False
        def mutate_after_read(path):
            nonlocal changed_once
            raw = original_read(path)
            if path == metadata and not changed_once:
                changed_once = True
                metadata.write_bytes(changed)
            return raw
        with patch.object(Path, 'read_bytes', mutate_after_read):
            result = audit.audit(self.entry, self.root)
        self.assertTrue(changed_once)
        self.assertEqual(result['metadata_sha256'], hashlib.sha256(original_bytes).hexdigest())
        self.assertEqual(result['checks']['metadata']['status'], 'PASS')
        self.assertEqual(result['checks']['render_binding']['status'], 'FAIL')

    def test_duplicate_receipt_keys_do_not_bind(self):
        (self.root/'figure.png').write_bytes(b'example')
        (self.root/'receipt.json').write_text('{"tree_sha256":"bad", "tree_sha256":"other"}')
        self.entry.update(render='figure.png', render_receipt='receipt.json')
        result=self.check()['render_binding']
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIn('duplicate JSON key', result['detail'])

    def test_duplicate_manifest_keys_are_refused(self):
        manifest=self.root/'manifest.json'
        manifest.write_text('{"trees":[], "trees":[{}]}')
        self.assertEqual(audit.main(['--manifest',str(manifest),'--output',str(self.root/'out.json')]),2)
        self.assertFalse((self.root/'out.json').exists())

    def test_display_malformed_newick_does_not_crash(self):
        (self.root/'display.nwk').write_text('(A,B);(C,D);')
        self.assertEqual(self.check()['tree']['status'], 'FAIL')
    def test_invalid_analysis_tree(self):
        for tree in ('(A,A);','(A,B)','(A,B);(C,D);'):
            self.entry['analysis_tree']=self.binding(tree)
            self.assertEqual(self.check()['analysis_display_roster']['status'],'FAIL')

if __name__=='__main__': unittest.main()
