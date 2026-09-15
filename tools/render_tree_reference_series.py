"""Render a hash-bound series of prepared tree displays using immutable input copies."""
import argparse,csv,hashlib,json,os,shutil,subprocess,sys
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tree_series_contract import validate,validate_delivery,digest
from _phylo_metadata import normalize_isolation_source
from phylo_display_contract import load_palette,validate_display_metadata
INPUTS={'tree.newick','metadata.tsv','provenance.tsv','palette.tsv','settings.tsv','caption.txt'}
SAFE_NAME_CHARS='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.'
GENERIC_OUTPUT_STEMS={'tree','figure','plot','output','result'}
MISSING_DISPLAY_VALUES={'','n/a','na','none','not recorded','unknown','unresolved','unresolved source','missing'}

def output_basename(job):
 return f"{job['series_index']:02d}_{job['output_stem']}"

def is_missing_display_value(value):
 return str(value or '').strip().casefold() in MISSING_DISPLAY_VALUES

def admit_complete_display_metadata(rows):
 rows=list(rows)
 if not rows:raise ValueError('SERIES_DISPLAY_METADATA_EMPTY')
 required={'tip','label','role','source_category','geography'}
 if any(not required<=set(row) for row in rows):raise ValueError('SERIES_DISPLAY_METADATA_SCHEMA')
 seen=set();counts={'query':0,'reference':0,'outgroup':0}
 for row in rows:
  tip=row['tip'].strip();role=row['role'].strip().lower()
  if not tip or tip in seen:raise ValueError('SERIES_DISPLAY_TIP_IDENTITY')
  seen.add(tip)
  if role not in counts:raise ValueError('SERIES_DISPLAY_ROLE:'+tip)
  counts[role]+=1
  for field in ('label','source_category','geography'):
   if is_missing_display_value(row.get(field)):
    raise ValueError(f'SERIES_DISPLAY_METADATA_INCOMPLETE:{tip}:{field}')
 return {'rows':len(rows),'role_counts':counts,'all_tips_complete':True,
         'required_fields':['label','source_category','geography']}

def admit_palette(rows,mapping=None,colors=None):
 mapping={} if mapping is None else mapping;colors={} if colors is None else colors
 if not rows or any(not {'field','value','color'}<=set(row) for row in rows):raise ValueError('SERIES_PALETTE_SCHEMA')
 for row in rows:
  field=row['field'].strip();value=row['value'].strip();color=row['color'].strip().upper();key=(field,value);color_key=(field,color)
  if field not in {'source','geography'} or is_missing_display_value(value) or not __import__('re').fullmatch(r'#[0-9A-F]{6}',color):raise ValueError('SERIES_PALETTE_VALUE')
  if key in mapping and mapping[key]!=color:raise ValueError('SERIES_PALETTE_CONTRADICTION')
  if color_key in colors and colors[color_key]!=value:raise ValueError('SERIES_PALETTE_COLOR_REUSED')
  mapping[key]=color;colors[color_key]=value
 return mapping,colors

def preflight(config):
 config=Path(config).resolve();data=json.loads(config.read_text());jobs=data['display_jobs']
 receipt=validate(data,jobs,config.parent)
 shared_palette=load_palette(Path(__file__).with_name('phylo_display_palette.tsv'))
 indices=[job.get('series_index') for job in jobs]
 if any(type(x) is not int for x in indices) or sorted(indices)!=list(range(1,len(jobs)+1)):raise ValueError('SERIES_INDEX_SEQUENCE')
 stems=[job.get('output_stem') for job in jobs]
 if any(not isinstance(x,str) or len(x)<8 or x.lower() in GENERIC_OUTPUT_STEMS or x[0]=='.' or any(c not in SAFE_NAME_CHARS for c in x) for x in stems):raise ValueError('SERIES_OUTPUT_STEM')
 if len(stems)!=len(set(stems)):raise ValueError('SERIES_OUTPUT_STEM_DUPLICATE')
 seen=set();palette_mapping={};palette_colors={}
 for job in jobs:
  name=job['job_id']
  if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.' for c in name) or name in seen:raise ValueError('SERIES_JOB_ID')
  seen.add(name)
  group=job.get('group','')
  if group and any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.' for c in group):raise ValueError('SERIES_GROUP_ID')
  if set(job.get('input_hashes',{}))!=INPUTS:raise ValueError('SERIES_INPUT_BINDINGS')
  folder=(config.parent/job['input_dir']).resolve()
  for name,sha in job['input_hashes'].items():
   if digest(folder/name)!=sha:raise ValueError('SERIES_INPUT_HASH_CHANGED')
  with (folder/'palette.tsv').open() as f:palette_rows=list(csv.DictReader(f,delimiter='\t'))
  admit_palette(palette_rows,palette_mapping,palette_colors)
  for row in palette_rows:
   key=(row['field'].strip(),row['value'].strip())
   if key not in shared_palette or shared_palette[key]!=row['color'].strip().upper():raise ValueError('SERIES_PALETTE_NOT_CANONICAL')
  with (folder/'metadata.tsv').open() as f:md=list(csv.DictReader(f,delimiter='\t'))
  from Bio import Phylo
  display_tips=[x.name for x in Phylo.read(folder/'tree.newick','newick').get_terminals()]
  if len(display_tips)!=len(set(display_tips)) or set(display_tips)!={row.get('tip','') for row in md}:raise ValueError('SERIES_DISPLAY_TREE_METADATA_BIJECTION')
  with (folder/'provenance.tsv').open() as f:provenance=list(csv.DictReader(f,delimiter='\t'))
  with (folder/'settings.tsv').open() as f:settings={x['key']:x['value'] for x in csv.DictReader(f,delimiter='\t')}
  required_settings={'view','title','layout_profile','tree_fraction','outgroup_tip','inference_program','model','support_type','support_replicates','support_cutoff','rooting'}
  if not required_settings<=set(settings):raise ValueError('SERIES_SETTINGS_CONTRACT')
  job['display_metadata_gate']=validate_display_metadata(md,provenance,shared_palette,
   profile=settings['layout_profile'],tree_fraction=float(settings['tree_fraction']))
  for row in md:
   actual=row['source_category'].strip().lower()
   if actual in {'bumblebee','honeybee','wasp'} and normalize_isolation_source(row['raw_source'])['display_category']!=actual:raise ValueError('SERIES_SOURCE_CATEGORY_CONTRADICTION')
 receipt['palette_contract']={f'{field}:{value}':color for (field,value),color in sorted(palette_mapping.items())}
 receipt['display_metadata_contract']={
  'all_tips_require_complete_label_source_and_geography':True,
  'missing_value_sentinels':sorted(MISSING_DISPLAY_VALUES),
  'jobs':{job['job_id']:job['display_metadata_gate'] for job in jobs},
 }
 receipt['query_label_color']=os.environ.get('GG_FOCAL_COLOUR','#000000')
 receipt['shared_palette_sha256']=digest(Path(__file__).with_name('phylo_display_palette.tsv'))
 return config,data,receipt

def render(config,outdir,rscript='Rscript',workers=2):
 config,data,receipt=preflight(config);root=Path(outdir).resolve()
 if root.exists():raise ValueError('SERIES_OUTPUT_EXISTS')
 if workers not in (1,2,3,4):raise ValueError('SERIES_WORKER_LIMIT')
 root.mkdir(parents=True);code=root/'code';code.mkdir();here=Path(__file__).resolve().parent
 for name in ['tree_reference_series.R','tree_annotation_geometry.R','phylo_display_palette.tsv']:
  shutil.copy2(here/name,code/name)
 source_hashes={p.name:digest(p) for p in code.iterdir()}
 def run(job):
  folder=root/job.get('group','')/job['job_id'];folder.mkdir(parents=True);source=(config.parent/job['input_dir']).resolve()
  stem=output_basename(job)
  result={'job_id':job['job_id'],'series_index':job['series_index'],'output_basename':stem,'directory':str(folder.relative_to(root)),'status':'FAIL'}
  try:
   for name,sha in job['input_hashes'].items():
    shutil.copy2(source/name,folder/name)
    if digest(folder/name)!=sha:raise ValueError('SERIES_INPUT_CHANGED_DURING_COPY')
   if any(digest(code/name)!=sha for name,sha in source_hashes.items()):raise ValueError('SERIES_RENDERER_CHANGED')
   with (folder/f'{stem}.render.log').open('w') as f:p=subprocess.run([rscript,str(code/'tree_reference_series.R'),str(folder),str(code/'tree_annotation_geometry.R'),stem],stdout=f,stderr=subprocess.STDOUT)
   if p.returncode:raise ValueError('SERIES_R_RENDER_FAILED')
   if any(digest(code/name)!=sha for name,sha in source_hashes.items()):raise ValueError('SERIES_RENDERER_CHANGED')
   if any(digest(folder/name)!=sha for name,sha in job['input_hashes'].items()):raise ValueError('SERIES_RENDER_INPUT_CHANGED')
   extras=[f'{stem}.layout_audit.tsv',f'{stem}.methods.txt',f'{stem}.R_SESSION.txt',
           f'{stem}.source_category_actual_cells.tsv',f'{stem}.geography_actual_cells.tsv']
   if any(not (folder/name).is_file() or not (folder/name).stat().st_size for name in extras):raise ValueError('SERIES_RENDER_AUDIT_MISSING')
   shutil.copy2(folder/'metadata.tsv',folder/f'{stem}.metadata.tsv')
   for name in ['provenance.tsv','palette.tsv','settings.tsv','caption.txt']:
    shutil.copy2(folder/name,folder/f'{stem}.{name}')
   adapted=dict(job,output_layout={'tree':f'{stem}.newick','metadata':f'{stem}.metadata.tsv','pdf':f'{stem}.pdf','png':f'{stem}.png'})
   result.update(status='PASS',audit=validate_delivery(data,adapted,folder,config.parent),inputs=job['input_hashes'],renderers=source_hashes,extra_artifacts={name:digest(folder/name) for name in extras})
  except Exception as e:result['error']=str(e)
  (folder/f'{stem}.render_receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result
 results=[]
 with ThreadPoolExecutor(max_workers=workers) as pool:
  for i,result in enumerate(pool.map(run,data['display_jobs']),1):
   results.append(result)
   if i%20==0:logging.getLogger(__name__).info('%s/%s variants processed', i, len(data['display_jobs']))
 complete=len(results)==receipt['expected_variants'] and all(x['status']=='PASS' for x in results)
 result={'status':'COMPLETE_MECHANICAL_REVIEW_ONLY' if complete else 'INCOMPLETE','config_sha256':digest(config),'preflight':receipt,'planned':len(data['display_jobs']),'passed':sum(x['status']=='PASS' for x in results),'results':results,'ceiling':'Mechanical completion does not establish scientific or publication acceptance.'}
 (root/'SERIES_RENDER_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--outdir',required=True);p.add_argument('--rscript',default='Rscript');p.add_argument('--workers',type=int,default=2);a=p.parse_args()
 try:r=render(a.config,a.outdir,a.rscript,a.workers)
 except (ValueError,OSError,KeyError) as e:raise SystemExit(str(e))
 return 0 if r['status']=='COMPLETE_MECHANICAL_REVIEW_ONLY' else 2
if __name__=='__main__':sys.exit(main())
