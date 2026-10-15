"""Reject display categories inconsistent with their retained raw source text."""
import argparse,csv,json,os
from pathlib import Path
from _phylo_metadata import normalize_isolation_source
from phylo_display_contract import load_palette

MISSING_DISPLAY_VALUES={'','n/a','na','none','not recorded','unknown','unresolved','unresolved source','missing'}

def GEO_FIELD():
 return 'country' if os.environ.get('SAPOTE_GEOGRAPHY_LEVEL')=='country' else 'geography'

def missing(value):
 return str(value or '').strip().casefold() in MISSING_DISPLAY_VALUES

def validate_activity(rows):
 """v9.7.444: strips hold measured activity, not isolation source. Query rows need an activity value from the shared
 'activity' palette; reference and outgroup rows must stay blank (they were not part of the screen)."""
 rows=list(rows)
 if not rows:raise ValueError("ANNOTATION_EMPTY: no metadata rows")
 palette=load_palette(Path(__file__).with_name('phylo_display_palette.tsv'))
 seen=set()
 for row in rows:
  tip=row.get('tip','')
  if not tip or tip in seen:raise ValueError('ANNOTATION_TIP_IDENTITY: empty or duplicate tip')
  seen.add(tip)
  spec=json.loads(os.environ.get('GG_ACTIVITY_SPEC','[]'))
  for col in ([item['column'] for item in spec] if spec else ('category','source')):
   v=(row.get(col) or '').strip()
   if (row.get('role') or '')=='query':
    if ('activity',v) not in palette and not (spec and v in {'+','−','n.t.',''}):raise ValueError('ANNOTATION_ACTIVITY_UNSUPPORTED: '+tip+' '+col+'='+v)
   elif v:raise ValueError('ANNOTATION_ACTIVITY_ON_REFERENCE: '+tip)
 return {'status':'ANNOTATION_ACTIVITY_METADATA_VALIDATED','rows':len(seen),'ceiling':'Display consistency only; measured strain-level activity, not attributed to any locus.'}

def validate(rows,require_geography=False,allow_blank_reference=False):
 rows=list(rows)
 if not rows:raise ValueError("ANNOTATION_EMPTY: no metadata rows")
 palette=load_palette(Path(__file__).with_name('phylo_display_palette.tsv'))
 seen=set()
 for row in rows:
  tip=row.get('tip','')
  if not tip or tip in seen:raise ValueError('ANNOTATION_TIP_IDENTITY: empty or duplicate tip')
  seen.add(tip)
  if 'category_raw' not in row:raise ValueError('ANNOTATION_RAW_SOURCE_MISSING: '+tip)
  actual=(row.get('category') or '').strip()
  # v9.7.444 option 1: a reference (type strain) with no deposited value is drawn as a blank cell, never a guessed one.
  blank_ref=allow_blank_reference and (row.get('role') or '')!='query'
  if blank_ref and missing(actual) and missing(row.get('category_raw')):
   if require_geography and not missing(row.get('source')) and (GEO_FIELD(),(row.get('source') or '').strip()) not in palette:raise ValueError('ANNOTATION_GEOGRAPHY_PALETTE_UNSUPPORTED: '+tip)
   continue
  if missing(actual):raise ValueError('ANNOTATION_SOURCE_INCOMPLETE: '+tip)
  expected=normalize_isolation_source(row['category_raw'])['display_category']
  if actual!=expected:raise ValueError('ANNOTATION_CATEGORY_CONTRADICTION: '+tip+' observed='+actual+' expected='+expected)
  if ('source',actual) not in palette:raise ValueError('ANNOTATION_SOURCE_PALETTE_UNSUPPORTED: '+tip)
  if require_geography and missing(row.get('source')):
   if blank_ref:continue
   raise ValueError('ANNOTATION_GEOGRAPHY_INCOMPLETE: '+tip)
  if require_geography and (GEO_FIELD(),(row.get('source') or '').strip()) not in palette:raise ValueError('ANNOTATION_GEOGRAPHY_PALETTE_UNSUPPORTED: '+tip)
 return {'status':'ANNOTATION_DISPLAY_METADATA_VALIDATED','rows':len(seen),'complete_geography_required':require_geography,'ceiling':'Display consistency only; raw metadata and biological claims require source review.'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('metadata');ap.add_argument('--require-geography',action='store_true');ap.add_argument('--activity',action='store_true');ap.add_argument('--allow-blank-reference',action='store_true');a=ap.parse_args()
 with open(a.metadata) as f:rows=list(csv.DictReader(f,delimiter='\t'))
 try:print(json.dumps(validate_activity(rows) if a.activity else validate(rows,a.require_geography,a.allow_blank_reference)))
 except ValueError as e:raise SystemExit(str(e))
if __name__=='__main__':main()
