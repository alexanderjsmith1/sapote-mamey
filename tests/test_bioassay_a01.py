from mamey.bioassay_paper import prepare, write
def test_a01_target_and_denominator_contract(tmp_path):
    table=tmp_path/'assay.tsv';roster=tmp_path/'roster.tsv';aliases=tmp_path/'aliases.json'
    aliases.write_text('{}')
    write(roster,[dict(strain='X',genus='Streptomyces',group='Bryophytes')])
    values=[('Candida albicans','20'),('Candida auris','50'),('Candida (species not named)','90'),('MRSA','0'),('Foulbrood 818','80')]
    write(table,[dict(strain='X',organism=t,material='Crude extract',best_pct=v) for t,v in values])
    z=prepare(table,roster,aliases,'A01','moss')
    # moss profile splits Candida by species (card 452_bioassay_candida_split_and_label) and draws no panel for an
    # unnamed Candida screen (card 453_bioassay_unnamed_candida_panel_dropped: a01_drop_targets)
    assert {(r['target'],r['best_pct']) for r in z['plot']} == {('C. albicans',20.0),('C. auris',50.0),('MRSA',0.0)}
