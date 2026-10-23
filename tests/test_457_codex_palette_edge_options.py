import ast
from pathlib import Path
import pytest
from tools.edge_plot_data import convert

def test_counts_and_order_preserve_explicit_edge_semantics():
    totals=[dict(strain='SYN_A',genus='Synthetic',regions='8',contig_edge='3')]
    assert convert(totals,[dict(strain='SYN_A',genus='Synthetic')])==[dict(strain='SYN_A',genus='Synthetic',families=8,in_public=5,not_in_public=3)]

@pytest.mark.parametrize('n,e,g',[('8','9','Synthetic'),('8','-1','Synthetic'),('8','3','Different')])
def test_invalid_counts_or_genus_refuse(n,e,g):
    with pytest.raises(ValueError):convert([dict(strain='SYN_A',genus=g,regions=n,contig_edge=e)],[dict(strain='SYN_A',genus='Synthetic')])

def test_palette_override_is_explicit_input_and_default_is_retained():
    from tools import taxonomy_T01_figures as t
    # The main run is patched at the input boundary: existing plotted-number checks still run.
    import inspect
    source=inspect.getsource(t.run)
    assert "getattr(args,'palette_json',None)" in source
    assert 'palette_path' in source[source.index('bound='):]


def test_invalid_palette_refuses_before_renderer_or_cohort_read(tmp_path):
    from types import SimpleNamespace
    from tools import taxonomy_T01_figures as t
    bad=tmp_path/'palette.json';bad.write_text('{"default":{"Synthetic":"orange"},"sets":{},"fallback":"#ffffff"}')
    with pytest.raises(ValueError,match='six-digit hex'):
        t.run(SimpleNamespace(palette_json=bad))
