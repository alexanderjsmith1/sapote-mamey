from mamey.bioassay_paper import prepare, write
def test_a04_target_and_denominator_contract(tmp_path):
    table=tmp_path/'assay.tsv';roster=tmp_path/'roster.tsv';aliases=tmp_path/'aliases.json'
    aliases.write_text('{}')
    write(roster,[dict(strain='X',genus='Streptomyces',group='Bryophytes')])
    values=[('Candida albicans','20'),('Candida auris','50'),('Candida (species not named)','90'),('MRSA','0'),('Foulbrood 818','80')]
    write(table,[dict(strain='X',organism=t,material='Crude extract',best_pct=v) for t,v in values])
    z=prepare(table,roster,aliases,'A04','moss')
    # moss profile: one Candida axis, the higher of the three screens (owner, 13 Oct: one Candida panel)
    assert [(r['x'],r['y']) for r in z['plot']] == [(90.0,0.0)]
