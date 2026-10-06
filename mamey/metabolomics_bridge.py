"""Deterministic genome-side class hypotheses and immutable reader exports.

No MS analysis, product prediction, or external-tool submission occurs here.
"""
from __future__ import annotations
import hashlib
import json
import math
import zipfile
from dataclasses import asdict
from pathlib import Path
from .companion_evidence import (CAPACITY_CEILING, archive_member, identity_text,
    publication, read_manifest, safe_name, validated_region, write_json, write_table)
from .postseal_output import resolve_source_archive, sha256_file

MAPPING_PATH = Path(__file__).parent / 'data/bgc_class_to_npclassifier.json'

def metabolomics_targets(strain, bgcs, source_scans=None, gecco=None):
    """One hypothesis entry per locked BGC; reference metrics require bound evidence."""
    mapping = json.loads(MAPPING_PATH.read_text())
    scans = source_scans or {}
    per_bgc = (scans.get('domain_architecture') or {}).get('per_bgc', {})
    references = (scans.get('mibig_per_gene') or {}).get('per_gene_mibig', {})
    targets = []
    for b in bgcs:
        counts = (per_bgc.get(b['bgc_id']) or {}).get('domain_counts', {})
        observed = sorted(k for k, v in counts.items() if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0)
        classes = sorted(cls for cls, domains in mapping['domain_rules'].items() if set(domains) & set(observed)) or ['unmapped']
        refs = [x for x in references.get(b['bgc_id'], []) if x.get('mibig_accession') == b.get('closest_mibig_accession') and x.get('source_file') == b.get('source_kcb_file')]
        metric = None
        by_gene = {}
        for ref in refs:
            value = ref.get('pct_identity')
            if ref.get('query_gene') and ref.get('source_file') and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 100:
                by_gene.setdefault(ref['query_gene'], []).append(value)
        if by_gene and sum(len(v) for v in by_gene.values()) == len(refs) and all(len(v) == 1 for v in by_gene.values()):
            from statistics import median
            metric = median(v[0] for v in by_gene.values())
        accession = b.get('closest_mibig_accession', 'UNRESOLVED')
        ref_bound = (str(b.get('source_kcb_file', '')).strip() not in ('', 'UNRESOLVED') and str(b.get('source_kcb_locator', '')).strip() not in ('', 'UNRESOLVED'))
        if not ref_bound:
            accession, metric = 'UNRESOLVED', None
        targets.append({'identity': identity_text(strain, b), 'strain': strain,
            'contig': b['contig'], 'region': b.get('antismash_region') or f"region{int(b['region_number']):03d}",
            'bgc_id': b['bgc_id'], 'biosynthetic_classes': classes,
            'npclassifier_pathways': sorted({mapping['mapping'][x] for x in classes}),
            'mapping_state': 'UNMAPPED_CORE_EVIDENCE' if classes == ['unmapped'] else 'DOMAIN_SUPPORTED_HYPOTHESIS',
            'core_domain_evidence': observed, 'antismash_products_observed': b.get('products', []),
            'best_mibig_accession': accession, 'median_pct_identity': metric,
            'close_match_74pct': None if metric is None else metric >= 74.0,
            'reference_metric_state': 'MEASURED_BOUND_REFERENCE' if metric is not None else 'NOT_MEASURED_OR_UNBOUND',
            'reference_source_file': b.get('source_kcb_file', 'UNRESOLVED'),
            'reference_source_locator': b.get('source_kcb_locator', 'UNRESOLVED'),
            'gecco_support': (gecco or {}).get(identity_text(strain, b), {'state': 'NOT_RUN'}),
            'mapping_policy_sha256': sha256_file(MAPPING_PATH), 'claim_ceiling': CAPACITY_CEILING})
    return targets

def targets_for_run(run):
    return metabolomics_targets(run.context.strain_id, [asdict(x) for x in run.bgcs], asdict(run.source_scans) if run.source_scans else {})

def export_metabolomics(package, out=None, source_zip=None, gecco_dir=None):
    manifest = read_manifest(package)
    archive_path, binding = resolve_source_archive(package, source_zip)
    support = None
    if gecco_dir is not None:
        from .gecco_crosscheck import bound_support
        support = bound_support(package, gecco_dir)
    targets = metabolomics_targets(manifest['strain_id'], manifest['bgcs'], manifest.get('source_scans'), support)
    with publication(package, 'export-metabolomics', out) as (stage, package_receipt):
        region_dir = stage / 'nplinker' / 'antismash'
        region_dir.mkdir(parents=True)
        pointers = []
        with zipfile.ZipFile(archive_path) as archive:
            for bgc in manifest['bgcs']:
                member = bgc.get('source_gbk')
                if not member or not __import__('re').search(r'\.region\d+\.gbk$', member):
                    raise ValueError('METABOLOMICS_REGION_SOURCE_UNBOUND')
                payload = archive_member(archive, member)
                declaration = validated_region(payload, manifest['strain_id'], bgc, member)
                filename = safe_name(manifest['strain_id']) + '_' + safe_name(bgc['bgc_id']) + '.gbk'
                (region_dir / filename).write_bytes(payload)
                pointers.append({'identity': identity_text(manifest['strain_id'], bgc), 'source_member': member,
                    'source_sha256': hashlib.sha256(payload).hexdigest(), 'declaration': declaration, 'staged_file': 'antismash/' + filename})
        write_table(stage / (manifest['strain_id'] + '_metabolomics_targets.tsv'), targets, list(targets[0]) if targets else ['identity', 'claim_ceiling'])
        write_json(stage / 'metabolomics_targets.json', targets)
        write_json(stage / 'nplinker' / 'source_pointers.json', pointers)
        write_json(stage / 'nplinker' / 'strain_mappings.json', {'schema': 'sapote.operator-sample-mapping-template.v1', 'strain_mappings': [{'strain_id': manifest['strain_id'], 'ms_sample_names': []}], 'state': 'OPERATOR_COMPLETION_REQUIRED', 'note': 'Adapt this source staging template to the installed NPLinker version; no MS association has been asserted.'})
        write_json(stage / 'podp_record_template.json', {'schema': 'sapote.genome-side-podp-template.v1', 'strain_id': manifest['strain_id'], 'assembly_accession': manifest.get('assembly_accession'), 'antismash_version': manifest.get('antismash_version'), 'bgcs': [x['identity'] for x in targets], 'ms_metadata': None, 'state': 'OPERATOR_COMPLETION_REQUIRED', 'note': 'Preparation template, not a validated PoDP submission.'})
        (stage / 'README.md').write_text('# Genome-side metabolomics bridge\n\n' + CAPACITY_CEILING + '.\n\nNPLinker can combine region/GCF and MS inputs; GNPS/MASST, SIRIUS/CANOPUS, PRISM and PoDP require their own formats, sample metadata and review. This export stages exact region GBKs and a private mapping template; it does not run them, validate their submission schemas, or establish production, activity, novelty or physical linkage. Class pathways are broad domain-supported hypotheses; unmapped is explicit. Fill MS sample names yourself.\n')
        if sha256_file(archive_path) != binding['sha256']:
            raise ValueError('METABOLOMICS_ARCHIVE_CHANGED')
        write_json(stage / 'receipt.json', {'schema': 'sapote.metabolomics-export.v1', 'package_binding': package_receipt,
            'source_archive': binding, 'gecco_directory': str(Path(gecco_dir).resolve()) if gecco_dir else None,
            'region_declaration_policy': 'Single terminated GenBank record; exact normalized contig, declared original bounds, region number/local span and bounded unique CDS loci; admitted member bytes unchanged.', 'mapping_sha256': sha256_file(MAPPING_PATH), 'region_count': len(pointers), 'claim_ceiling': CAPACITY_CEILING})
    return targets
