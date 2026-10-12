"""Regression for a real singleton log heatmap's invisible white count label."""
import csv
import numpy as np
import pytest

pytest.importorskip('matplotlib')
from matplotlib.colors import to_rgb
from mamey import cohort_figures as cf


def _luminance(rgb):
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    return sum(w*v for w,v in zip((.2126,.7152,.0722), linear))


def _contrast(a, b):
    x,y=sorted((_luminance(a),_luminance(b)))
    return (y+.05)/(x+.05)


@pytest.mark.parametrize('renderer', ['heatmap','hmap'])
@pytest.mark.parametrize('values,lognorm,cmap', [
    ([[51]],True,'magma_r'),
    ([[1,100]],True,'magma_r'),
    ([[1,100]],False,'Greens'),
    ([[1,100]],False,'magma'),
    ([[0,float('nan'),5]],True,'magma_r'),
])
def test_text_uses_actual_fill_and_sidecar_values_are_preserved(tmp_path,monkeypatch,renderer,values,lognorm,cmap):
    captured=[]
    def capture(fig,path,**kwargs):
        fig.canvas.draw()
        captured.append((fig,path))
    monkeypatch.setattr(cf,'_save_pair',capture)
    order=[f'SYNTHETIC_REFERENCE_{i}' for i in range(len(values[0]))]
    kwargs=dict(mat=values,rowlabs=['observed count'],order=order,title='Synthetic count panel',
                fid='actual_fill',OUT=str(tmp_path),lognorm=lognorm,cmap=cmap)
    if renderer=='heatmap':
        kwargs['S']={s:{'privacy':{'effective_release':'PUBLIC'}} for s in order}
    getattr(cf,renderer)(**kwargs)
    assert len(captured)==1
    fig,path=captured[0]
    ax=fig.axes[0];image=ax.images[0]
    expected_finite=sum(np.isfinite(v) for row in values for v in row)
    labels=[t for t in ax.texts if t.get_text() in {'0','1','5','51','100'}]
    assert len(labels)==expected_finite
    for label in labels:
        x,y=map(int,label.get_position());value=values[y][x]
        rgba=image.cmap(image.norm(value));back=ax.get_facecolor()
        fill=[rgba[i]*rgba[3]+back[i]*(1-rgba[3]) for i in range(3)]
        chosen=to_rgb(label.get_color())
        # Either black or white always exceeds this contrast; the former scalar
        # threshold chose white on the pale singleton51 cell and fails this.
        assert _contrast(fill,chosen)>=4.5
        if value==51:
            assert label.get_color()=='#000000'
    with open(path.replace('.png','_data.csv'),newline='') as stream:
        rows=list(csv.reader(stream))
    assert rows[0][1:]==order
    stored=[float(v) for v in rows[1][1:]]
    assert np.allclose(stored,values[0],equal_nan=True)
    assert all(t.get_text().lower()!='nan' for t in ax.texts)
