#!/usr/bin/env python3
"""Package retained protein-space displays as single-file offline HTML tools.

Consumes codex.protein_space.enriched.v1 data and a bound catalogue. No analysis,
sequence search, ordination or figure redraw. Python standard library only.
"""
import argparse,base64,csv,gzip,hashlib,json,re
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()
def read_data(text):
 m=re.search(r'<script id="data"([^>]*)>(.*?)</script>',text,re.S)
 if not m:raise ValueError('No data script in input HTML')
 return json.loads(gzip.decompress(base64.b64decode(m[2])) if 'data-encoding="gzip"' in m[1] else m[2])

def packed_assets(folder,files,existing):
 result=dict(existing or {})
 for strain,relative in files.items():
  if strain in result:continue
  path=(folder/relative).resolve()
  if not path.is_relative_to(folder.resolve()):raise ValueError('Detail asset escapes the input viewer directory')
  text=path.read_text();args=json.loads('['+text[text.index('(')+1:text.rindex(')')]+']')
  if len(args)!=2 or args[0]!=strain:raise ValueError('Packed asset strain mismatch: '+str(path))
  json.loads(gzip.decompress(base64.b64decode(args[1])))
  result[strain]=args[1]
 if set(result)!=set(files):raise ValueError('Embedded asset roster differs from declared roster')
 for encoded in result.values():
  payload=json.loads(gzip.decompress(base64.b64decode(encoded)))
  if not isinstance(payload,dict) or not any(isinstance(payload.get(k),dict) for k in ['regions','comparisons']):raise ValueError('Invalid embedded gene-detail schema')
 return result

def fonts(vendor):
 css=(vendor/'fonts.css').read_text();names=['jetbrains-mono-400.ttf','jetbrains-mono-600.ttf','public-sans-400.ttf','public-sans-600.ttf','public-sans-700.ttf']
 urls=re.findall(r'url\((https[^)]+)\)',css)
 if len(urls)!=len(names):raise ValueError('Unexpected pinned font manifest')
 for url,name in zip(urls,names):css=css.replace(url,'data:font/ttf;base64,'+base64.b64encode((vendor/name).read_bytes()).decode())
 return css

def safe_script(text):return re.sub(r'</script',r'<\/script',text,flags=re.I)

def package_html(source,D,reference_js,vendor,plotly=False):
 # Repack either a linked source template or an already standalone document.
 p=re.search(r'<script id="viewer-program"[^>]*>(.*?)</script>',source,re.S)
 if p:
  program=p[1].replace('<\\/script','</script');shell=source[:source.index('<script id="data"')]
  # Drop prior inline vendor/reader code from the shell when repacking.
  shell=re.sub(r'<script data-offline-vendor[^>]*>.*?</script>','',shell,flags=re.S)
 else:
  program=list(re.finditer(r'<script(?:\s[^>]*)?>(.*?)</script>',source,re.S))[-1][1]
  shell=source[:source.index('<script id="data"')]
 shell=re.sub(r'<script\b[^>]*src=[^>]*>.*?</script>','',shell,flags=re.S)
 shell=re.sub(r'<link\b[^>]*href="https://fonts.googleapis.com/[^>]*>','',shell)
 shell=re.sub(r'<style id="offline-fonts">.*?</style>','',shell,flags=re.S)
 program=re.sub(r'JSON\.parse\(document\.getElementById\(["\']data["\']\)\.textContent\)','window.STANDALONE_DATA',program)
 if 'window.STANDALONE_DATA' not in program:raise ValueError('Input program does not use the expected data contract')
 encoded=base64.b64encode(gzip.compress(json.dumps(D,separators=(',',':')).encode(),mtime=0)).decode()
 licenses='\n\n'.join((vendor/n).read_text() for n in ['PLOTLY_LICENSE.txt','PUBLIC_SANS_OFL.txt','JETBRAINS_MONO_OFL.txt'])
 vendor_js='<script data-offline-vendor="plotly">'+safe_script((vendor/'plotly-gl3d-2.27.0.min.js').read_text())+'</script>\n' if plotly else ''
 bootstrap="""(async()=>{try{if(typeof DecompressionStream==='undefined')throw Error('A current browser with DecompressionStream support is required.');const b=Uint8Array.from(atob(document.getElementById('data').textContent.trim()),c=>c.charCodeAt(0));window.STANDALONE_DATA=JSON.parse(await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text());const s=document.createElement('script');s.textContent=document.getElementById('viewer-program').textContent;document.body.appendChild(s);document.getElementById('offline-loading').remove()}catch(e){document.getElementById('offline-loading').textContent='Could not open embedded data: '+e.message}})();"""
 return shell+'\n<style id="offline-fonts">'+fonts(vendor)+'</style>\n'+vendor_js+'<script data-offline-vendor="reference-reader">'+safe_script(reference_js)+'</script>\n<p id="offline-loading" role="status">Opening embedded data…</p>\n<script id="data" type="application/octet-stream" data-encoding="gzip">'+encoded+'</script>\n<script id="viewer-program" type="text/plain">'+safe_script(program)+'</script>\n<script>'+bootstrap+'</script>\n<details style="margin:1rem"><summary>Embedded software licenses</summary><pre style="white-space:pre-wrap">'+licenses.replace('&','&amp;').replace('<','&lt;')+'</pre></details>\n</body></html>\n'

def main():
 root=Path(__file__).resolve().parents[1];assets=root/'tools/protein_space_viewer_assets'
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--viewer',type=Path,required=True);ap.add_argument('--catalogue',type=Path,required=True);ap.add_argument('--viewer-template',type=Path,default=assets/'viewer_template.html');ap.add_argument('--catalogue-template',type=Path,default=assets/'catalogue_template.html');ap.add_argument('--reference-reader',type=Path,default=assets/'reference_browser.js');ap.add_argument('--vendor-dir',type=Path,default=root/'assets/protein_space_vendor');ap.add_argument('--viewer-out',type=Path,required=True);ap.add_argument('--catalogue-out',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--replace-candidate',action='store_true');a=ap.parse_args()
 if not a.replace_candidate and any(p.exists() for p in [a.viewer_out,a.catalogue_out]):raise ValueError('Output exists. Use --replace-candidate only for an identified derived candidate.')
 inputs=[{'path':str(p.resolve()),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in [a.viewer,a.catalogue,a.viewer_template,a.catalogue_template,a.reference_reader,Path(__file__)]]
 # Read every input before replacing any derived candidate. Sources are never overwritten.
 viewer=read_data(a.viewer.read_text());catalogue=read_data(a.catalogue.read_text());old_points=sha(json.dumps([s['pts'] for s in viewer['sets']],separators=(',',':')).encode())
 if viewer.get('schema')!='codex.protein_space.enriched.v1':raise ValueError('Unsupported enriched viewer schema; no alternate reader is inferred')
 viewer['region_payloads']=packed_assets(a.viewer.parent,viewer['region_files'],viewer.get('region_payloads'))
 viewer['reference_payloads']=packed_assets(a.viewer.parent,viewer['reference_files'],viewer.get('reference_payloads'))
 split_counts={}
 for encoded in viewer['reference_payloads'].values():
  payload=json.loads(gzip.decompress(base64.b64decode(encoded)))
  for key,item in payload['comparisons'].items():split_counts[key]=len(item['splits'] or [])
 for row in catalogue['rows']:row['retained_split_records']=split_counts.get(row['source_pair'],0)
 viewer['standalone']=True;catalogue['standalone']=True;catalogue['reference_payloads']=viewer['reference_payloads'];catalogue['reference_summaries']=viewer['reference_summaries'];catalogue['reference_files']=viewer['reference_files']
 exports={}
 for filename in ['SOURCE_BINDINGS.tsv','REFERENCE_SOURCE_BINDINGS.tsv','BUILD_RECEIPT.json']:
  path=a.viewer.parent/filename
  if path.exists():exports[filename]=path.read_text()
 viewer['offline_exports']=exports
 for filename in ['ALL_COMPARISONS.tsv','STRAIN_COVERAGE.tsv','SOURCE_BINDINGS.tsv','AUDIT_RECEIPT.json']:
  path=a.catalogue.parent/filename
  if path.exists():catalogue.setdefault('offline_exports',{})[filename]=path.read_text()
 reader=a.reference_reader.read_text();vtext=package_html(a.viewer_template.read_text(),viewer,reader,a.vendor_dir,True);ctext=package_html(a.catalogue_template.read_text(),catalogue,reader,a.vendor_dir)
 for path,text in [(a.viewer_out,vtext),(a.catalogue_out,ctext)]:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
 receipt={'schema':'sapote.protein_space.standalone.v1','viewer':str(a.viewer_out.resolve()),'catalogue':str(a.catalogue_out.resolve()),'viewer_bytes':len(vtext.encode()),'catalogue_bytes':len(ctext.encode()),'layouts':len(viewer['sets']),'point_rows':sum(len(s['pts']) for s in viewer['sets']),'point_fingerprint_before':old_points,'point_fingerprint_after':sha(json.dumps([s['pts'] for s in read_data(vtext)['sets']],separators=(',',':')).encode()),'embedded_region_strains':len(viewer['region_payloads']),'embedded_reference_strains':len(viewer['reference_payloads']),'comparison_rows':len(catalogue['rows']),'reference_gene_rows':viewer['reference_detail_coverage']['reference_gene_rows'],'network_dependencies':0,'new_analysis':False,'outputs':{str(a.viewer_out):sha(vtext.encode()),str(a.catalogue_out):sha(ctext.encode())},'vendor_files':[{'file':p.name,'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(a.vendor_dir.iterdir()) if p.is_file()]}
 if receipt['point_fingerprint_before']!=receipt['point_fingerprint_after']:raise ValueError('Point geometry changed during packaging')
 receipt['inputs']=inputs;a.receipt.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['vendor_files','outputs','inputs']},indent=2))

if __name__=='__main__':main()
