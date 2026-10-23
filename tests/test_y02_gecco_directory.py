"""An unavailable GECCO directory must not imply an unrun row."""
from pathlib import Path
import os,sys
import pytest
root=Path(os.environ.get('Y02_RUNTIME',str(Path(__file__).resolve().parents[1])))
sys.path.insert(0,str(root/'tests'))
from test_y02_multi_reference_gecco import mrc,modelmod

@pytest.mark.parametrize('kind',['missing','file'])
def test_unavailable_directory_refused(tmp_path,kind):
    directory=tmp_path/'input'
    if kind=='file':directory.write_text('not a directory')
    model=modelmod._model()
    with pytest.raises(ValueError,match='GECCO directory unavailable'):
        mrc.attach_gecco(model,directory)
    assert 'gecco_tracks' not in model

def test_available_directory_without_row_table_keeps_unrun_state(tmp_path):
    model=modelmod._model()
    result=mrc.attach_gecco(model,tmp_path)
    assert result['query']['state']=='NOT_RUN'
    assert result['query']['note']=='GECCO not run'
