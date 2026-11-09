import hashlib,json,re
from pathlib import Path
from types import SimpleNamespace
from mamey import compile_report as cr
from mamey import validate,blastp_gate,claim_safety_gate

def test_external_report_svg_link_resolves(tmp_path,monkeypatch):
    pkg=tmp_path/'reader view'/'package';pkg.mkdir(parents=True)
    fig=pkg/'figure folder';fig.mkdir();png=fig/'one.png';svg=fig/'one.svg'
    png.write_bytes(b'PNG fixture');svg.write_text('<svg/>')
    def rec(p):return {'logical_locator':p.relative_to(pkg).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    (pkg/'figure_receipts.jsonl').write_text(json.dumps({'outputs':{'png':rec(png),'svg':rec(svg)}})+'\n')
    output=tmp_path/'published'/'report.md';output.parent.mkdir()
    monkeypatch.setattr(validate,'validate_package',lambda *a,**kw:{'identity_binding':'PASS','manifest_parse':'PASS','checksum_integrity':'PASS'})
    monkeypatch.setattr(blastp_gate,'gate',lambda *a,**kw:{'blocked':False,'message':''})
    monkeypatch.setattr(cr,'_read_manifests',lambda *a,**kw:{'strain_id':'SYN'})
    monkeypatch.setattr(cr,'build_report',lambda package,**kw:cr._figures(package,generate=False,absolute_companions=kw.get('absolute_figure_companions',False)))
    monkeypatch.setattr(claim_safety_gate,'lint_text',lambda *a:[])
    args=SimpleNamespace(package_dir=str(pkg),out=str(output),strict=False,no_figures=True,toc_depth=1,pdf=False)
    assert cr._compile_report_from_reader_view(args)==0
    md=output.read_text();image=re.search(r'!\[[^]]*\]\(<([^>]+)>\)',md);link=re.search(r'\[SVG version\]\(<([^>]+)>\)',md)
    assert image and Path(image.group(1)).is_file()
    assert link
    target=Path(link.group(1));target=target if target.is_absolute() else output.parent/target
    assert target.is_file(),f'SVG link does not resolve: {target}\n{md}'
