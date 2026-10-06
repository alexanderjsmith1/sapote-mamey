"""Read-only synthetic cross-review reproductions; no real GECCO/source data."""
import csv
import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from tests.test_447_companion_class_evidence import fixture, mocked_gecco, score
from mamey import gecco_crosscheck as G, metabolomics_bridge as M, nonks_second_proof as N
from mamey.postseal_output import package_binding


def test_gecco_foreign_strain_gap_row_is_refused(fixture,mocked_gecco):
    f=fixture;gap=f.out.parent/'foreign_gap.csv'
    gap.write_text('strain,contig,locus_tag,start,end\nFOREIGN-2,NODE_1_length_900_cov_7.0,g1,801,890\n')
    with pytest.raises(ValueError,match='STRAIN_MISMATCH'):
        G.crosscheck(f.package,f.archive,f.out,gap_genes=[gap])
    assert not f.out.exists()


def test_gap_duplicate_columns_are_refused(fixture,mocked_gecco):
    f=fixture;gap=f.out.parent/'duplicate_gap.csv'
    gap.write_text('locus_tag,locus_tag\nnot_in_source,g1\n')
    with pytest.raises(ValueError,match='TABLE_SCHEMA_INVALID'):
        G.crosscheck(f.package,f.archive,f.out,gap_genes=[gap])
    assert not f.out.exists()


@pytest.mark.parametrize('invalid',[-1,float('nan'),'0',True])
def test_invalid_nonks_domain_count_is_refused(fixture,invalid):
    f=fixture;scans=f.manifest['source_scans']['domain_architecture']['per_bgc']
    scans['BGC001']={'domain_counts':{'NRPS_A':invalid}}
    scans['BGC002']={'domain_counts':{}}
    row={**f.rgg,'verdict':'RGGMCI_ONLY','ks_clade_id':''}
    with pytest.raises(ValueError,match='DOMAIN_COUNT_INVALID'):
        N.apply_policy([row],f.manifest,[score(f)],N.POSITION_POLICY)
    assert N.apply_policy([row],f.manifest,policy=N.DEFAULT_POLICY)[0]['verdict']=='RGGMCI_ONLY'


def test_unparseable_region_bytes_refuse_before_publication(fixture):
    f=fixture
    with zipfile.ZipFile(f.archive,'w') as archive:
        for bgc in f.manifest['bgcs']:archive.writestr(bgc['source_gbk'],b'not GenBank; synthetic malformed fixture')
    f.manifest['input_zip_sha256']=hashlib.sha256(f.archive.read_bytes()).hexdigest()
    (f.package/'manifest.json').write_text(json.dumps(f.manifest))
    before=package_binding(f.package)
    with pytest.raises(ValueError,match='REGION_DECLARATION_INVALID'):
        M.export_metabolomics(f.package,f.out,f.archive)
    assert not f.out.exists()
    assert package_binding(f.package)==before


def test_external_publication_and_wrong_source_digest_controls(fixture,mocked_gecco):
    f=fixture;before=package_binding(f.package)
    with pytest.raises(ValueError,match='INSIDE_PACKAGE'):G.crosscheck(f.package,f.archive,f.package/'bad')
    assert not (f.package/'bad').exists() and package_binding(f.package)==before
    f.archive.write_bytes(f.archive.read_bytes()+b'synthetic changed bytes')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):M.export_metabolomics(f.package,f.out,f.archive)
    assert not f.out.exists()


def test_optional_cli_defaults_and_flag_contract_control():
    from mamey.cli import build_parser
    parser=build_parser()
    assert parser.parse_args(['gecco-crosscheck','--package','synthetic','--zip','source']).jobs==1
    assert parser.parse_args(['two-proof-rescue','--package','synthetic']).policy==N.DEFAULT_POLICY


@pytest.mark.parametrize('columns,values',[
 ('start,end','801,890'),('start_0based,end_exclusive','30,89'),
 ('start_1based,end_inclusive','30,90'),('start','31'),
 ('locus_tag,query_gene','g1,g2')])
def test_gecco_supplied_coordinate_or_alias_conflicts_refuse(fixture,mocked_gecco,columns,values):
    f=fixture;gap=f.out.parent/'wrong_coords.csv'
    # Identifier aliases case supplies its own locus_tag; others use one known identifier.
    if columns.startswith('locus_tag'):gap.write_text(columns+'\n'+values+'\n')
    else:gap.write_text('strain,locus_tag,'+columns+'\nSYN-1,g1,'+values+'\n')
    with pytest.raises(ValueError,match='GECCO_GAP_'):
        G.crosscheck(f.package,f.archive,f.out,gap_genes=[gap])
    assert not f.out.exists()


@pytest.mark.parametrize('header,value,scope',[
 ('locus_tag','g1','SOURCE_LOCUS_TAG_ONLY'),
 ('strain,contig,locus_tag,start,end','SYN-1,NODE_1_length_900_cov_7.0,g1,31,90','SOURCE_LOCUS_TAG_AND_SUPPLIED_COORDINATES'),
 ('locus_tag,start_0based,end_exclusive','g1,30,90','SOURCE_LOCUS_TAG_AND_SUPPLIED_COORDINATES')])
def test_gecco_legitimate_coordinate_and_tag_only_controls(fixture,mocked_gecco,header,value,scope):
    f=fixture;gap=f.out.parent/'valid_gap.csv';gap.write_text(header+'\n'+value+'\n')
    G.crosscheck(f.package,f.archive,f.out,gap_genes=[gap])
    row=next(csv.DictReader((f.out/'valid_gap_gecco.csv').open()))
    assert row['gecco_mean_p']=='0.9' and row['gecco_binding_scope']==scope


@pytest.mark.parametrize('entry',[
 {'domain':'NRPS_A'},
 {'domain':'NRPS_A','contig':'FOREIGN','start':31,'end':40},
 {'domain':'NRPS_A','contig':'NODE_1_length_900_cov_7.0','start':0,'end':40},
 {'domain':'NRPS_A','contig':'NODE_1_length_900_cov_7.0','start':301,'end':340}])
def test_nonks_unbound_or_nonpositive_domain_entries_refuse(fixture,entry):
    f=fixture;scans=f.manifest['source_scans']['domain_architecture']['per_bgc']
    scans['BGC001']['domains']=[entry]
    with pytest.raises(ValueError,match='NONKS_DOMAIN_'):
        N.apply_policy([{**f.rgg,'verdict':'RGGMCI_ONLY','ks_clade_id':''}],f.manifest,[score(f)],N.POSITION_POLICY)


def test_nonks_valid_bound_entry_and_zero_or_absent_counts_controls(fixture):
    f=fixture;scans=f.manifest['source_scans']['domain_architecture']['per_bgc']
    scans['BGC001']['domains']=[dict(domain='AMP-binding',classes=['NRPS_A'],contig=f.manifest['bgcs'][0]['contig'],start=31,end=40)]
    row={**f.rgg,'verdict':'RGGMCI_ONLY','ks_clade_id':''}
    assert N.apply_policy([row],f.manifest,[score(f)],N.POSITION_POLICY)[0]['verdict']=='TWO_PROOF_RESCUE'
    for counts in ({'NRPS_A':0},{}):
        scans['BGC001']['domain_counts']=counts;scans['BGC002']['domain_counts']={}
        assert N.apply_policy([row],f.manifest,[score(f)],N.POSITION_POLICY)[0]['verdict']=='RGGMCI_ONLY'


def region_damage(f,damage):
    import io
    from Bio import SeqIO
    members={}
    with zipfile.ZipFile(f.archive) as archive:
        for item in archive.infolist():members[item.filename]=archive.read(item)
    name=f.manifest['bgcs'][0]['source_gbk']
    record=next(SeqIO.parse(io.StringIO(members[name].decode()),'genbank'))
    if damage=='contig':record.id='FOREIGN';record.name='FOREIGN'
    if damage=='bounds':record.annotations['structured_comment']['antiSMASH-Data']['Orig. start']='20'
    if damage=='missing_bounds':record.annotations.pop('structured_comment')
    if damage=='number':record.features[0].qualifiers['region_number']=['9']
    if damage=='missing_cds':record.features=[x for x in record.features if x.type!='CDS']
    if damage=='duplicate_locus':record.features.append(record.features[1])
    if damage=='cds_coord':
        from Bio.SeqFeature import FeatureLocation
        record.features[1].location=FeatureLocation(30,250)
    buffer=io.StringIO();SeqIO.write([record],buffer,'genbank');members[name]=buffer.getvalue().encode()
    if damage=='multiple_records':members[name]+=members[name]
    if damage=='truncated':members[name]=members[name].replace(b'//\n',b'')
    if damage=='partial_marker':members[name]=members[name].replace(b':: 0',b':: <0').replace(b':: 200',b':: >200')
    with zipfile.ZipFile(f.archive,'w') as archive:
        for name,data in members.items():archive.writestr(name,data)
    f.manifest['input_zip_sha256']=hashlib.sha256(f.archive.read_bytes()).hexdigest()
    (f.package/'manifest.json').write_text(json.dumps(f.manifest))


@pytest.mark.parametrize('damage',['contig','bounds','missing_bounds','number','missing_cds','duplicate_locus','cds_coord','multiple_records','truncated'])
def test_metabolomics_wrong_or_ambiguous_region_declarations_refuse(fixture,damage):
    f=fixture;region_damage(f,damage)
    before=package_binding(f.package)
    with pytest.raises(ValueError,match='REGION_DECLARATION_INVALID'):M.export_metabolomics(f.package,f.out,f.archive)
    assert not f.out.exists() and package_binding(f.package)==before


def test_metabolomics_valid_partial_markers_preserve_exact_bytes_and_binding(fixture):
    f=fixture;region_damage(f,'partial_marker')
    M.export_metabolomics(f.package,f.out,f.archive)
    pointers=json.loads((f.out/'nplinker/source_pointers.json').read_text())
    with zipfile.ZipFile(f.archive) as archive:
        for pointer in pointers:
            assert (f.out/'nplinker'/pointer['staged_file']).read_bytes()==archive.read(pointer['source_member'])
            assert pointer['declaration']['state']=='REGION_DECLARATION_BOUND'
            assert pointer['declaration']['cds_locus_tags']


def test_gecco_invalid_source_cds_range_refuses_before_job(fixture,mocked_gecco):
    import io
    from Bio import SeqIO
    from Bio.SeqFeature import FeatureLocation
    f=fixture
    with zipfile.ZipFile(f.archive) as archive:
        members={x.filename:archive.read(x) for x in archive.infolist()}
    records=list(SeqIO.parse(io.StringIO(members['source.gbk'].decode()),'genbank'))
    records[0].features[0].location=FeatureLocation(30,1000)
    buffer=io.StringIO();SeqIO.write(records,buffer,'genbank');members['source.gbk']=buffer.getvalue().encode()
    with zipfile.ZipFile(f.archive,'w') as archive:
        for name,data in members.items():archive.writestr(name,data)
    f.manifest['input_zip_sha256']=hashlib.sha256(f.archive.read_bytes()).hexdigest()
    (f.package/'manifest.json').write_text(json.dumps(f.manifest))
    with pytest.raises(ValueError,match='SOURCE_CDS_COORDINATE_INVALID'):G.crosscheck(f.package,f.archive,f.out)
    assert len(mocked_gecco)==1 and '--version' in mocked_gecco[0]
    assert not f.out.exists()


def test_nonks_domain_end_outside_bound_contig_is_refused(fixture):
    bgc=fixture.manifest['bgcs'][0];bgc['contig_length']=900
    domains={'domain_counts':{'NRPS_A':1},'domains':[dict(domain='AMP-binding',contig=bgc['contig'],start=31,end=901)]}
    with pytest.raises(ValueError,match='DOMAIN_COORDINATE_INVALID'):N.class_state(bgc,domains)
