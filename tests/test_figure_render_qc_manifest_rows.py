"""Manifest rows must preserve their own defect, source, and expected-hash obligations."""
import hashlib
import sys
from pathlib import Path
import pytest
pytest.importorskip("PIL")
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import figure_render_qc as qc

@pytest.fixture
def figures(tmp_path):
    image=Image.new("RGB",(300,200),"white")
    ImageDraw.Draw(image).rectangle((20,20,160,160),fill="navy")
    png=tmp_path/"review.png"; image.save(png,dpi=(300,300))
    png.with_suffix(".svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Regions per isolate</text></svg>')
    other=tmp_path/"other.png"
    Image.new("RGB",(300,200),"black").save(other,dpi=(300,300))
    return tmp_path,png,other

def run_manifest(root,rows):
    manifest=root/"MANIFEST.tsv"
    manifest.write_text("png\tsource\tnote\tsha256\n"+"".join("\t".join(row)+"\n" for row in rows))
    return qc.run([],root/"qa",ocr_mode="off",manifest=manifest)

@pytest.mark.parametrize("bad_first",[True,False])
@pytest.mark.parametrize("obligation",["defect_note","source","expected_hash"])
def test_each_repeated_review_row_keeps_its_obligations(figures,bad_first,obligation):
    root,png,other=figures
    good=("review.png","review.png","","")
    bad={"defect_note":("review.png","review.png","DO NOT USE: wrong selected cohort",""),
         "source":("review.png","other.png","",""),
         "expected_hash":("review.png","review.png","","0"*64)}[obligation]
    results=run_manifest(root,[bad,good] if bad_first else [good,bad])
    assert len(results)==2
    expected="defect logged" if obligation=="defect_note" else ("review/source PNG mismatch" if obligation=="source" else "manifest SHA-256 mismatch")
    row_errors=[[m for lv,m in flags if lv=="error"] for _,flags in results]
    assert any(expected in m for m in row_errors[0 if bad_first else 1])
    assert not row_errors[1 if bad_first else 0]

def test_repeated_review_with_bad_note_cannot_exit_clean(figures):
    root,png,other=figures
    run_manifest(root,[("review.png","review.png","DO NOT USE: wrong cohort",""),("review.png","review.png","","")])
    assert qc.main(["--manifest",str(root/"MANIFEST.tsv"),"--out",str(root/"qa"),"--ocr","off"])==2

def test_identical_manifest_rows_remain_valid(figures):
    root,png,other=figures
    digest=hashlib.sha256(png.read_bytes()).hexdigest()
    results=run_manifest(root,[("review.png","review.png","",digest)]*2)
    assert len(results)==2
    assert not any(lv in ("error","not_checked") for _,flags in results for lv,_ in flags)

def test_repeated_review_uses_its_own_source_svg(figures):
    root,png,other=figures
    source=root/"equivalent.png"; source.write_bytes(png.read_bytes())
    source.with_suffix(".svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Judgment deferred</text></svg>')
    results=run_manifest(root,[("review.png","equivalent.png","",""),("review.png","review.png","","")])
    assert any(lv=="error" and "judgment deferred" in message for lv,message in results[0][1])
    assert not any(lv=="error" for lv,message in results[1][1])
