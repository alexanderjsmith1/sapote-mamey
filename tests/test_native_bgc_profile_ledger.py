"""Known-answer native attribution; colliding aliases never share measurements."""
import copy

from mamey.crosswalk import infer_node_id
from mamey.models import BGCRecord, CDSFeature, DomainFeature
from mamey.source_scans import (
    _native_bgc_profiles, scan_domain_architecture, bgc_coupling, apply_cctt_vetoes,
    couple_kcb_ptm, resistance_tier_classification, scan_blda_tta, scan_umed,
)


def native_collision_fixture(*, collision=True, extra_zero=False, return_inputs=False):
    contigs = ['NODE_1_length_1000_cov_1.5', 'CP123456.2']
    bgcs = [BGCRecord('BGC001', contigs[0], 1, 0, 1000, 1000, products=['lanthipeptide'],
                      node_id=infer_node_id(contigs[0], ''), antismash_region='region001'),
            BGCRecord('BGC001' if collision else 'BGC002', contigs[1], 1, 0, 1000, 1000,
                      products=['other'], node_id=infer_node_id(contigs[1], ''), antismash_region='region001')]
    if extra_zero:
        bgcs.append(BGCRecord('BGC003', 'ctg3_segment', 3, 0, 1000, 1000, products=['other'],
                             node_id='ctg3', antismash_region='region003'))
    cds = [CDSFeature(contigs[0], 10, 30, 1, 'fixture_a', 'synthetic annotation', nucleotide_seq='TTATTA'),
           CDSFeature(contigs[1], 10, 30, 1, 'fixture_b', 'synthetic annotation', nucleotide_seq='ATGATG')]
    def domain(contig, token, kind='aSDomain', start=10):
        return DomainFeature(contig, start, start+5, 1, kind, 'fixture', token, 'synthetic')
    domains = [domain(contigs[0], 'PKS_KS'), domain(contigs[0], 'PKS_KS', start=20),
               domain(contigs[0], 'PKS_KS', 'aSModule'), domain(contigs[0], 'PKS_KS', 'CDS_motif'),
               domain(contigs[1], 'AMP-binding')]
    def hit(contig):
        return {'contig': contig, 'start': 10, 'end': 30, 'strand': 1,
                'locus_tag': 'synthetic', 'product': 'synthetic annotation'}
    architecture = scan_domain_architecture(bgcs, domains)
    raw = {'blda': {'per_bgc': {'BGC001': {'tta_codons': 999}}},
           'cctt': {'hits': {'T43-HAL_halogenation': [hit(contigs[0])],
                             'T43-LAN_lanthipeptide': [hit(contigs[1])]},
                    'bgc_coupling': {'BGC001': ['COLLAPSED_SENTINEL']}},
           'flbr': {'hits': {}},
           'resistance': {'hits': {'Erm_methylase': [hit(contigs[0])]}, 'bgc_coupling': {'BGC001': ['WRONG']}},
           'transporters': {'hits': {'ABC': [hit(contigs[1])]}, 'bgc_coupling': {'BGC001': ['WRONG']}},
           'umed': {'hits': {'maturation': [hit(contigs[0])]}, 'per_bgc': {'BGC001': {'verdict': 'WRONG'}}}}
    raw_before = copy.deepcopy(raw)
    old_architecture = copy.deepcopy({k: v for k, v in architecture.items() if k != 'native_architecture_records_v1'})
    ledger = _native_bgc_profiles(bgcs, cds, architecture, **raw, organism='Streptomyces sp.')
    assert raw == raw_before
    assert architecture == old_architecture
    if return_inputs:
        return bgcs, ledger, architecture, cds, raw
    return bgcs, ledger, architecture


def test_all_five_channels_are_independently_attributed_despite_alias_collision():
    bgcs, ledger, legacy = native_collision_fixture()
    a, b = ledger['records']
    assert [r['identity']['bgc_id'] for r in ledger['records']] == ['BGC001', 'BGC001']
    assert [r['identity']['contig'] for r in ledger['records']] == [bgc.contig for bgc in bgcs]
    assert a['architecture']['domain_counts'] == {'PKS_KS': 2}
    assert b['architecture']['domain_counts'] == {'NRPS_A': 1}
    assert a['architecture']['module_count'] == 1
    assert a['architecture']['domain_hit_count'] == 4
    assert b['architecture']['domain_hit_count'] == 1
    assert (a['tta']['tta_codons'], a['tta']['tta_cds']) == (2, 1)
    assert (b['tta']['tta_codons'], b['tta']['tta_cds']) == (0, 0)
    assert a['resistance']['tier'] == 'T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED'
    assert b['resistance']['tier'] == 'T3_TRANSPORTER_ONLY_ROUTING'
    assert a['umed']['verdict'] == 'IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED'
    assert b['umed']['verdict'] == 'NOT_MATURATION_GATED'
    assert a['cctt_triggers'] == ['T43-HAL_halogenation']
    assert b['cctt_triggers'] == ['T43-LAN_lanthipeptide']
    # Historical alias accumulator remains merged; native records do not copy it.
    assert set(legacy['per_bgc']) == {'BGC001'}
    assert legacy['per_bgc']['BGC001']['domain_counts'] == {'PKS_KS': 2, 'NRPS_A': 1}
    assert legacy['per_bgc']['BGC001']['domain_hit_count'] == 5


def test_unique_alias_architecture_projection_equals_entire_legacy_measurement_record():
    _, ledger, legacy = native_collision_fixture(collision=False)
    for record in ledger['records']:
        assert record['architecture'] == legacy['per_bgc'][record['identity']['bgc_id']]


def test_zero_is_explicitly_measured_and_keeps_source_record():
    _, ledger, _ = native_collision_fixture(extra_zero=True)
    zero = ledger['records'][2]
    assert zero['architecture'] == {'domain_counts': {}, 'domains': [], 'module_count': 0,
                                     'core_summary': [], 'domain_hit_count': 0}
    assert zero['tta']['tta_codons'] == 0
    assert zero['cctt_triggers'] == []
    assert set(zero['coverage'].values()) == {'MEASURED'}


def _default_channel_maps(bgcs, cds, raw):
    cctt = {'bgc_coupling': bgc_coupling(bgcs, raw['cctt'])}
    cctt = apply_cctt_vetoes(cctt, bgcs, cds)
    cctt = couple_kcb_ptm(bgcs, cctt, {'bgc_coupling': bgc_coupling(bgcs, raw['flbr'])})
    resistance = {'bgc_coupling': bgc_coupling(bgcs, raw['resistance'])}
    transport = {'bgc_coupling': bgc_coupling(bgcs, raw['transporters'])}
    return {'tta': scan_blda_tta(cds, bgcs, organism='Streptomyces sp.')['per_bgc'],
            'resistance': resistance_tier_classification(bgcs, resistance, transport, cds_list=cds)['per_bgc'],
            'umed': scan_umed(cds, bgcs, _hits=raw['umed'])['per_bgc'],
            'cctt_triggers': cctt['bgc_coupling']}


def test_entire_unique_alias_channel_dictionaries_match_default_legacy_functions():
    bgcs, ledger, architecture, cds, raw = native_collision_fixture(collision=False, return_inputs=True)
    defaults = _default_channel_maps(bgcs, cds, raw)
    defaults['architecture'] = architecture['per_bgc']
    for channel, old_map in defaults.items():
        new_map = {row['identity']['bgc_id']: row[channel] for row in ledger['records']}
        assert new_map == old_map


def test_legacy_collision_merge_and_overwrite_contracts_remain_explicit():
    bgcs, ledger, architecture, cds, raw = native_collision_fixture(return_inputs=True)
    defaults = _default_channel_maps(bgcs, cds, raw)
    assert set(defaults['tta']) == set(defaults['resistance']) == set(defaults['umed']) == {'BGC001'}
    assert defaults['tta']['BGC001']['tta_codons'] == 2
    assert defaults['tta']['BGC001']['total_cds'] == 2
    assert defaults['resistance']['BGC001']['tier'] == 'T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED'
    assert defaults['umed']['BGC001']['verdict'] == 'NOT_MATURATION_GATED'
    assert defaults['cctt_triggers'] == {'BGC001': ['T43-HAL_halogenation', 'T43-LAN_lanthipeptide']}
    assert architecture['per_bgc']['BGC001']['domain_counts'] == {'PKS_KS': 2, 'NRPS_A': 1}
    assert ledger['records'][1]['resistance']['tier'] != defaults['resistance']['BGC001']['tier']
