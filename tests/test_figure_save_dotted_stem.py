import sys
import pytest
from pathlib import Path
from mamey.figure_save import FigureSaveRefusal, NativeSvgFigure, audit_figure_outputs, save_figure

class FakeCairo:
    @staticmethod
    def svg2png(*,bytestring,output_width):
        return b'\x89PNG\r\n\x1a\n' + bytestring

def test_dotted_stems_keep_full_name_and_do_not_collide(tmp_path,monkeypatch):
    monkeypatch.setitem(sys.modules,'cairosvg',FakeCairo)
    root=tmp_path/'package';root.mkdir()
    names=['F01_GCA_021432215.1_first','F01_GCA_021432215.2_second']
    for name in names:
        fig=NativeSvgFigure(f'<svg xmlns="http://www.w3.org/2000/svg"><text>{name}</text></svg>')
        save_figure(fig,figure_id=name,out_stem=root/name,renderer='synthetic',package_dir=root,provenance='test')
    for name in names:
        assert (root/f'{name}.png').is_file()
        assert (root/f'{name}.svg').is_file()
        assert name.encode() in (root/f'{name}.svg').read_bytes()
    assert not (root/'F01_GCA_021432215.png').exists()
    audit=audit_figure_outputs(root)
    assert len(audit['figures'])==2
    assert all(x['state']=='RECEIPT_BOUND_PAIR' for x in audit['figures'])


def test_output_stem_cannot_be_package_directory(tmp_path,monkeypatch):
    monkeypatch.setitem(sys.modules,"cairosvg",FakeCairo)
    root=tmp_path/"package";root.mkdir()
    fig=NativeSvgFigure('<svg xmlns="http://www.w3.org/2000/svg"><text>test</text></svg>')
    with pytest.raises(FigureSaveRefusal,match="output paths must be contained"):
        save_figure(fig,figure_id="fixture",out_stem=root,renderer="synthetic",package_dir=root,provenance="test")
    assert not (tmp_path/"package.png").exists()
    assert not (tmp_path/"package.svg").exists()
