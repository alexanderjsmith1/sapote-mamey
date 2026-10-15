"""Compact class panels preserve data while fitting a page."""
import importlib.util
from pathlib import Path
import pytest
from pypdf import PdfReader

spec=importlib.util.spec_from_file_location("layout_fixture",Path(__file__).with_name("test_452_blastp_identity_figures_alex_notes.py"))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
world=fixture.world

@pytest.mark.parametrize("shown,grid,expected_columns", [(4,"auto",2),(3,"auto",2),(4,"column",1),(5,"auto",1)])
def test_panel_geometry_and_print_constraints(world,monkeypatch,shown,grid,expected_columns):
    from matplotlib.figure import Figure
    captures=[];save=Figure.savefig
    def capture(fig,path,*args,**kwargs):
        if str(path).endswith(".pdf"):
            visible=[ax for ax in fig.axes if ax.get_visible()]
            captures.append(visible)
            assert len({round(ax.get_position().x0,3) for ax in visible})==expected_columns
            for col in {round(ax.get_position().x0,3) for ax in visible}:
                same=[ax for ax in visible if round(ax.get_position().x0,3)==col]
                lowest=min(same,key=lambda ax:ax.get_position().y0)
                assert any(t.get_visible() and t.get_text() for t in lowest.get_xticklabels())
        return save(fig,path,*args,**kwargs)
    monkeypatch.setattr(Figure,"savefig",capture)
    out=world["tmp"]/"layout"
    omit=[item for c in ["Other","Terpene"][:5-shown] for item in ["--omit-class",c]]
    assert fixture._run(world,out,"--figure","by-class","--grid",grid,*omit)==0
    pdf=out/"BLASTP_IDENTITY_BY_CLASS.pdf"
    box=PdfReader(pdf).pages[0].mediabox
    assert float(box.width)/72<=7.21
    assert all(size>=7.95 for size,text in fixture._text_runs(pdf))
    if expected_columns==2: assert float(box.height)/72<=9.0
    else: assert float(box.height)/72>9.0
    assert captures


def test_grid_and_column_tables_are_identical(world):
    for grid in ("auto","column"):
        fixture._run(world,world["tmp"]/grid,"--figure","by-class","--grid",grid,"--omit-class","Other")
    for name in ["GENE_VALUES.tsv","BLASTP_IDENTITY_BY_CLASS_numbers.tsv"]:
        assert (world["tmp"]/"auto"/name).read_bytes()==(world["tmp"]/"column"/name).read_bytes()
