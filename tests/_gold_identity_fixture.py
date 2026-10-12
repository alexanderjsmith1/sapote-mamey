"""Explicit synthetic package context for positive Gold presentation fixtures.

Unique-alias convenience fixtures only. Collision known-answer tests use actual
native source functions and independently specified expectations instead.
"""
import copy
import csv
import json
from pathlib import Path

from mamey.crosswalk import infer_node_id
from mamey.deep_data import PROFILE_DOMAINS, extract_profiles
from mamey.gold_bgc_identity import CHANNELS, load_gold_identity_context


def bind_synthetic_gold_package(package, strain, *, manifest=None, deep=None, gene=None):
    package = Path(package)
    package.mkdir(parents=True, exist_ok=True)
    read = lambda name, default: json.loads((package / name).read_text()) if (package / name).exists() else default
    deep = copy.deepcopy(deep if deep is not None else read('deep_data.json', {'bgc_profile': [], 'active_sites': []}))
    gene = copy.deepcopy(gene if gene is not None else read('gene_data.json', {'domain_arch': []}))
    manifest = copy.deepcopy(manifest if manifest is not None else read('manifest.json', {}))
    profiles = deep.get('bgc_profile', [])
    if 'bgcs' not in manifest:
        manifest['bgcs'] = [
            {'bgc_id': profile['bgc_id'], 'contig': f'ctg{index}_fixture_segment',
             'node_id': f'ctg{index}', 'antismash_region': f'region{index:03d}',
             'region_number': index, 'products': [], 'release': 'PRIVATE'}
            for index, profile in enumerate(profiles, 1)]
    aliases = [bgc['bgc_id'] for bgc in manifest['bgcs']]
    if len(set(aliases)) != len(aliases):
        raise AssertionError('Convenience helper refuses alias collisions; use real native producer fixture')
    manifest.setdefault('strain_id', strain)
    manifest.setdefault('release', 'PRIVATE')
    manifest.setdefault('taxonomy', 'Syntheticus sp.')
    manifest.setdefault('source', 'synthetic fixture')
    for bgc in manifest['bgcs']:
        bgc['node_id'] = infer_node_id(bgc['contig'], '')
    scans = manifest.setdefault('source_scans', {})
    architecture = scans.setdefault('domain_architecture', {'status': 'SOURCE_DERIVED_STRUCTURED_DOMAINS', 'per_bgc': {}})
    records = []
    by_alias = {profile['bgc_id']: profile for profile in profiles}
    for index, bgc in enumerate(manifest['bgcs'], 1):
        profile = by_alias.get(bgc['bgc_id'], {})
        measured = copy.deepcopy(architecture['per_bgc'].get(bgc['bgc_id'], {
            'domain_counts': {name: profile.get(name, 0) for name in PROFILE_DOMAINS}, 'domains': []}))
        measured.setdefault('module_count', 0)
        measured.setdefault('core_summary', [])
        measured['domain_hit_count'] = len(measured['domains'])
        architecture['per_bgc'][bgc['bgc_id']] = measured
        records.append({'source_record_index': index,
            'identity': {name: bgc[name] for name in ('contig', 'node_id', 'antismash_region', 'bgc_id')},
            'architecture': copy.deepcopy(measured),
            'tta': {'tta_codons': profile.get('tta_codons', 0), 'tta_cds': profile.get('tta_cds', 0)},
            'resistance': {'tier': profile.get('resistance_tier') or 'NULL_NO_SOURCE_DERIVED_RESISTANCE'},
            'umed': {'verdict': profile.get('umed_verdict') or 'NOT_MATURATION_GATED'},
            'cctt_triggers': (profile.get('cctt_triggers') or '').split(',') if profile.get('cctt_triggers') else [],
            'coverage': {channel: 'MEASURED' for channel in CHANNELS}})
    architecture['native_bgc_profiles_v1'] = {'schema_version': 'native_bgc_profiles_v1', 'records': records}
    (package / 'manifest.json').write_text(json.dumps(manifest))
    inventory = list(package.glob('*_2_inventory.csv'))
    if not inventory:
        inventory_path = package / f'{strain}_2_inventory.csv'
        with inventory_path.open('w', newline='') as stream:
            fields = ['Strain', 'Contig', 'Node_ID', 'antiSMASH_Region', 'BGC_ID']
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            for bgc in manifest['bgcs']:
                writer.writerow(dict(zip(fields, [strain, bgc['contig'], bgc['node_id'], bgc['antismash_region'], bgc['bgc_id']])))
    (package / f'{strain}_Project_Memory_Snapshot.json').write_text(json.dumps({'alias_of': 'manifest.json'}))
    context = load_gold_identity_context(package, strain, manifest)
    native_profiles, architectures, hits = extract_profiles(strain, manifest, identity_context=context)
    deep.update(bgc_profile=native_profiles, domain_hits=hits, bgc_identity_contract=context['receipt'])
    gene.update(domain_arch=architectures, bgc_identity_contract=context['receipt'])
    (package / 'deep_data.json').write_text(json.dumps(deep))
    (package / 'gene_data.json').write_text(json.dumps(gene))
    return {'pkg': str(package), 'deep': deep, 'gene': gene, 'manifest': manifest, 'context': context}
