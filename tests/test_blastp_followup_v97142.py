import csv
from pathlib import Path

from mamey.blastp_followup import parse_hit_table_csv, parse_xml2, merge_hit_xml, summarize_results, ingest_followup


def test_headerless_hit_table_preserves_first_row(tmp_path):
    p = tmp_path / 'hit.csv'
    p.write_text('AS168|BGC001|ctg10_1|aa=100|role=core,WP_1.1,99.0,100,1,0,1,100,1,100,0.0,200,99.0\n'
                 'AS168|BGC001|ctg10_1|aa=100|role=core,WP_2.1,50.0,50,20,0,1,50,1,50,1e-5,50,60.0\n')
    rows = parse_hit_table_csv(p)
    assert len(rows) == 2
    assert rows[0].subject_id == 'WP_1.1'
    assert rows[0].query_coverage == 1.0


def test_xml2_metadata_merges_hit_titles(tmp_path):
    hit = tmp_path / 'hit.csv'
    hit.write_text('AS168|BGC002|ctg11_9|aa=317|role=core_or_context,WP_401454914.1,89.0,305,1,0,12,316,1,305,0.0,558,91.0\n')
    xml = tmp_path / 'x.xml'
    xml.write_text('''<?xml version="1.0"?><BlastXML2 xmlns="http://www.ncbi.nlm.nih.gov"><BlastOutput2><report><Report><results><Results><search><Search><query-title>AS168|BGC002|ctg11_9|aa=317|role=core_or_context</query-title><query-len>317</query-len><hits><Hit><description><HitDescr><id>ref|WP_401454914.1|</id><accession>WP_401454914</accession><title>presqualene diphosphate synthase HpnD [Streptomyces]</title><taxid>1883</taxid><sciname>Streptomyces</sciname></HitDescr></description><len>306</len><hsps><Hsp><bit-score>558</bit-score><evalue>0</evalue><identity>282</identity><positive>288</positive><align-len>305</align-len></Hsp></hsps></Hit></hits></Search></search></Results></results></Report></report></BlastOutput2></BlastXML2>''')
    rows = merge_hit_xml(parse_hit_table_csv(hit), parse_xml2(xml))
    assert rows[0].subject_title.startswith('presqualene')
    _, qrows = summarize_results(rows)
    assert qrows[0]['followup_decision'] == 'RETAIN_PROOF_RELEVANT'


def test_ingest_followup_writes_tables_and_next_fasta(tmp_path):
    panel = tmp_path / 'panel'
    panel.mkdir()
    manifest = panel / 'AS-TEST_BGC_BLASTP_PANEL_selection_manifest.csv'
    fields = ['panel_scope','round_file','strain','bgc_id','slot','locus_tag','protein_id','contig','node_id','antismash_region','source_gbk','start','end','strand','aa_len','selection_role','selection_reason','selection_score','bgc_products','assembly_locator','product_annotation','warning','blastp_claim_safety']
    rows = [
        {'panel_scope':'curated_2_per_BGC_NCBI_safe','round_file':'old.faa','strain':'AS-TEST','bgc_id':'BGC001','slot':'1','locus_tag':'gene1','protein_id':'','contig':'ctg','node_id':'NODE_1','antismash_region':'region001','source_gbk':'','start':'1','end':'300','strand':'1','aa_len':'100','selection_role':'core','selection_reason':'PKS','selection_score':'100','bgc_products':'PKS','assembly_locator':'NODE_1','product_annotation':'PKS','warning':'','blastp_claim_safety':'safe'},
        {'panel_scope':'curated_2_per_BGC_NCBI_safe','round_file':'old.faa','strain':'AS-TEST','bgc_id':'BGC002','slot':'1','locus_tag':'gene2','protein_id':'','contig':'ctg','node_id':'NODE_2','antismash_region':'region001','source_gbk':'','start':'1','end':'300','strand':'1','aa_len':'100','selection_role':'core','selection_reason':'NRPS','selection_score':'90','bgc_products':'NRPS','assembly_locator':'NODE_2','product_annotation':'NRPS','warning':'','blastp_claim_safety':'safe'},
    ]
    with manifest.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    from mamey.bgc_blastp_panel import fasta_header, wrap_fasta
    panel.joinpath('old.faa').write_text(wrap_fasta(fasta_header('AS-TEST', rows[0])[1:], 'M'*100).replace('>>','>') + wrap_fasta(fasta_header('AS-TEST', rows[1])[1:], 'M'*100).replace('>>','>'))
    # Correct headers after using helper without leading >
    txt=''
    for r in rows:
        txt += '>' + fasta_header('AS-TEST', r)[1:] + '\n' + 'M'*100 + '\n'
    panel.joinpath('old.faa').write_text(txt)
    hit = tmp_path / 'hit.csv'
    hit.write_text(f"{fasta_header('AS-TEST', rows[0])[1:]},WP_1.1,99.0,100,1,0,1,100,1,100,0.0,200,99.0\n")
    out = tmp_path / 'out'
    summary = ingest_followup(hit, out, previous_selection=manifest, panel_dir=panel, next_proteins=10, target_residues=1000)
    assert summary['query_count'] == 1
    assert summary['next_batch_count'] == 1
    assert (out / 'BLASTP_FOLLOWUP_next_batch_round001_for_BLASTP.faa').read_text().count('>') == 1
    assert 'BGC002' in (out / 'BLASTP_FOLLOWUP_next_batch_round001_for_BLASTP.faa').read_text()


def test_headerless_hit_table_recovers_unquoted_commas_in_query_title(tmp_path):
    p = tmp_path / 'hit.csv'
    # NCBI web Hit Table can be headerless and fail to quote commas embedded in
    # the Sapote/Mamey query title, especially KCB labels such as
    # "complete genome, Type: T1PKS". The parser must join the leading fields
    # back into a single query id and keep subject_id/metrics aligned.
    p.write_text(
        'AS168|BGC008|ctg15_126|NODE_15|region002|aa=420|products=PKS;_T1PKS|role=core_or_context|kcb=Streptomyces_violaceoruber_strain_S21_chromosome,_complete_genome_|_Type:_T1PKS,'
        'RUP69732.1,96.860,414,13,0,6,419,43,456,0.0,780,99.03\n'
    )
    rows = parse_hit_table_csv(p)
    assert len(rows) == 1
    assert rows[0].query_id.endswith('Type:_T1PKS')
    assert rows[0].subject_id == 'RUP69732.1'
    assert rows[0].pct_identity == 96.86
    assert rows[0].align_len == 414
    assert rows[0].query_coverage > 0.98


# ---------------------------------------------------------------------------
# PATCH-001 (v9.7.154): space-delimited multi-query XML2 metadata merge
# ---------------------------------------------------------------------------

def test_parse_query_id_space_delimited_header():
    """Manually-built NCBI rounds use a space-delimited key=value header whose
    first token is a combined BGC<n>_<gene> id. parse_query_id must populate
    bgc_id AND gene from it (the pipe path is unaffected)."""
    from mamey.blastp_followup import parse_query_id
    h = ('BGC008_ctg162_3 contig=NODE_162 node=NODE_162 start=2859 end=3950 '
         'strand=+ kind=biosynthetic sec_met_domain=[PKS_KS]')
    m = parse_query_id(h)
    assert m['bgc_id'] == 'BGC008'
    assert m['gene'] == 'ctg162_3'
    assert m['node'] == 'NODE_162'
    assert m['start'] == '2859'
    assert m['strand'] == '+'
    assert m['kind'] == 'biosynthetic'
    # Pipe path must still decompose correctly.
    p = parse_query_id('AS-901|BGC002|slot=1|gene=ctg11_9|node=NODE_11|aa=317')
    assert p['bgc_id'] == 'BGC002'
    assert p['gene'] == 'ctg11_9'
    assert p['aa'] == '317'


def test_merge_hit_xml_multiquery_space_delimited_no_misbind():
    """4 space-delimited queries, one XML2 file (XML keyed by long titles,
    hit-table query_ids are the short combined tokens). Each row must receive
    ITS OWN title/accession/sciname, not blanks and not the first query's data.

    Before PATCH-001 this mis-bound: parse_query_id couldn't extract
    bgc_id/gene from the space-delimited header, so the fallback match
    degenerated to `None == None` (True for every XML query) and the loop bound
    the first-iterated query's hits to all four rows; the accession sub-match
    then failed, leaving 3 of 4 rows blank."""
    from mamey.blastp_followup import merge_hit_xml, HitRecord
    genes = [('ctg162_3', 'WP_AAA.1', 'alpha synthase'),
             ('ctg162_8', 'WP_BBB.1', 'beta reductase'),
             ('ctg162_11', 'WP_CCC.1', 'gamma transferase'),
             ('ctg162_12', 'WP_DDD.1', 'delta hydrolase')]
    xml_meta = {}
    for g, acc, title in genes:
        long_title = f'BGC008_{g} contig=NODE_162 node=NODE_162 kind=biosynthetic'
        xml_meta[long_title] = {
            'query_len': 300,
            'hits': [{'subject_id': acc, 'subject_accession': acc,
                      'subject_title': title, 'subject_sciname': 'Streptomyces',
                      'subject_taxid': '1883', 'hit_len': 300}],
        }
    recs = [HitRecord(query_id=f'BGC008_{g}', subject_id=acc, pct_identity=90.0,
                      align_len=300, mismatches=1, gap_opens=0, qstart=1, qend=300,
                      sstart=1, send=300, evalue=0.0, bitscore=500.0,
                      pct_positive=95.0, query_len=300)
            for g, acc, _ in genes]
    merged = merge_hit_xml(recs, xml_meta)
    titles = {r.query_id: r.subject_title for r in merged}
    accs = {r.query_id: r.subject_accession for r in merged}
    assert titles['BGC008_ctg162_3'] == 'alpha synthase'
    assert titles['BGC008_ctg162_8'] == 'beta reductase'
    assert titles['BGC008_ctg162_11'] == 'gamma transferase'
    assert titles['BGC008_ctg162_12'] == 'delta hydrolase'
    # No row may be left blank, and none may carry another query's accession.
    for g, acc, _ in genes:
        assert accs[f'BGC008_{g}'] == acc


def test_merge_hit_xml_unparseable_header_does_not_misbind():
    """Guard the truthy-check directly: if a header yields neither bgc_id nor
    gene, the fallback must leave metadata blank rather than binding the first
    XML query's hits to it."""
    from mamey.blastp_followup import merge_hit_xml, HitRecord
    xml_meta = {
        'something_unrelated': {
            'query_len': 100,
            'hits': [{'subject_id': 'WP_X.1', 'subject_accession': 'WP_X.1',
                      'subject_title': 'should not leak', 'subject_sciname': 'Foo',
                      'subject_taxid': '1', 'hit_len': 100}],
        }
    }
    rec = HitRecord(query_id='totally_opaque_token', subject_id='WP_Y.1',
                    pct_identity=80.0, align_len=100, mismatches=2, gap_opens=0,
                    qstart=1, qend=100, sstart=1, send=100, evalue=1e-9,
                    bitscore=200.0, pct_positive=88.0, query_len=100)
    merged = merge_hit_xml([rec], xml_meta)
    assert merged[0].subject_title == ''
    assert merged[0].subject_accession == ''


def test_query_summary_raw_counts_and_honest_strain():
    """PATCH-005 part 1: query_summary carries raw identical/positive counts.
    Also locks the honest-blank `strain` for space-delimited headers: the
    leading BGC###_<gene> token must NOT be written into the strain column
    (it is a bgc+gene id, not a strain name)."""
    from mamey.blastp_followup import summarize_results, HitRecord
    rec = HitRecord(
        query_id="BGC008_ctg162_3 contig=NODE_162 node=NODE_162 kind=biosynthetic",
        subject_id="WP_AAA.1", pct_identity=90.0, align_len=300, mismatches=1,
        gap_opens=0, qstart=1, qend=300, sstart=1, send=300, evalue=0.0,
        bitscore=500.0, pct_positive=95.0, query_len=300,
        subject_title="alpha synthase", subject_accession="WP_AAA.1",
        subject_sciname="Streptomyces")
    _, qrows = summarize_results([rec])
    row = qrows[0]
    assert row["bgc_id"] == "BGC008"
    assert row["gene"] == "ctg162_3"
    assert row["strain"] == ""          # honest blank, not the combined token
    assert row["top_identical_count"] == 270   # round(0.90 * 300)
    assert row["top_positive_count"] == 285    # round(0.95 * 300)
    # pct_positive None -> count must be blank, never a TypeError
    rec2 = HitRecord(
        query_id="AS-901|BGC002|gene=ctg11_9|aa=300", subject_id="WP_B.1",
        pct_identity=80.0, align_len=300, mismatches=2, gap_opens=0, qstart=1,
        qend=300, sstart=1, send=300, evalue=1e-9, bitscore=200.0,
        pct_positive=None, query_len=300, subject_title="t",
        subject_accession="WP_B.1", subject_sciname="x")
    _, qrows2 = summarize_results([rec2])
    assert qrows2[0]["top_positive"] == ""
    assert qrows2[0]["top_positive_count"] == ""


def test_parse_query_id_non_bgc_first_token_no_strain():
    """Audit hardening (v9.7.154): a space-delimited header whose first token is
    neither BGC###_<gene> nor BGC### must NOT be labelled a strain — leave it
    blank rather than guess. Real manual NCBI headers always lead with BGC###_,
    so this only guards the degenerate case; consistency with the honest-blank
    rule applied to the combined-token path."""
    from mamey.blastp_followup import parse_query_id
    m = parse_query_id("ctg162_3 node=NODE_1 kind=biosynthetic")
    assert "strain" not in m or m.get("strain") in (None, "")
    assert m.get("bgc_id", "") == ""
    # the kv pairs after the unparseable head are still captured
    assert m.get("node") == "NODE_1"
    assert m.get("kind") == "biosynthetic"
