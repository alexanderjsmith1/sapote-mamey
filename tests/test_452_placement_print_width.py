import shutil
import json
import pytest
from .test_452_rect02_shipping import render_direct, read_pdf


def _scale_word(page, tips):
    """Find the positive scale below tip centers and left of labels, independent of value."""
    import re
    tip_words = [word for word in page['words'] if word['text'].replace('−', '-') in set(tips)]
    assert tip_words, 'assigned tip labels must be visible before locating the scale'
    # Separate columns can have slightly overlapping glyph boxes without text overlap.
    # Locate the scale by its center below all tip centers and by its tree-column position.
    last_tip_center = max((word['top'] + word['bottom']) / 2 for word in tip_words)
    label_left = min(word['x0'] for word in tip_words)
    numeric = r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
    scales = [word for word in page['words']
              if re.fullmatch(numeric, word['text'])
              and float(word['text']) > 0
              and (word['top'] + word['bottom']) / 2 > last_tip_center
              and word['x1'] <= label_left]
    assert len(scales) == 1, f'expected one positive scale below tips, got {scales}'
    return scales[0]


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_default_print_width_and_all_text_at_least_eight_points(tmp_path):
    prefix,tips=render_direct(tmp_path,long_label=True)
    pages=read_pdf(prefix.with_suffix('.pdf'))
    assert len(pages)==1
    for page in pages:
        assert page['width']==pytest.approx(7.2*72,abs=.01)
        assert page['height']<=9*72+.01
        assert min(c['size'] for c in page['chars'] if c['text'].strip())>=7.99
        assert all(-.01<=c['x0']<=c['x1']<=page['width']+.01 for c in page['chars'])
    assert '600 shared sites)' in pages[0]['text']
    scale=_scale_word(pages[0],tips)
    panel_left=min(line['x0'] for line in pages[0]['lines'])
    assert scale['x0']>=panel_left
    from PIL import Image
    import numpy as np
    a=np.array(Image.open(prefix.with_suffix('.png')).convert('RGB'))
    a=a[:int(len(a)*.78),int(a.shape[1]*.7):]
    bounds=[]
    for colour in [(176,0,32),(77,77,77)]:
        mask=(a==colour).all(axis=2)
        col=mask.sum(axis=0).argmax()
        ys=np.where(mask[:,col])[0]
        runs=np.split(ys,np.where(np.diff(ys)>1)[0]+1)
        tiles=sorted(runs,key=len,reverse=True)[:2]
        bounds.append((min(int(x.min()) for x in tiles),max(int(x.max()) for x in tiles)))
    assert max(abs(x-y) for x,y in zip(*bounds))<=2


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_120_tip_pages_have_every_tip_once_and_repeat_scale_and_legend(tmp_path):
    prefix,tips=render_direct(tmp_path,n=120,GG_PRINT_WIDTH='7.2')
    manifest=json.loads(prefix.with_suffix('.pages.json').read_text())
    assert len(manifest['pages'])>1
    assigned=[tip for page in manifest['pages'] for tip in page['tips']]
    assert len(assigned)==len(set(assigned))==len(tips) and set(assigned)==set(tips)
    all_text=[]
    for page in manifest['pages']:
        pdf=read_pdf(tmp_path/page['pdf'])[0];all_text.append(pdf['text'].replace('−','-'))
        assert pdf['width']==pytest.approx(7.2*72,abs=.01)
        assert pdf['height']<=9*72+.01
        assert min(c['size'] for c in pdf['chars'] if c['text'].strip())>=7.99
        assert 'Activity' in pdf['text'].replace('−','-')
        _scale_word(pdf,page['tips'])
        for tip in page['tips']:assert tip in pdf['text'].replace('−','-')
        # A clipped page must not show an extra unlabelled terminal branch in
        # the scale-bar band below its last assigned tip.
        from PIL import Image
        import numpy as np
        chars=pdf['chars']; text=''.join(c['text'] for c in chars).replace('−','-')
        index=text.index(page['tips'][-1]); char=chars[index]
        pixels=np.array(Image.open(tmp_path/page['png']).convert('RGB'))
        scale=pixels.shape[1]/pdf['width']
        region=pixels[int((char['bottom']+3)*scale):int((char['bottom']+15)*scale),
                      int((char['x0']-30)*scale):int((char['x0']-4)*scale)]
        assert ((region<40).all(axis=2)).sum(axis=1).max(initial=0)<=12
    # Full PDF is the same page sequence; no additional hidden tip labels.
    pdfs=read_pdf(prefix.with_suffix('.pdf'))
    assert len(pdfs)==len(manifest['pages'])
    import re
    observed=[]
    for page in pdfs:observed.extend(re.findall(r'SYN-\d+|Reference_\d+|Reference_outgroup',page['text'].replace('−','-')))
    assert sorted(observed)==sorted(tips)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_export_binds_and_keeps_page_files(tmp_path,monkeypatch):
    from .test_452_rect02_shipping import test_flat_admitted_run_renders_strips_end_to_end as render
    import hashlib
    render(tmp_path,monkeypatch)
    output=tmp_path/'display'
    receipt=json.loads((output/'placement_display_receipt.json').read_text())
    package=output/'standalone_R_package'
    assert (package/'toy_rect02.pages.json').is_file()
    for filename,expected in receipt['page_artifacts'].items():
        assert hashlib.sha256((output/filename).read_bytes()).hexdigest()==expected
        assert (package/filename).read_bytes()==(output/filename).read_bytes()


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_caption_override_and_figure_id_are_rendered_at_print_width(tmp_path):
    methods='Synthetic trees retain their supplied root and measured branch lengths while display annotations remain separate.'
    prefix,_=render_direct(tmp_path,GG_CAPTION_WRAP='35',GG_FIGID='Figure SYN-970',GG_METHODS=methods)
    page=read_pdf(prefix.with_suffix('.pdf'))[0]
    assert page['width']==pytest.approx(7.2*72,abs=.01)
    caption=page['text'].replace('−','-').split('Figure SYN-970',1)[1]
    assert ' '.join(methods.split()) in ' '.join(caption.split())
    assert all(len(line)<=35 for line in ('Figure SYN-970'+caption).splitlines())
    assert min(c['size'] for c in page['chars'] if c['text'].strip())>=7.99
