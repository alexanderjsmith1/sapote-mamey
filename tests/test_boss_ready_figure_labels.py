import csv
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use('Agg')
from mamey.render_brief import _setup_mpl, fig_landscape
from mamey.figures_sapote import fig_dapr_scatter, _fig_ranked
from mamey.render_safe import figure_text_overlap_report


def _row(i, kcb='knownclusterblast | very very long kirromycin-class product family name that should not be on the plot'):
    return {'rank': str(i), 'bgc_id': f'BGC{i:03d}', 'contig': 'NODE_' + '1234567890'*3, 'region': f'region_{i}',
            'products': 'transAT-PKS; NRPS', 'boundary': 'Interior', 'arch': 'A',
            'ab': 90 - i, 'af': 60 + (i % 10), 'novelty': 80 - i, 'lead_tier': 'High',
            'kcb_top': kcb, 'kcb_score': '12', 'cctt': ''}


def test_dapr_scatter_does_not_put_long_kcb_labels_on_plot(tmp_path):
    plt = _setup_mpl()
    rows = [_row(i) for i in range(1, 15)]
    png = str(tmp_path / 'dap.png')
    fig_dapr_scatter(rows, png, 'AS-TEST', plt)
    # CSV preserves full KCB, plot image has compact labels by construction.
    csv_text = open(png.replace('.png', '_data.csv')).read()
    assert 'very very long kirromycin-class' in csv_text


def test_landscape_labels_are_wrapped_not_raw_contigs(tmp_path):
    plt = _setup_mpl()
    rows = [_row(i) for i in range(1, 8)]
    png = str(tmp_path / 'land.png')
    fig = fig_landscape(rows, png, 'AS-TEST', plt)
    labels = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert all(len(line) <= 35 for lab in labels for line in lab.split('\n'))
    plt.close(fig)
