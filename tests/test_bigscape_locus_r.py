"""Critical coordinate/refusal tests; no external biological searches."""
import importlib.util,json,os,sqlite3,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
module_path=Path(os.environ['BIGSCAPE_LOCUS_R_SOURCE']) if 'BIGSCAPE_LOCUS_R_SOURCE' in os.environ else HERE/'bigscape_locus_r.py'
if 'BIGSCAPE_LOCUS_R_SOURCE' not in os.environ and not module_path.exists():module_path=HERE.parent/'tools/bigscape_locus_r.py'
spec=importlib.util.spec_from_file_location('bigscape_locus_r',module_path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class CoordinateAndReadOnlyTests(unittest.TestCase):
    def test_reverse_stored_B_and_exclusive_stop(self):
        cds=[{'nt_start':10,'nt_stop':20},{'nt_start':30,'nt_stop':40},{'nt_start':50,'nt_stop':70}]
        self.assertEqual(m.span_coordinates(cds,0,2,reverse=True),(30,70))
        self.assertEqual(m.span_coordinates(cds,1,3),(30,70))
        self.assertEqual(m.span_coordinates(cds,1,2,reverse=True),(30,40))
    def test_invalid_boundaries_refuse(self):
        for start,stop in [(0,0),(-1,1),(0,2),(1,0)]:
            with self.assertRaises(ValueError):m.span_coordinates([{'nt_start':10,'nt_stop':20}],start,stop)
    def test_existing_destination_preserved(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            p=Path(tmp)/'existing';p.mkdir();f=p/'retain.txt';f.write_text('prior result')
            with self.assertRaises(ValueError):m.require_fresh(p)
            self.assertEqual(f.read_text(),'prior result')
    def test_symlink_destination_refuses(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            p=Path(tmp);(p/'target').mkdir();(p/'alias').symlink_to(p/'target')
            with self.assertRaises(ValueError):m.require_fresh(p/'alias')
    def test_source_database_cannot_be_written(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            p=Path(tmp)/'source.db';c=sqlite3.connect(p);c.execute('create table evidence(value text)');c.commit();c.close();before=m.sha(p)
            c=m.read_only(p)
            with self.assertRaises(sqlite3.OperationalError):c.execute("insert into evidence values ('changed')")
            c.close();self.assertEqual(m.sha(p),before)
    def test_refresh_checks_prior_outputs_before_replacement(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root=Path(tmp);db=root/'source.db';db.write_text('bound database');selected=root/'selected.json';selected.write_text('{}')
            out=root/'render';out.mkdir();image=out/'figure.svg';image.write_text('prior artwork')
            receipt={'status':'COMPLETE','source_bindings':[{'path':str(db),'sha256':m.sha(db)},{'path':str(selected),'sha256':m.sha(selected)}],'outputs':{'figure.svg':{'sha256':m.sha(image),'bytes':image.stat().st_size}}}
            (out/'PROTOTYPE_RECEIPT.json').write_text(json.dumps(receipt))
            self.assertEqual(m.checked_refresh(out,db,selected)['status'],'COMPLETE')
            image.write_text('operator change')
            with self.assertRaises(ValueError):m.checked_refresh(out,db,selected)
            self.assertEqual(image.read_text(),'operator change')
    def test_refresh_cannot_change_scientific_inputs(self):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            root=Path(tmp);db=root/'source.db';db.write_text('old input');selected=root/'selected.json';selected.write_text('{}')
            out=root/'render';out.mkdir();receipt={'status':'COMPLETE','source_bindings':[{'path':str(db),'sha256':m.sha(db)},{'path':str(selected),'sha256':m.sha(selected)}],'outputs':{}}
            (out/'PROTOTYPE_RECEIPT.json').write_text(json.dumps(receipt));db.write_text('different input')
            with self.assertRaises(ValueError):m.checked_refresh(out,db,selected)

if __name__=='__main__':unittest.main()
