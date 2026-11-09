import hashlib,json,re,shutil
from pathlib import Path
from mamey.compile_report import _figures

def test_receipt_bound_pair_survives_package_relocation(tmp_path):
    pkg=tmp_path/'original'/'package';folder=pkg/'figure folder';folder.mkdir(parents=True)
    png=folder/'one.png';svg=folder/'one.svg';png.write_bytes(b'PNG fixture');svg.write_bytes(b'<svg/>')
    def meta(p):return {'logical_locator':p.relative_to(pkg).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    (pkg/'figure_receipts.jsonl').write_text(json.dumps({'outputs':{'png':meta(png),'svg':meta(svg)}})+'\n')
    report=_figures(pkg,generate=False);(pkg/'report.md').write_text(report)
    new=tmp_path/'relocated'/'package';shutil.copytree(pkg,new)
    target=re.search(r'\[SVG version\]\(<([^>]+)>\)',(new/'report.md').read_text()).group(1)
    path=Path(target);path=path if path.is_absolute() else new/path
    assert path.resolve()==(new/'figure folder'/'one.svg').resolve()
    assert path.is_file()
