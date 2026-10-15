from mamey.bioassay_paper import prepare, write
def test_a02_target_and_denominator_contract(tmp_path):
    table=tmp_path/'assay.tsv';roster=tmp_path/'roster.tsv';aliases=tmp_path/'aliases.json'
    aliases.write_text('{}')
    write(roster,[dict(strain='X',genus='Streptomyces',group='Bryophytes')])
    values=[('Candida albicans','20'),('Candida auris','50'),('Candida (species not named)','90'),('MRSA','0'),('Foulbrood 818','80')]
    write(table,[dict(strain='X',organism=t,material='Crude extract',best_pct=v) for t,v in values])
    z=prepare(table,roster,aliases,'A02','moss')
    assert next(r for r in z['plot'] if r['target']=='Candida albicans' and r['material']=='Crude extract')['label']=='0/1'
