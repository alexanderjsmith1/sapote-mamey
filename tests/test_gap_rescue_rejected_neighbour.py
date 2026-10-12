"""Real public reference replay: a supported neighbour must not promote a rejected gene."""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip('matplotlib')
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gap_map_rejected_neighbour', ROOT/'tools/gap_rescue_locus_map.py')
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)
FIXTURE = json.loads((Path(__file__).parent/'fixtures/gap_rescue_brevicatena_rows.json').read_text())

@pytest.mark.parametrize('verdict', ['PARALOG_FAMILY', 'HOUSEKEEPING_CONTEXT'])
def test_rejected_adjacent_gene_is_context_not_a_reference_match(verdict):
    rows = [dict(r) for r in FIXTURE['rows']]
    rows[3]['partner_verdict'] = verdict
    drawn, _, contigs, _, _ = glm.choose(FIXTURE['reference_genes'], rows, [], FIXTURE['proteins'], FIXTURE['core']['contig'])
    assert rows[2]['best_protein'] in {pid for _,pid,_ in drawn}, 'Supported crtU remains a match.'
    assert rows[3]['best_protein'] not in {pid for _,pid,_ in drawn}, 'Rejected crtV must have no identity ribbon.'
    assert rows[3]['best_contig'] in contigs, 'The supported neighbour keeps the contig as context.'

def test_real_replay_has_gray_reference_gene_and_no_rejected_identity_label(tmp_path, monkeypatch):
    monkeypatch.setattr(glm, 'reference_genes', lambda _: (FIXTURE['reference_genes'], FIXTURE['reference_length_kb']))
    arrows = []
    texts = []
    original_arrow = glm._arrow
    def observed_arrow(ax, x0, x1, y, strand, fc):
        arrows.append(fc)
        return original_arrow(ax,x0,x1,y,strand,fc)
    monkeypatch.setattr(glm, '_arrow', observed_arrow)
    from matplotlib.axes import Axes
    original_text = Axes.text
    def observed_text(self, x, y, text, *args, **kwargs):
        texts.append(str(text))
        return original_text(self,x,y,text,*args,**kwargs)
    monkeypatch.setattr(Axes, 'text', observed_text)
    glm.draw_locus_map(Path('BGC0000664.gbk'),FIXTURE['rows'],[],FIXTURE['proteins'],[],FIXTURE['core'],
                       'Nocardia_brevicatena_NBRC_12119','isorenieratene',tmp_path/'map.png',tmp_path/'map.pdf')
    assert arrows[3] == glm.GREY, 'Rejected crtV reference arrow must remain gray.'
    assert not any('CrtV-like' in text for text in texts), 'Rejected gene must have no identity label.'
    assert any('CrtU-like' in text for text in texts)
