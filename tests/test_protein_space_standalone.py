"""Checks for single-file packaging; no sequence analyses or external assets."""
import base64,gzip,hashlib,importlib.util,json,re,unittest,os,tempfile
from pathlib import Path
from html.parser import HTMLParser

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('standalone',HERE/'tools/protein_space_standalone.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
VIEWER=os.environ.get('SAPOTE_STANDALONE_VIEWER');CATALOGUE=os.environ.get('SAPOTE_STANDALONE_CATALOGUE')
class Resources(HTMLParser):
 def __init__(self):super().__init__();self.external=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='script' and a.get('src'):self.external.append(a['src'])
  if tag=='link' and a.get('rel')=='stylesheet' and a.get('href'):self.external.append(a['href'])

class ReaderContract(unittest.TestCase):
 def test_plain_and_gzip_data(self):
  obj={'schema':'example','values':[1,2,3]};raw=json.dumps(obj);encoded=base64.b64encode(gzip.compress(raw.encode())).decode()
  self.assertEqual(M.read_data('<script id="data" type="application/json">'+raw+'</script>'),obj)
  self.assertEqual(M.read_data('<script id="data" data-encoding="gzip">'+encoded+'</script>'),obj)
 def test_existing_payload_needs_no_external_asset(self):
  value=base64.b64encode(gzip.compress(b'{"regions":{}}')).decode()
  with tempfile.TemporaryDirectory() as td:self.assertEqual(M.packed_assets(Path(td),{'AS-1':'missing.js'},{'AS-1':value}),{'AS-1':value})
 def test_payload_roster_mismatch_refused(self):
  with self.assertRaises(ValueError):M.packed_assets(Path('.'),{},{'AS-1':'unbound'})
 def test_escaping_asset_path_refused_before_read(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(ValueError):M.packed_assets(Path(td),{'AS-1':'../private.js'},{})

@unittest.skipUnless(VIEWER and CATALOGUE,'Set SAPOTE_STANDALONE_VIEWER and SAPOTE_STANDALONE_CATALOGUE for the retained 70-layout/970-comparison fixture')
class Standalone(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.vtext=Path(VIEWER).read_text();cls.ctext=Path(CATALOGUE).read_text();cls.v=M.read_data(cls.vtext);cls.c=M.read_data(cls.ctext)
 def test_no_external_scripts_styles_or_font_urls(self):
  for text in [self.vtext,self.ctext]:
   p=Resources();p.feed(text);self.assertEqual(p.external,[])
   css=re.search(r'<style id="offline-fonts">(.*?)</style>',text,re.S)[1]
   self.assertNotIn('https:',css);self.assertEqual(css.count('data:font/ttf;base64,'),5)
 def test_every_declared_asset_is_embedded(self):
  self.assertTrue(self.v['standalone']);self.assertTrue(self.c['standalone'])
  self.assertEqual(set(self.v['region_payloads']),set(self.v['region_files']));self.assertEqual(len(self.v['region_payloads']),44)
  self.assertEqual(set(self.v['reference_payloads']),set(self.v['reference_files']));self.assertEqual(self.v['reference_payloads'],self.c['reference_payloads'])
 def test_all_reference_evidence_decodes_without_sidecar_files(self):
  comps=genes=0
  for packed in self.c['reference_payloads'].values():
   payload=json.loads(gzip.decompress(base64.b64decode(packed)))
   comps+=len(payload['comparisons']);genes+=sum(len(c['genes']) for c in payload['comparisons'].values())
  self.assertEqual((comps,genes),(970,28595))
 def test_all_whole_region_genes_decode_without_sidecar_files(self):
  regions=genes=0
  for packed in self.v['region_payloads'].values():
   payload=json.loads(gzip.decompress(base64.b64decode(packed)));regions+=len(payload['regions']);genes+=sum(len(r['cds']) for r in payload['regions'].values())
  self.assertEqual((regions,genes),(2435,54739))
 def test_point_fingerprint_and_comparison_roster_preserved(self):
  self.assertEqual(len(self.v['sets']),70);self.assertEqual(sum(len(s['pts']) for s in self.v['sets']),152571)
  fp=hashlib.sha256(json.dumps([s['pts'] for s in self.v['sets']],separators=(',',':')).encode()).hexdigest()
  self.assertEqual(fp,'ec70c8782b9e054efa0f6b9dec6ff4a3c1855a4aa01941b0aa468fd2b6799c18')
  self.assertEqual(len(self.c['rows']),970);self.assertEqual(len(self.c['coverage']),45)
 def test_embedded_source_exports_and_licenses(self):
  self.assertIn('SOURCE_BINDINGS.tsv',self.v['offline_exports']);self.assertIn('SOURCE_BINDINGS.tsv',self.c['offline_exports'])
  self.assertIn('MIT License',self.vtext);self.assertIn('SIL OPEN FONT LICENSE',self.ctext)

if __name__=='__main__':unittest.main()
