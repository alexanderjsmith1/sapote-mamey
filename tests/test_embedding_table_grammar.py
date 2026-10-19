from pathlib import Path
import importlib.util,os
import pytest
from tools import protein_pcoa_render as current
p=Path(os.environ.get("LANE06_PPR_CANDIDATE",current.__file__));sp=importlib.util.spec_from_file_location("strict_embedding_candidate",p);ppr=importlib.util.module_from_spec(sp);sp.loader.exec_module(ppr)
ROWS=[dict(id="r1",source="reference"),dict(id="i1",source="isolate")]

@pytest.mark.parametrize("raw",[
 "id\tid\tTRIMAP1\tTRIMAP2\nFOREIGN_r\tr1\t0\t1\nFOREIGN_i\ti1\t2\t3\n",
 "id\tTRIMAP1\tTRIMAP1\tTRIMAP2\nr1\tNaN\t0\t1\ni1\tNaN\t2\t3\n",
 "id\tTRIMAP1\tTRIMAP2\t\nr1\t0\t1\tx\ni1\t2\t3\tx\n",
 "id\tTRIMAP1\tTRIMAP2\t note\nr1\t0\t1\tx\ni1\t2\t3\tx\n",
 "id\tTRIMAP1\tTRIMAP2\tnote\nr1\t0\t1\ni1\t2\t3\tx\n",
 "id\tTRIMAP1\tTRIMAP2\nr1\t0\t1\textra\ni1\t2\t3\textra\n",
 "id\tTRIMAP1\tTRIMAP2\nr1\t0\t1\ni1\t2\t\"3",
 "id\tTRIMAP1\tTRIMAP2\nr1\t0\t1\n\ni1\t2\t3\n",
])
def test_ambiguous_or_ragged_raw_table_refused(tmp_path,raw):
    p=tmp_path/"emb.tsv";p.write_text(raw)
    with pytest.raises(ppr.RenderRefusal):ppr.embedding_coordinates(p,ROWS,"TRIMAP",ppr.file_binding(p))

@pytest.mark.parametrize("raw",[
 "id\tTRIMAP1\tTRIMAP2\ni1\t2\t3\nr1\t0\t1\n",
 '\ufeffid\tTRIMAP1\tTRIMAP2\tnote\ni1\t2\t3\t"quoted\nmultiline"\nr1\t0\t1\t"a\tfield"\n'
])
def test_valid_quoted_and_reversed_table_preserves_exact_values(tmp_path,raw):
    p=tmp_path/"emb.tsv";p.write_text(raw)
    out=ppr.embedding_coordinates(p,ROWS,"TRIMAP",ppr.file_binding(p))
    assert [(r["id"],r["PC1"],r["PC2"],r["source"]) for r in out]==[("r1","0","1","reference"),("i1","2","3","isolate")]
