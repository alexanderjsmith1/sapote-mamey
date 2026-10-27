from mamey.report_card import render_report_cards
import tests.test_458_report_card_modules_by_region as fixture


def package(tmp_path,unbound=False,unique=False):
    p=fixture._package(tmp_path)
    other='chromosome_other_full_identifier'
    fixture._csv(p/f'{fixture.S}_4_triage_board.csv',[
        {'BGC_ID':'BGC001','Contig':fixture.CONTIG,'antiSMASH_Region':'region001','Rank':'1','Products':'NRPS'},
        {'BGC_ID':'BGC002','Contig':other,'antiSMASH_Region':'region002','Rank':'2','Products':'NRPS'}])
    tags=['first_unique','second_unique'] if unique else ['shared_tag','shared_tag']
    fixture._csv(p/f'{fixture.S}_gene_by_gene_all_bgcs.csv',[
        {'bgc_id':'BGC001','contig':fixture.CONTIG,'locus_tag':tags[0]},
        {'bgc_id':'BGC002','contig':other,'locus_tag':tags[1]}])
    fixture._csv(p/f'{fixture.S}_nrps_prediction.csv',[
        {'record_id':'' if unbound else fixture.CONTIG,'locus_tag':tags[0],'domain_class':'NRPS_A','substrate':'ser','confidence':'high'},
        {'record_id':'' if unbound else other,'locus_tag':tags[1],'domain_class':'NRPS_A','substrate':'orn','confidence':'high'}])
    return p


def test_repeated_tags_on_different_records_do_not_cross_assign(tmp_path):
    text=render_report_cards(str(package(tmp_path)))['markdown']
    one,two=fixture._card_text(text,'BGC001'),fixture._card_text(text,'BGC002')
    assert 'ser(' in one and 'orn(' not in one
    assert 'orn(' in two and 'ser(' not in two


def test_ambiguous_unbound_modules_are_unresolved_not_negative(tmp_path):
    text=render_report_cards(str(package(tmp_path,unbound=True)))['markdown']
    assert 'ser(' not in text and 'orn(' not in text
    assert 'module mapping unresolved' in text
    assert 'no per-module substrate calls (non-NRPS/PKS' not in text


def test_unique_legacy_tags_remain_usable(tmp_path):
    text=render_report_cards(str(package(tmp_path,unbound=True,unique=True)))['markdown']
    one,two=fixture._card_text(text,'BGC001'),fixture._card_text(text,'BGC002')
    assert 'ser(' in one and 'orn(' not in one
    assert 'orn(' in two and 'ser(' not in two


def test_region_gene_join_is_not_labelled_contig_pending(tmp_path):
    p=fixture._package(tmp_path)
    fixture._csv(p/f'{fixture.S}_predicted_polymers.csv',[
        {'record_id':fixture.CONTIG,'region_number':'1','predicted_polymer':''},
        {'record_id':fixture.CONTIG,'region_number':'2','predicted_polymer':''}])
    text=render_report_cards(str(p))['markdown']
    assert 'per-region coord scoping pending' not in text
    assert 'gene-table region assignment' in text


def test_single_region_fallback_respects_known_module_record(tmp_path):
    p=fixture._package(tmp_path,with_gene_table=False)
    fixture._csv(p/f'{fixture.S}_4_triage_board.csv',[
        {'BGC_ID':'BGC001','Contig':fixture.CONTIG,'antiSMASH_Region':'region001','Rank':'1','Products':'NRPS'}])
    fixture._csv(p/f'{fixture.S}_nrps_prediction.csv',[
        {'record_id':fixture.CONTIG,'locus_tag':'ctg5_10','domain_class':'NRPS_A','substrate':'ser','confidence':'high'},
        {'record_id':'other_full_record','locus_tag':'ctg5_80','domain_class':'NRPS_A','substrate':'orn','confidence':'high'}])
    text=render_report_cards(str(p))['markdown']
    assert 'ser(' in text and 'orn(' not in text
