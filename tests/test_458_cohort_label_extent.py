"""Exercise the native cohort heatmap with long generic identifiers."""
from pathlib import Path
import csv,importlib.util,os
import pytest
pytestmark=pytest.mark.slow

def module():
 import mamey.cohort_figures as baseline
 path=Path(os.environ.get('SAPOTE_COHORT_MODULE',baseline.__file__))
 spec=importlib.util.spec_from_file_location('mamey._label_test_candidate',path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m

@pytest.mark.parametrize('n',[3,8])
def test_native_heatmap_labels_and_cell_font(tmp_path,monkeypatch,n):
 m=module();ids=[f'Genusdemo_species_reference_collection_{i}_GCF_90000000{i}' for i in range(n)]
 S={s:{'privacy':{'effective_release':'PUBLIC'}} for s in ids}
 for s in ids:m.GENUS[s]='Genusdemo species'
 native_save=m._save_pair;observed=[]
 def capture(fig,path,**kwargs):
  native_save(fig,path,**kwargs);fig.canvas.draw();ax=fig.axes[0];r=fig.canvas.get_renderer()
  labels=ax.get_xticklabels();boxes=[t.get_window_extent(r) for t in labels]
  assert not any(a.overlaps(b) for i,a in enumerate(boxes) for b in boxes[i+1:]),'Genome tick labels collide'
  assert all(t.get_fontsize()>=8 for t in ax.texts),'Numeric text below8pt'
  for s,label in zip(ids,labels):
   assert s in ''.join(label.get_text().split()),'Full identifier was abbreviated or rewritten'
  observed.append(True)
 monkeypatch.setattr(m,'_save_pair',capture)
 m.heatmap([list(range(1,n+1)),list(range(n+1,2*n+1))],['Metric A','Metric B'],ids,S,'Generic cohort','generic',str(tmp_path))
 assert observed
 sidecar=next(tmp_path.glob('*_data.csv'))
 with sidecar.open() as f:rows=list(csv.reader(f))
 assert rows[0][1:]==ids,'Source columns changed'
 assert [float(x) for x in rows[1][1:]]==list(range(1,n+1))
