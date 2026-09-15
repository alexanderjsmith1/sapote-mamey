import copy
import pytest
from mamey.cohort_resolver import is_placeholder_taxonomy

@pytest.mark.parametrize('value', ['.', '...', '1234', 'sp.', 'SP', 'spp.'])
def test_placeholder_refused_before_outputs(tmp_path, value):
    from mamey.cli import run_one_strain
    out = tmp_path / 'must-not-exist'
    result = run_one_strain('TEST', 'TEST', 'unread.zip', str(out), 'gold', value, 'not supplied')
    assert result == {'status': 'TAXONOMY_PLACEHOLDER', 'written': False}
    assert not out.exists()

@pytest.mark.parametrize('value', ['', ' ', 'not verified', 'Streptomyces sp.', 'Nocardia thailandica', 'Candidatus Example bacterium'])
def test_explicit_unknown_and_named_taxonomy_remain_admissible(value):
    assert not is_placeholder_taxonomy(value)

class PageCheck:
    def __init__(self): self.pages = []
    def savefig(self, fig):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        boxes = []
        texts = []
        for artist in fig.texts:
            box = artist.get_window_extent(renderer)
            assert box.x0 >= 0 and box.y0 >= 0
            assert box.x1 <= fig.bbox.width and box.y1 <= fig.bbox.height
            if artist.get_text():
                for prior in boxes:
                    assert not box.overlaps(prior), artist.get_text()
                boxes.append(box)
                texts.append(artist.get_text())
        self.pages.append(texts)

@pytest.mark.parametrize('tier', ['minimal', 'standard'])
def test_long_identity_warning_and_scan_text_fit_without_overlap(tier):
    from mamey import render_brief as rb
    plt = rb._setup_mpl()
    row = {'bgc_id': 'BGC001', 'contig': 'NODE_'+'0123456789'*18,
           'region': 'region001', 'products': 'NRPS', 'ab': 0, 'af': 0, 'novelty': 0,
           'ab_input_state': 'UNBOUND', 'af_input_state': 'INVALID', 'novelty_input_state': 'MEASURED'}
    facts = {'manifest': {'strain_id': 'TEST', 'taxonomy': 'Nocardia thailandica',
             'package_status': 'MAMEY_COMPLETE_WITH_ISSUES', 'source': 'Long metadata '*50,
             'bgc_counts': {'assembly_tier': 'VERY_POOR'},
             'assembly': {'quality': {'caveat_required': True, 'caveat': 'Long warning '*80}},
             'scan_status': {'scans': [('scan', 'MISSING', 'Long detail '*30)]}},
             'strain_label': 'Long strain name '*15, 'release': 'PRIVATE',
             'rows': [copy.deepcopy(row) for _ in range(10)]}
    check = PageCheck()
    rb._text_page(check, plt, facts, tier)
    text = '\n'.join(line for page in check.pages for line in page)
    assert 'MAMEY_COMPLETE_WITH_ISSUES' in text
    assert 'DETERMINISTIC EXTRACTION COMPLETE' not in text
    assert len(check.pages) > 1
    if tier == 'standard':
        assert row['contig'] in text.replace('\n', '')
        assert 'UNBOUND' in text and 'INVALID' in text
        assert 'Source scans' in text
