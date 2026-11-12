"""TTA figure rows must distinguish an unrecorded count from a measured zero."""
import pytest
from mamey import cohort_figures as f


def test_g07_bins_missing_separately_from_zero(monkeypatch, tmp_path):
    names=['SYNTHETIC']
    data={'SYNTHETIC':{'deep':{'bgc_profile':[{'bgc_id':'BGC001','tta_codons':None}, {'bgc_id':'BGC002','tta_codons':0}]}}}
    monkeypatch.setattr(f, '_load_inv_g', lambda *_: {'SYNTHETIC':[]})
    observed=[]
    def capture(matrix,labels,order,title,fid,out,**kwargs):
        if fid=='tta_bldA_dependency':
            observed.append((dict(zip(labels,[row[0] for row in matrix])),title))
    monkeypatch.setattr(f,'hmap',capture)
    f.batch2(data,names,str(tmp_path))
    bins,title=observed[0]
    assert bins['0 counted']==1 and bins['unknown / missing']==1
    assert 'dependent' not in title.lower()


@pytest.mark.parametrize("all_missing", [False, True])
def test_d11_preserves_missing_row_without_plotting_it(monkeypatch,tmp_path,all_missing):
    names=['SYNTHETIC']
    records={'SYNTHETIC':{'privacy':{'effective_release':'PUBLIC'},'ms':{'raw_bgcs':2,'corrected_bgcs':2,'assembly_tier':'GOOD'},'deep':{'bgc_profile':[{'bgc_id':'BGC001','tta_codons':None},{'bgc_id':'BGC002','tta_codons':None if all_missing else 0}]}}}
    inventory={'SYNTHETIC':[{'BGC_ID':'BGC001','Length_kb':20,'Products':'','KCB_score':1000,'KCB_top':'ref','Boundary':'Interior'},{'BGC_ID':'BGC002','Length_kb':20,'Products':'','KCB_score':1000,'KCB_top':'ref','Boundary':'Interior'}]}
    monkeypatch.setattr(f,'_load_inv_d',lambda *_:inventory)
    monkeypatch.setattr(f,'bubble_matrix',lambda *a,**k:None)
    seen=[]; sidecars=[]
    def save(fig,path,**kwargs):
        if 'scatter_tta_vs_modularity' in str(path):
            ax=fig.axes[0];seen.append((len(ax.collections[0].get_offsets()),ax.get_title(),ax.get_ylabel()))
        f.plt.close(fig)
    def sidecar(path,header,rows):
        if 'scatter_tta_vs_modularity' in str(path):sidecars.append((header,rows))
    monkeypatch.setattr(f,'_save_pair',save);monkeypatch.setattr(f,'sidecar',sidecar)
    f.build(records,names,str(tmp_path))
    if all_missing:
        assert not seen
    else:
        assert seen and seen[0][0]==1 and 'dependency' not in (seen[0][1]+seen[0][2]).lower()
    header,rows=sidecars[0]
    assert header[-1]=='tta_count_state'
    assert [r[-1] for r in rows]==(['MISSING','MISSING'] if all_missing else ['MISSING','RECORDED'])
    if not all_missing: assert rows[1][-2]==0
    assert 'does not establish' in f.CAPTIONS['scatter_tta_vs_modularity']


def test_g07_footer_describes_count_without_changing_filename():
    f._load_plot_dependencies()
    fig=f.plt.figure()
    try:
        filename=f.stamp_g(fig, "tta_bldA_dependency")
        assert filename.endswith("_tta_bldA_dependency")
        assert "tta_codon_count" in fig._supxlabel.get_text()
        assert "dependency" not in fig._supxlabel.get_text()
    finally:
        f.plt.close(fig)
