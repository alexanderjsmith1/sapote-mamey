"""Refuse invalid final-width text before saving; separate from numeric regression."""
import pytest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tests import test_449_protein_pcoa_compare as fixture


@pytest.mark.parametrize('fault',['small','collision','overflow','tick_in_data'])
def test_geometry_refuses_distinct_defects(fault):
    mod=fixture._load();fig=plt.figure(figsize=(7.2,3))
    try:
        if fault=='small': fig.text(.1,.1,'below floor',fontsize=7)
        elif fault=='collision':
            fig.text(.1,.1,'first',fontsize=8);fig.text(.1,.1,'second',fontsize=8)
        elif fault=='overflow': fig.text(1.0,.1,'outside canvas',fontsize=8)
        else:
            ax=fig.add_subplot();ax.set_xticks([.5]);ax.set_yticks([])
            ax.tick_params(axis='x',pad=-12,labelsize=8)
        with pytest.raises(mod.CompareRefusal): mod.comparison_text_geometry(fig,8.)
    finally: plt.close(fig)


def test_unshown_locator_ticks_are_not_false_overflow():
    mod=fixture._load();fig,ax=plt.subplots(figsize=(7.2,3))
    try:
        ax.set_xticks([-20,0,50,100,120]);ax.set_xlim(-2,102);ax.set_yticks([])
        ax.tick_params(labelsize=8)
        result=mod.comparison_text_geometry(fig,8.)
        assert result['layout']['status']=='PASS'
        assert result['tick_data_clearance']['tick_label_rectangle_count']==3
    finally: plt.close(fig)
