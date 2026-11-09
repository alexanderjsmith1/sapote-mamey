from pathlib import Path
from mamey import cohort_figures as cf
from mamey import compile_report as cr
from mamey.figure_save import audit_figure_outputs

def test_cohort_render_keeps_dotted_stem_and_resolves_caption(tmp_path,monkeypatch):
    sid='GCA_021432215.1_Test_strain'
    identity={'strain_id':sid,'contig':'NODE_1_length_100_cov_1.0','antismash_region':'region001','bgc_id':'BGC001','node_id':'NODE_1'}
    profile={'bgc_identity':identity,'exact_locus':'synthetic locus','source_record_index':0,'measurement_sha256':'fixture','tta_codons':0,'tta_cds':0,'resistance_tier':'','umed_verdict':'','cctt_triggers':'','total_domains':1,'PKS_KS':1}
    monkeypatch.setattr(cf,'FIGNUM',[0])
    cf._figs_single_panels({sid:{'deep':{'bgc_profile':[profile],'active_sites':[]}}},sid,str(tmp_path))
    stem='F01_'+sid+'_perBGC_domain_heatmap'
    for suffix in ['.png','.svg','_data.csv','_identity.csv']:
        assert (tmp_path/(stem+suffix)).is_file()
    assert audit_figure_outputs(tmp_path)['figures'][0]['state']=='RECEIPT_BOUND_PAIR'
    report=cr._figures(tmp_path,generate=False)
    assert report.count('![')==1 and stem+'.png' in report and '[SVG version]' in report
    assert f'[SVG version](<{stem}.svg>)' in report
    caption=Path(cf.write_captions(str(tmp_path),[stem+'.png'])).read_text()
    assert cf.CAPTIONS['perBGC_domain_heatmap'] in caption

def test_caption_uses_longest_known_suffix_and_leaves_unknown_pending(tmp_path):
    names=['F01_GCA_021432215.1_Test_perGene_active_site_completeness.png','F02_GCA_021432215.1_Test_unknown.png']
    caption=Path(cf.write_captions(str(tmp_path),names)).read_text()
    assert cf.CAPTIONS['perGene_active_site_completeness'] in caption
    assert '**F02** (GCA_021432215.1_Test_unknown). (caption pending)' in caption
