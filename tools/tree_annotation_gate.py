"""Reject display categories inconsistent with their retained raw source text."""
import argparse,csv,json
from pathlib import Path
from _phylo_metadata import normalize_isolation_source
from phylo_display_contract import load_palette

MISSING_DISPLAY_VALUES={'','n/a','na','none','not recorded','unknown','unresolved','unresolved source','missing'}

def missing(value):
 return str(value or '').strip().casefold() in MISSING_DISPLAY_VALUES

def validate(rows,require_geography=False):
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
  if missing(actual):raise ValueError('ANNOTATION_SOURCE_INCOMPLETE: '+tip)
  expected=normalize_isolation_source(row['category_raw'])['display_category']
  if actual!=expected:raise ValueError('ANNOTATION_CATEGORY_CONTRADICTION: '+tip+' observed='+actual+' expected='+expected)
  if ('source',actual) not in palette:raise ValueError('ANNOTATION_SOURCE_PALETTE_UNSUPPORTED: '+tip)
  if require_geography and missing(row.get('source')):raise ValueError('ANNOTATION_GEOGRAPHY_INCOMPLETE: '+tip)
  if require_geography and ('geography',(row.get('source') or '').strip()) not in palette:raise ValueError('ANNOTATION_GEOGRAPHY_PALETTE_UNSUPPORTED: '+tip)
 return {'status':'ANNOTATION_DISPLAY_METADATA_VALIDATED','rows':len(seen),'complete_geography_required':require_geography,'ceiling':'Display consistency only; raw metadata and biological claims require source review.'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('metadata');ap.add_argument('--require-geography',action='store_true');a=ap.parse_args()
 with open(a.metadata) as f:rows=list(csv.DictReader(f,delimiter='\t'))
 try:print(json.dumps(validate(rows,a.require_geography)))
 except ValueError as e:raise SystemExit(str(e))
if __name__=='__main__':main()
