"""Verify the biopython-free GBK parser shim provides correct record interface."""
from pathlib import Path


def test_shim_module_importable():
    from mamey._gbk_shim import parse_genbank_text, _Record, _Feature, _Location
    assert callable(parse_genbank_text)


def test_shim_parses_region_gbk():
    from mamey._gbk_shim import parse_genbank_text
    # Minimal synthetic region GBK
    gbk = (
        'LOCUS       TEST_CONTIG          5000 bp    DNA              UNK 01-JAN-1980\n'
        'DEFINITION  test contig.\n'
        'ACCESSION   TEST_CONTIG\n'
        'VERSION     TEST_CONTIG.1\n'
        'COMMENT     ##antiSMASH-Data-START##\n'
        '            Orig. start :: 10000\n'
        '            Orig. end   :: 15000\n'
        '            ##antiSMASH-Data-END##\n'
        'FEATURES             Location/Qualifiers\n'
        '     region          1..5000\n'
        '                     /contig_edge="False"\n'
        '                     /product="NRPS"\n'
        '                     /region_number="3"\n'
        '                     /tool="antismash"\n'
        '     CDS             100..900\n'
        '                     /locus_tag="ctg1_1"\n'
        '                     /gene_functions="biosynthetic"\n'
        '                     /product="condensation"\n'
        '                     /translation="MTEST"\n'
        'ORIGIN\n'
        '        1 atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat\n'
        '//\n'
    )
    records = parse_genbank_text(gbk)
    assert len(records) == 1
    rec = records[0]
    assert rec.id == 'TEST_CONTIG.1'
    assert len(rec.seq) > 0
    # Region feature
    region_feats = [f for f in rec.features if f.type == 'region']
    assert len(region_feats) == 1
    rf = region_feats[0]
    assert rf.qualifiers['product'] == ['NRPS']
    assert rf.qualifiers['contig_edge'] == ['False']
    assert rf.qualifiers['region_number'] == ['3']
    # CDS feature
    cds_feats = [f for f in rec.features if f.type == 'CDS']
    assert len(cds_feats) >= 1
    cds = cds_feats[0]
    assert cds.qualifiers['locus_tag'] == ['ctg1_1']
    assert cds.qualifiers['product'] == ['condensation']
    assert cds.location.start == 99  # 0-based
    assert cds.location.end == 900


def test_parsers_fallback_active():
    """Confirm parsers.py uses shim when biopython unavailable."""
    text = Path('mamey/parsers.py').read_text(encoding='utf-8')
    assert 'from ._gbk_shim import parse_genbank_text' in text
    assert 'if SeqIO is not None:' in text
