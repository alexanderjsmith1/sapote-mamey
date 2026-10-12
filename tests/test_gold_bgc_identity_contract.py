"""Producer-to-renderer identity contract; actual native synthetic measurements."""
import copy
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pytest

from mamey.deep_data import PROFILE_DOMAINS, build_deep_data_files, extract_profiles
from mamey.gold_bgc_identity import (
    GoldBGCIdentityError, admit_gold_profiles, load_gold_identity_context,
)
from .test_native_bgc_profile_ledger import native_collision_fixture


def _dump(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')


def package_fixture(tmp_path, *, collision=True, extra_zero=False, strain='SYNTHETIC_GOLD'):
    package = tmp_path / strain / 'package'
    package.mkdir(parents=True)
    bgcs, ledger, architecture = native_collision_fixture(collision=collision, extra_zero=extra_zero)
    architecture['native_bgc_profiles_v1'] = ledger
    manifest = {'strain_id': strain, 'release': 'PRIVATE', 'bgcs': [asdict(b) for b in bgcs],
                'source_scans': {'domain_architecture': architecture}, 'taxonomy': 'Syntheticus sp.'}
    _dump(package / 'manifest.json', manifest)
    _dump(package / f'{strain}_Project_Memory_Snapshot.json', {'alias_of': 'manifest.json'})
    _dump(package / 'manifest_short.json', {'strain_id': strain, 'taxonomy': 'Syntheticus sp.'})
    write_inventory(package, strain, manifest['bgcs'])
    build_deep_data_files(package, strain)
    return package, strain, manifest


def write_inventory(package, strain, bgcs):
    fields = ['Strain', 'Contig', 'Node_ID', 'antiSMASH_Region', 'BGC_ID', 'Region']
    with (package / f'{strain}_2_inventory.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for bgc in bgcs:
            writer.writerow(dict(zip(fields, [strain, bgc['contig'], bgc['node_id'],
                                              bgc['antismash_region'], bgc['bgc_id'], bgc['region_number']])))


def payload(package):
    return tuple(json.loads((package / name).read_text()) for name in ('deep_data.json', 'gene_data.json'))


def test_collision_profiles_preserve_all_known_answer_values_and_exact_physical_identity(tmp_path):
    package, strain, _ = package_fixture(tmp_path)
    deep, gene = payload(package)
    profiles, context = admit_gold_profiles(package, strain, deep, gene)
    assert len(profiles) == context['receipt']['records'] == 2
    assert [p['bgc_id'] for p in profiles] == ['BGC001', 'BGC001']
    assert [p['PKS_KS'] for p in profiles] == [2, 0]
    assert [p['NRPS_A'] for p in profiles] == [0, 1]
    assert [p['tta_codons'] for p in profiles] == [2, 0]
    assert [p['resistance_tier'] for p in profiles] == ['T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED', 'T3_TRANSPORTER_ONLY_ROUTING']
    assert [p['umed_verdict'] for p in profiles] == ['IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED', 'NOT_MATURATION_GATED']
    assert [p['cctt_triggers'] for p in profiles] == ['T43-HAL_halogenation', 'T43-LAN_lanthipeptide']
    assert profiles[0]['exact_locus'] == f'{strain} / NODE_1_length_1000_cov_1.5 / region001 / BGC001'
    assert profiles[1]['exact_locus'] == f'{strain} / CP123456.2 / region001 / BGC001'
    assert profiles[0]['bgc_identity']['node_id'] != profiles[0]['bgc_identity']['contig']


def test_unique_alias_numeric_and_architecture_legacy_parity_for_every_column(tmp_path):
    package, strain, manifest = package_fixture(tmp_path, collision=False)
    # Independently supply legacy channel values from the known-answer fixture.
    legacy = copy.deepcopy(manifest)
    legacy['source_scans'].update(
        blda_tta={'per_bgc': {'BGC001': {'tta_codons': 2, 'tta_cds': 1}, 'BGC002': {'tta_codons': 0, 'tta_cds': 0}}},
        resistance_tiers={'per_bgc': {'BGC001': {'tier': 'T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED'}, 'BGC002': {'tier': 'T3_TRANSPORTER_ONLY_ROUTING'}}},
        umed={'per_bgc': {'BGC001': {'verdict': 'IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED'}, 'BGC002': {'verdict': 'NOT_MATURATION_GATED'}}},
        cctt={'bgc_coupling': {'BGC001': ['T43-HAL_halogenation'], 'BGC002': ['T43-LAN_lanthipeptide']}})
    old_profiles, old_arch, old_hits = extract_profiles(strain, legacy)
    deep, gene = payload(package)
    columns = ['sid', 'bgc_id', 'tta_codons', 'tta_cds', 'resistance_tier', 'umed_verdict',
               'cctt_triggers', 'total_domains', *PROFILE_DOMAINS]
    assert [{k: r[k] for k in columns} for r in old_profiles] == [{k: r[k] for k in columns} for r in deep['bgc_profile']]
    assert [r['architecture'] for r in old_arch] == [r['architecture'] for r in gene['domain_arch']]
    assert deep['domain_hits'] == old_hits


@pytest.mark.parametrize('where', ['manifest', 'inventory', 'producer', 'profile', 'architecture'])
def test_duplicate_rows_hold_instead_of_deduplicating(tmp_path, where):
    package, strain, manifest = package_fixture(tmp_path)
    deep, gene = payload(package)
    if where == 'manifest':
        manifest['bgcs'].append(copy.deepcopy(manifest['bgcs'][0])); _dump(package / 'manifest.json', manifest)
    elif where == 'inventory':
        write_inventory(package, strain, manifest['bgcs'] + [manifest['bgcs'][0]])
    elif where == 'producer':
        records = manifest['source_scans']['domain_architecture']['native_bgc_profiles_v1']['records']
        records.append(copy.deepcopy(records[0])); _dump(package / 'manifest.json', manifest)
    elif where == 'profile':
        deep['bgc_profile'].append(copy.deepcopy(deep['bgc_profile'][0]))
    else:
        gene['domain_arch'].append(copy.deepcopy(gene['domain_arch'][0]))
    with pytest.raises(GoldBGCIdentityError):
        admit_gold_profiles(package, strain, deep, gene)


@pytest.mark.parametrize('field,value', [('contig', ''), ('node_id', ''), ('antismash_region', ''),
                                         ('bgc_id', ''), ('node_id', 'NODE_1'), ('Contig', 'CONFLICT')])
def test_missing_or_conflicting_native_identity_cannot_be_repaired(tmp_path, field, value):
    package, strain, manifest = package_fixture(tmp_path)
    manifest['bgcs'][0][field] = value
    _dump(package / 'manifest.json', manifest)
    with pytest.raises(GoldBGCIdentityError, match='GOLD_IDENTITY_'):
        load_gold_identity_context(package, strain)


@pytest.mark.parametrize('damage', ['source_order', 'missing_channel', 'missing_coverage', 'missing_record', 'extra_inventory', 'wrong_strain', 'swapped_profiles', 'value_changed', 'source_changed'])
def test_source_measurement_binding_is_revalidated(tmp_path, damage):
    package, strain, manifest = package_fixture(tmp_path)
    deep, gene = payload(package)
    records = manifest['source_scans']['domain_architecture']['native_bgc_profiles_v1']['records']
    if damage == 'source_order': records[0]['source_record_index'] = 2
    if damage == 'missing_channel': records[0].pop('tta')
    if damage == 'missing_coverage': records[0]['coverage'].pop('tta')
    if damage == 'missing_record': records.pop()
    if damage == 'extra_inventory': (package / 'extra_2_inventory.csv').write_text('BGC_ID\n')
    if damage == 'wrong_strain': deep['bgc_profile'][0]['sid'] = 'OTHER_SYNTHETIC'
    if damage == 'swapped_profiles':
        deep['bgc_profile'][0]['bgc_identity'], deep['bgc_profile'][1]['bgc_identity'] = deep['bgc_profile'][1]['bgc_identity'], deep['bgc_profile'][0]['bgc_identity']
    if damage == 'value_changed': deep['bgc_profile'][0]['PKS_KS'] = 999
    if damage == 'source_changed': records[0]['architecture']['domain_counts']['PKS_KS'] = 3
    _dump(package / 'manifest.json', manifest)
    with pytest.raises(GoldBGCIdentityError):
        admit_gold_profiles(package, strain, deep, gene)


def test_measured_zero_retained_but_missing_coverage_held(tmp_path):
    package, strain, manifest = package_fixture(tmp_path, extra_zero=True)
    deep, gene = payload(package)
    profiles, _ = admit_gold_profiles(package, strain, deep, gene)
    assert profiles[2]['total_domains'] == profiles[2]['tta_codons'] == 0
    assert profiles[2]['identity_state'] == 'BOUND_NATIVE_INVENTORY'
    manifest['source_scans']['domain_architecture']['native_bgc_profiles_v1']['records'][2]['coverage']['architecture'] = 'MISSING'
    _dump(package / 'manifest.json', manifest)
    with pytest.raises(GoldBGCIdentityError, match='GOLD_MEASUREMENT_COVERAGE_UNAVAILABLE'):
        admit_gold_profiles(package, strain, deep, gene)


def test_same_alias_across_strains_remains_separate(tmp_path):
    packages = [package_fixture(tmp_path, strain=strain) for strain in ('SYNTHETIC_A', 'SYNTHETIC_B')]
    labels = []
    for package, strain, _ in packages:
        profiles, _ = admit_gold_profiles(package, strain, *payload(package))
        labels.extend(p['exact_locus'] for p in profiles)
    assert len(set(labels)) == 4


def test_snapshot_alias_cannot_escape_same_package(tmp_path):
    package, strain, _ = package_fixture(tmp_path)
    _dump(package / f'{strain}_Project_Memory_Snapshot.json', {'alias_of': '../manifest.json'})
    result = build_deep_data_files(package, strain)
    assert result['identity']['status'] == 'HOLD'
    assert result['identity']['reason'] == 'GOLD_IDENTITY_SNAPSHOT_ALIAS_INVALID'


def test_both_real_panels_and_typed_sidecars_preserve_separate_alias_loci(tmp_path):
    pytest.importorskip('matplotlib')
    from mamey import cohort_figures as figures
    package, strain, _ = package_fixture(tmp_path)
    deep, gene = payload(package)
    output = tmp_path / 'gold_figures'
    result = figures.figs_single({strain: {'pkg': str(package), 'deep': deep, 'gene': gene}}, strain, str(output))
    assert result['identity_holds'] == []
    for semantic in ('perBGC_domain_heatmap', 'perBGC_cctt_resistance'):
        identity_file, = output.glob(f'*{semantic}_identity.csv')
        rows = list(csv.DictReader(identity_file.open()))
        assert len(rows) == 2
        assert {row['bgc_id'] for row in rows} == {'BGC001'}
        assert {row['full_contig'] for row in rows} == {'NODE_1_length_1000_cov_1.5', 'CP123456.2'}
        assert {row['strain'] for row in rows} == {strain}
        assert {row['antismash_region'] for row in rows} == {'region001'}
        image, = output.glob(f'*{semantic}.png')
        assert image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    data, = output.glob('*perBGC_domain_heatmap_data.csv')
    rows = list(csv.DictReader(data.open()))
    assert [int(float(row['PKS_KS'])) for row in rows] == [2, 0]
    assert [int(float(row['NRPS_A'])) for row in rows] == [0, 1]
    receipt = json.loads((output / 'gold_bgc_identity_receipt.json').read_text())
    assert receipt['status'] == 'BOUND_NATIVE_INVENTORY'
    assert all(hashlib.sha256((output / row['filename']).read_bytes()).hexdigest() == row['sha256'] for row in receipt['files'])
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(ValueError, match='GOLD_FIGURE_OUTPUT_NOT_EMPTY'):
        figures.figs_single({strain: {'pkg': str(package), 'deep': deep, 'gene': gene}}, strain, str(output))
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_generate_all_series_keeps_stage_receipt_bound_after_later_appends_and_detects_corruption(tmp_path):
    pytest.importorskip('matplotlib')
    from mamey import cohort_figures as figures
    package, strain, _ = package_fixture(tmp_path, collision=False)
    short_path = package / 'manifest_short.json'
    short = json.loads(short_path.read_text())
    short.update(raw_bgcs=2, corrected_bgcs=2, assembly_tier='UNKNOWN')
    _dump(short_path, short)
    output = tmp_path / 'all_series'

    # Exercise the production automatic-gold path: real F, G and D renderers,
    # the governed paired writer, source admission and generate's actual ordering.
    result = figures.generate(runs_dir=str(package.parent.parent), out=str(output),
                              strains=[strain], series='all')
    assert result['identity_holds'] == []
    assert list(output.glob('G*.png')) and list(output.glob('D*.png'))
    receipt_path = output / 'gold_bgc_identity_receipt.json'
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    assert receipt['status'] == 'BOUND_NATIVE_INVENTORY'
    bound_names = {row['filename'] for row in receipt['files']}
    snapshot_name = 'gold_single_stage_figure_receipts.jsonl'
    assert snapshot_name in bound_names
    assert 'figure_receipts.jsonl' not in bound_names
    snapshot = (output / snapshot_name).read_bytes()
    snapshot_rows = [json.loads(line) for line in snapshot.splitlines()]
    assert len(snapshot_rows) == 2
    assert {row['figure_id'].split('_', 1)[0] for row in snapshot_rows} == {'F01', 'F02'}
    shared = (output / 'figure_receipts.jsonl').read_bytes()
    assert shared.startswith(snapshot) and len(shared.splitlines()) > len(snapshot_rows)

    def mismatches():
        return {row['filename'] for row in receipt['files']
                if hashlib.sha256((output / row['filename']).read_bytes()).hexdigest() != row['sha256']}

    assert mismatches() == set()
    # A later governed figure must append to the shared ledger without changing
    # the original stage snapshot, its source binding or any recorded asset hash.
    fig, ax = figures.plt.subplots()
    ax.plot([0, 1], [0, 1])
    ax.set_title('Synthetic later figure')
    try:
        figures._save_pair(fig, str(output / 'LATER_synthetic.png'))
    finally:
        figures.plt.close(fig)
    later_shared = (output / 'figure_receipts.jsonl').read_bytes()
    assert later_shared.startswith(shared)
    assert len(later_shared.splitlines()) == len(shared.splitlines()) + 1
    assert (output / snapshot_name).read_bytes() == snapshot
    assert receipt_path.read_bytes() == receipt_bytes
    assert mismatches() == set()

    # Check every bound artifact, including the snapshot, both PNG/SVG pairs,
    # plotted values and typed identity sidecars. An unrelated append is allowed;
    # modifying any claimed stage byte is independently detected.
    assert len(bound_names) == 9
    assert sum(name.endswith('.png') for name in bound_names) == 2
    assert sum(name.endswith('.svg') for name in bound_names) == 2
    assert sum(name.endswith('_data.csv') for name in bound_names) == 2
    assert sum(name.endswith('_identity.csv') for name in bound_names) == 2
    for name in sorted(bound_names):
        path = output / name
        original = path.read_bytes()
        path.write_bytes(original + b'\nCORRUPTED_SYNTHETIC_CONTROL\n')
        assert mismatches() == {name}
        path.write_bytes(original)
    assert mismatches() == set()
    assert receipt_path.read_bytes() == receipt_bytes


def test_legacy_holds_locus_panels_while_independent_gene_panel_survives(tmp_path):
    pytest.importorskip('matplotlib')
    from mamey import cohort_figures as figures
    legacy = {'bgc_profile': [{'bgc_id': 'BGC001', 'PKS_KS': 9}],
              'active_sites': [{'domain_id': 'ctg1_1', 'active_site_calls': 'state: True'}]}
    output = tmp_path / 'legacy_figures'
    result = figures.figs_single({'SYNTHETIC_LEGACY': {'deep': legacy}}, 'SYNTHETIC_LEGACY', str(output))
    assert len(result['identity_holds']) == 2
    assert not list(output.glob('*perBGC*.png'))
    assert list(output.glob('*perGene_active_site_completeness.png'))
    receipt = json.loads((output / 'gold_bgc_identity_receipt.json').read_text())
    assert receipt['status'] == 'HOLD'
    assert 'BGC001' not in json.dumps(receipt['identity_holds'])


def test_two_aliases_claiming_same_physical_region_hold(tmp_path):
    package, strain, manifest = package_fixture(tmp_path, collision=False)
    manifest['bgcs'][1].update({name: manifest['bgcs'][0][name] for name in ('contig', 'node_id', 'antismash_region')})
    _dump(package / 'manifest.json', manifest)
    with pytest.raises(GoldBGCIdentityError, match='GOLD_IDENTITY_PHYSICAL_CONFLICT'):
        load_gold_identity_context(package, strain)


def test_distinct_full_contigs_sharing_normalized_node_do_not_join(tmp_path):
    package, strain, manifest = package_fixture(tmp_path)
    rows = list(csv.DictReader((package / f'{strain}_2_inventory.csv').open()))
    # Coverage suffixes differ after the decimal, while native Node_ID is unchanged.
    rows[0]['Contig'] = 'NODE_1_length_1000_cov_1.9'
    with (package / f'{strain}_2_inventory.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with pytest.raises(GoldBGCIdentityError, match='GOLD_IDENTITY_INVENTORY_MEMBERSHIP_CONFLICT'):
        load_gold_identity_context(package, strain)


def test_duplicate_required_inventory_header_holds(tmp_path):
    package, strain, _ = package_fixture(tmp_path)
    path = package / f'{strain}_2_inventory.csv'
    with path.open(newline='') as stream:
        rows = list(csv.reader(stream))
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        for row in rows:
            writer.writerow([*row, row[1]])
    with pytest.raises(GoldBGCIdentityError, match='GOLD_IDENTITY_INVENTORY_HEADERS_INVALID'):
        load_gold_identity_context(package, strain)


def test_source_change_during_staging_commits_no_stale_artwork(tmp_path, monkeypatch):
    pytest.importorskip('matplotlib')
    from mamey import cohort_figures as figures
    package, strain, manifest = package_fixture(tmp_path)
    deep, gene = payload(package)
    real_panels = figures._figs_single_panels
    def changed_after_render(*args):
        real_panels(*args)
        manifest['source_scans']['domain_architecture']['native_bgc_profiles_v1']['records'][0]['tta']['tta_codons'] = 5
        _dump(package / 'manifest.json', manifest)
    monkeypatch.setattr(figures, '_figs_single_panels', changed_after_render)
    output = tmp_path / 'stale_stage'
    result = figures.figs_single({strain: {'pkg': str(package), 'deep': deep, 'gene': gene}}, strain, str(output))
    assert len(result['identity_holds']) == 2
    assert result['files'] == []
    assert not list(output.glob('*.png'))
    assert not list(output.glob('*.svg'))
    assert not list(output.glob('.gold_stage_*'))


def test_generate_refuses_occupied_output_before_loading_sources(tmp_path, monkeypatch):
    pytest.importorskip('matplotlib')
    from mamey import cohort_figures as figures
    output = tmp_path / 'occupied'; output.mkdir()
    sentinel = output / 'old.png'; sentinel.write_bytes(b'old unchanged')
    def forbidden_load(*args, **kwargs):
        raise AssertionError('Sources opened after occupied output refusal')
    monkeypatch.setattr(figures, 'load', forbidden_load)
    with pytest.raises(ValueError, match='GOLD_FIGURE_OUTPUT_NOT_EMPTY'):
        figures.generate(runs_dir=str(tmp_path / 'not_opened'), out=str(output))
    assert list(output.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b'old unchanged'


def test_manifest_key_reordering_does_not_change_architecture_measurements(tmp_path):
    package, strain, manifest = package_fixture(tmp_path)
    deep, gene = payload(package)
    (package / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True))
    profiles, _ = admit_gold_profiles(package, strain, deep, gene)
    assert [p['PKS_KS'] for p in profiles] == [2, 0]
