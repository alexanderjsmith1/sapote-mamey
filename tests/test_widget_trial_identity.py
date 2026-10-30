import csv,json
import pytest
from mamey import widget_deliverable as w

def package(tmp_path,change=None):
    p=tmp_path/'package';p.mkdir()
    (p/'manifest.json').write_text(json.dumps({'strain_id':'TEST'}))
    inv=[{'BGC_ID':'r1','Contig':'NODE_1_length_5000_cov_20','Region':'1','Strain':'TEST'}]
    genes=[{'bgc_id':'r1','contig':inv[0]['Contig'],'region':'region001','strain':'TEST','locus_tag':'gene1','aa_length':'20'}]
    if change=='missing_contig':inv[0]['Contig']=''
    if change=='missing_region':inv[0]['Region']=''
    if change=='duplicate_alias':inv.append(dict(inv[0]))
    if change=='gene_contig':genes[0]['contig']='other_contig'
    if change=='gene_region':genes[0]['region']='region002'
    if change=='gene_strain':genes[0]['strain']='OTHER'
    for suffix,rows in [('_2_inventory.csv',inv),('_gene_by_gene_all_bgcs.csv',genes),('_perBGC_domain_heatmap_data.csv',[{'bgc_id':'r1','PKS_KS':'0'}])]:
        with (p/('TEST'+suffix)).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return p

def load(p):
    source=w.PackageSource(p)
    try:return w._load_model(source)
    finally:source.close()

def test_full_identity_survives_projection(tmp_path):
    model=load(package(tmp_path))
    for key in ['priority','domains','genes']:
        row=model[key][0]
        assert row['full_identity']=='TEST / NODE_1_length_5000_cov_20 / region001 / r1'
        assert row['region']=='region001'
        assert row['contig']=='NODE_1_length_5000_cov_20'

@pytest.mark.parametrize('change',['missing_contig','missing_region','duplicate_alias','gene_contig','gene_region','gene_strain'])
def test_identity_conflict_refused(tmp_path,change):
    with pytest.raises(ValueError,match='WIDGET_IDENTITY_'):
        load(package(tmp_path,change))

@pytest.mark.parametrize('change',['valid','unbound','contig_conflict'])
def test_pair_endpoints_bound_independently(tmp_path,change):
    p=package(tmp_path)
    row={'bgc_a':'r1','bgc_b':'r1','contig_a':'NODE_1_length_5000_cov_20','contig_b':'NODE_1_length_5000_cov_20'}
    if change=='unbound':row['bgc_b']='unknown'
    if change=='contig_conflict':row['contig_b']='other'
    with (p/'TEST_4A_RGGMCI_ranked_pairs.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    if change!='valid':
        with pytest.raises(ValueError,match='WIDGET_IDENTITY_'):load(p)
    else:
        model=load(p);pair=model['rggmci'][0]
        assert pair['full_identity_a']==model['priority'][0]['full_identity']
        assert pair['full_identity_b']==pair['full_identity_a']
        assert pair['region_a']==pair['region_b']=='region001'

def test_unknown_domain_alias_refused(tmp_path):
    p=package(tmp_path)
    (p/'TEST_perBGC_domain_heatmap_data.csv').write_text('bgc_id,PKS_KS\nunknown,0\n')
    with pytest.raises(ValueError,match='WIDGET_IDENTITY_UNBOUND'):load(p)


def write_domain_rows(p, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (p / 'TEST_perBGC_domain_heatmap_data.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_native_exact_locus_domain_export_binds_without_shortening(tmp_path):
    p = package(tmp_path)
    exact = 'TEST / NODE_1_length_5000_cov_20 / region001 / r1'
    write_domain_rows(p, [{'exact_locus': exact, 'PKS_KS': '13.0', 'NRPS_A': '8.0'}])
    model = load(p)
    row = model['domains'][0]
    assert row['full_identity'] == exact
    assert row['bgc_id'] == 'r1'
    assert row['PKS_KS'] == 13 and row['NRPS_A'] == 8 and row['total'] == 21
    assert model['domain_coverage']['status'] == 'COMPLETE'


@pytest.mark.parametrize('extra', [
    {'bgc_id': 'other'}, {'BGC_ID': 'other'},
    {'bgc_id': 'r1', 'BGC_ID': 'other'},
])
def test_exact_locus_rejects_conflicting_alias_columns(tmp_path, extra):
    p = package(tmp_path)
    row = {'exact_locus': 'TEST / NODE_1_length_5000_cov_20 / region001 / r1', 'PKS_KS': '1'}
    row.update(extra)
    write_domain_rows(p, [row])
    with pytest.raises(ValueError, match='WIDGET_IDENTITY_CONFLICT'):
        load(p)


@pytest.mark.parametrize('exact', [
    'OTHER / NODE_1_length_5000_cov_20 / region001 / r1',
    'TEST / OTHER / region001 / r1',
    'TEST / NODE_1_length_5000_cov_20 / region002 / r1',
    'r1',
])
def test_unknown_exact_identity_cannot_fall_back_to_known_alias(tmp_path, exact):
    p = package(tmp_path)
    write_domain_rows(p, [{'exact_locus': exact, 'bgc_id': 'r1', 'PKS_KS': '1'}])
    with pytest.raises(ValueError, match='WIDGET_IDENTITY_UNBOUND'):
        load(p)


@pytest.mark.parametrize('extra', [{'strain': 'OTHER'}, {'contig': 'OTHER'}, {'region': 'region002'}])
def test_exact_locus_keeps_explicit_field_conflict_checks(tmp_path, extra):
    p = package(tmp_path)
    row = {'exact_locus': 'TEST / NODE_1_length_5000_cov_20 / region001 / r1', 'PKS_KS': '1'}
    row.update(extra)
    write_domain_rows(p, [row])
    with pytest.raises(ValueError, match='WIDGET_IDENTITY_CONFLICT'):
        load(p)


def test_repeated_exact_domain_rows_remain_inconsistent(tmp_path):
    p = package(tmp_path)
    row = {'exact_locus': 'TEST / NODE_1_length_5000_cov_20 / region001 / r1', 'PKS_KS': '0'}
    write_domain_rows(p, [row, dict(row)])
    model = load(p)
    assert len(model['domains']) == 2
    assert model['domain_coverage']['status'] == 'INCONSISTENT'
    assert model['domain_coverage']['duplicate_rows'] == 1
