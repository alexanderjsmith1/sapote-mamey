from pathlib import Path
import importlib.util,sys,subprocess,shutil
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from tree_annotation_gate import validate
from _phylo_metadata import normalize_isolation_source

def test_reference_categories_cannot_inherit_query_host():
 for raw in ['marine sponge','garden soil','root of a plant','dairy salt (contaminant of medium)']:
  with pytest.raises(ValueError,match='ANNOTATION_CATEGORY_CONTRADICTION'):
   validate([dict(tip='reference_1',category_raw=raw,category='bumblebee')])
 assert validate([dict(tip='query_1',category_raw='Bombus sp.',category='bumblebee')])['rows']==1

def test_ant_boundaries_and_raw_source_are_required():
 assert normalize_isolation_source('coastal salt-marsh plant stem')['display_category']=='plant-associated'
 assert normalize_isolation_source('dairy salt (contaminant of medium)')['display_category']=='other documented'
 assert normalize_isolation_source('ant')['display_category']=='insect-associated'
 with pytest.raises(ValueError,match='ANNOTATION_RAW_SOURCE_MISSING'):validate([dict(tip='reference_1',category='bumblebee')])
 with pytest.raises(ValueError,match='ANNOTATION_TIP_IDENTITY'):validate([dict(tip='x',category_raw='soil',category='soil/rock/sediment')]*2)

def test_direct_renderer_rejects_missing_source_and_full_view_geography():
 with pytest.raises(ValueError,match='ANNOTATION_SOURCE_INCOMPLETE'):
  validate([dict(tip='reference_1',category_raw='soil',category='Not recorded',source='US')])
 with pytest.raises(ValueError,match='ANNOTATION_GEOGRAPHY_INCOMPLETE'):
  validate([dict(tip='reference_1',category_raw='soil',category='soil/rock/sediment',source='Not recorded')],require_geography=True)
 assert validate([dict(tip='reference_1',category_raw='soil',category='soil/rock/sediment',source='Not recorded')],require_geography=False)['complete_geography_required'] is False

def test_actual_r_plot_geometry_and_fill(tmp_path):
 r=shutil.which('Rscript')
 if not r:pytest.skip('Rscript unavailable; render integration remains unverified')
 script=tmp_path/'geometry.R'
 script.write_text("""suppressPackageStartupMessages(library(ggplot2))
source(commandArgs(trailingOnly=TRUE)[1])
d<-data.frame(tip=factor(c('reference','query'),levels=c('reference','query')),value=c('soil','bee'))
pal<-c(soil='#8c6d31',bee='#0072b2')
make<-function(h,values=pal) ggplot(d,aes(x=0,y=tip,fill=value))+geom_tile(height=h,width=1)+scale_fill_manual(values=values)
a<-validate_annotation_strip(make(1),c('reference','query'),c('soil','bee'),pal);stopifnot(nrow(a)==2)
fails<-function(expr,code){e<-tryCatch({force(expr);NULL},error=function(e)e);stopifnot(inherits(e,'error'),grepl(code,conditionMessage(e)))}
fails(validate_annotation_strip(make(9),c('reference','query'),c('soil','bee'),pal),'ANNOTATION_GEOMETRY')
fails(validate_annotation_strip(make(1,c(soil='#0072b2',bee='#0072b2')),c('reference','query'),c('soil','bee'),pal),'ANNOTATION_COLOUR')
fails(validate_annotation_strip(make(1),c('reference','reference'),c('soil','bee'),pal),'ANNOTATION_IDENTITY')
""")
 result=subprocess.run([r,str(script),str(ROOT/'tools/tree_annotation_geometry.R')],capture_output=True,text=True)
 assert result.returncode==0,result.stdout+result.stderr

def test_gate_wired_before_render_and_dependencies_exported():
 s=(ROOT/'tools/ggtree_rect_heatmap.R').read_text()
 assert s.index('tree_annotation_gate.py')<s.index('tr <- read.tree')
 assert s.index('validate_annotation_strip(s_cat')<s.index('ggsave(')
 assert 'ANNOTATION_TREE_ALIGNMENT' in s
 assert '--require-geography' in s and 'ifelse(focal, disp, NA)' in s
 export=(ROOT/'tools/export_tree_figure_source_package.py').read_text()
 for name in ['tree_annotation_gate.py','tree_annotation_geometry.R','_phylo_metadata.py','phylo_display_contract.py','phylo_display_palette.tsv']:assert name in export


def test_full_renderer_blocks_bad_metadata_before_export(tmp_path):
 import os,csv
 r=shutil.which('Rscript')
 if not r:pytest.skip('Rscript unavailable')
 tree=tmp_path/'tree.nwk';tree.write_text('((((A:0.1,B:0.1):0.1,C:0.1):0.1,D:0.1):0.1,OUTGROUP:0.15);')
 md=tmp_path/'metadata.tsv'
 rows=[dict(tip=t,label='Genus species '+t,category_raw='soil',category='soil/rock/sediment',source='US') for t in ['A','B','C','D','OUTGROUP']]
 def write():
  with md.open('w') as f:
   w=csv.DictWriter(f,fieldnames=rows[0].keys(),delimiter='\t');w.writeheader();w.writerows(rows)
 env=dict(os.environ,GG_STRIPS='2',SAPOTE_PYTHON=sys.executable)
 def run(name):return subprocess.run([r,str(ROOT/'tools/ggtree_rect_heatmap.R'),str(tree),str(md),str(tmp_path/name)],env=env,capture_output=True,text=True)
 write();p=run('good');assert p.returncode==0,p.stdout+p.stderr
 assert (tmp_path/'good.pdf').exists() and (tmp_path/'good.annotation_audit.tsv').exists()
 rows[0]['category']='bumblebee';write();p=run('bad')
 assert p.returncode!=0 and 'ANNOTATION_CATEGORY_CONTRADICTION' in p.stdout+p.stderr
 assert not (tmp_path/'bad.pdf').exists() and not (tmp_path/'bad.png').exists()

def test_empty_metadata_fails():
 with pytest.raises(ValueError,match='ANNOTATION_EMPTY'):validate([])
