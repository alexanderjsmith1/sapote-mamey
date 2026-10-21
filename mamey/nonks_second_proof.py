"""Second-proof policies for split-cluster candidates, routed by cluster class.

The ketosynthase-clade proof applies to polyketide clusters only. For a pair with a positively observed non-KS core
and no KS on either side, `class_routed_v1` takes biosynthetic logic as the second proof: the two pieces together
complete their class core, which neither completes alone. A single-copy marker complete on both pieces (CONFLICT) or a
far-apart complete relative (APART_CLOSE) vetoes; the intact-relative position is recorded as a check on homology.
`nonks_position_v1` keeps the earlier rule (position CONSISTENT corroborates). KCB complementarity remains supporting
only.

Policies: `class_routed_v1` (default) routes by class and computes the position reading from the antiSMASH archive
when no scorecard is supplied; `nonks_position_v1` reads a supplied scorecard only; `ks_clade_v2` is the KS-clade
proof alone (the earlier default, kept for reproduction).
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from .companion_evidence import contig_key, identity_text, publication, read_manifest, table, write_json
from .postseal_output import sha256_file
from .rescue_two_proof import two_proof_join, write_4d_csv, _logic_proof, _short

KS_POLICY = 'ks_clade_v2'
POSITION_POLICY = 'nonks_position_v1'
CLASS_ROUTED_POLICY = 'class_routed_v1'
DEFAULT_POLICY = CLASS_ROUTED_POLICY
POLICIES = (CLASS_ROUTED_POLICY, KS_POLICY, POSITION_POLICY)
POSITION_POLICIES = (POSITION_POLICY, CLASS_ROUTED_POLICY)
# Rescue labels need both members bound to the current manifest; otherwise the row is held.
RESCUE_VERDICTS = ('TWO_PROOF_RESCUE', 'RGGMCI_ONLY')
UNBOUND_HOLD = 'UNBOUND_MEMBER_HOLD'

def _count(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or (isinstance(value, float) and not math.isfinite(value)) or value < 0 or int(value) != value:
        raise ValueError('NONKS_DOMAIN_COUNT_INVALID')
    return int(value)


def class_state(bgc, domains):
    if domains is None: domains = {}
    if not isinstance(domains, dict) or not isinstance(domains.get('domain_counts', {}), dict):
        raise ValueError('NONKS_DOMAIN_SCHEMA_INVALID')
    counts = {name: _count(value) for name, value in domains.get('domain_counts', {}).items()}
    ks = _count(bgc.get('ks_domain_count', 0))
    products = bgc.get('products', [])
    if not isinstance(products, list) or any(not isinstance(value, str) for value in products):
        raise ValueError('NONKS_PRODUCT_SCHEMA_INVALID')
    entries = domains.get('domains', [])
    if not isinstance(entries, list): raise ValueError('NONKS_DOMAIN_SCHEMA_INVALID')
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('contig'), str) or contig_key(entry['contig']) != contig_key(bgc['contig']):
            raise ValueError('NONKS_DOMAIN_LOCUS_UNBOUND')
        start, end = entry.get('start'), entry.get('end')
        if type(start) is not int or type(end) is not int or not 1 <= start <= end or end <= bgc['start'] or start - 1 >= bgc['end']:
            raise ValueError('NONKS_DOMAIN_COORDINATE_INVALID')
        length = bgc.get('contig_length')
        if length is not None and (type(length) is not int or length < 1 or end > length):
            raise ValueError('NONKS_DOMAIN_COORDINATE_INVALID')
        if not isinstance(entry.get('domain'), str) or not entry['domain'].strip():
            raise ValueError('NONKS_DOMAIN_IDENTITY_INVALID')
        classes = entry.get('classes', [])
        if not isinstance(classes, list) or any(not isinstance(value, str) or not value for value in classes):
            raise ValueError('NONKS_DOMAIN_CLASS_INVALID')
    products = ' '.join(products).lower()
    if counts.get('PKS_KS', 0) > 0 or ks > 0 or any(x in products for x in ('pks', 'polyketide', 'transat')):
        return 'KS_PRESENT'
    positive = {'NRPS_A', 'RiPP_precursor', 'YcaO_TOMM', 'Terpene_synthase', 'Terpene_cyclase', 'Terpene_synth_C', 'StaD', 'RebD', 'Trp_dimerase'}
    if any(counts.get(k, 0) > 0 for k in positive):
        return 'NON_KS_CLASS_OBSERVED'
    return 'CLASS_EVIDENCE_UNRESOLVED'


def position_index(manifest, scorecards):
    identities = {b['bgc_id']: identity_text(manifest['strain_id'], b) for b in manifest['bgcs']}
    idx = {}
    for row in scorecards or []:
        if row.get('strain') != manifest['strain_id']:
            continue
        a, b = row.get('identity_a'), row.get('identity_b')
        if a not in identities.values() or b not in identities.values() or a == b:
            raise ValueError('NONKS_SCORECARD_LOCUS_BINDING_MISMATCH')
        key = frozenset((a.split(' / ')[-1], b.split(' / ')[-1]))
        if key in idx:
            raise ValueError('NONKS_SCORECARD_DUPLICATE_PAIR')
        pair = row.get('pair', '')
        if pair and frozenset(pair.split('+')) != key:
            raise ValueError('NONKS_SCORECARD_PAIR_ID_MISMATCH')
        idx[key] = row
    return idx

def apply_policy(rows, manifest, scorecards=(), policy=DEFAULT_POLICY):
    if policy not in POLICIES:
        raise ValueError('NONKS_POLICY_UNSUPPORTED')
    bgcs = {b['bgc_id']: b for b in manifest['bgcs']}
    domains = ((manifest.get('source_scans') or {}).get('domain_architecture') or {}).get('per_bgc', {})
    scores = position_index(manifest, scorecards)
    result = []
    for original in rows:
        row = dict(original)
        a, b = row.get('bgc_a'), row.get('bgc_b')
        if a in bgcs and b in bgcs:
            for side, bid in (('a', a), ('b', b)):
                observed = row.get('contig_' + side)
                if observed not in (bgcs[bid]['contig'], _short(bgcs[bid]['contig'])):
                    raise ValueError('NONKS_RGGMCI_LOCUS_BINDING_MISMATCH')
        row['rule_policy'] = policy
        row['second_proof_channel'] = 'KS_CLADE' if row.get('ks_clade_id') else 'NONE'
        row['independent_proof_state'] = 'PRESENT' if row.get('ks_clade_id') else 'NOT_OBSERVED'
        row['position_verdict'] = 'NOT_READ'
        row['position_reference'] = ''
        row['kcb_role'] = 'SUPPORTING_ONLY; never independent second proof'
        row['identity_a'] = identity_text(manifest['strain_id'], bgcs[a]) if a in bgcs else ''
        row['identity_b'] = identity_text(manifest['strain_id'], bgcs[b]) if b in bgcs else ''
        if row.get('verdict') in RESCUE_VERDICTS and (a not in bgcs or b not in bgcs):
            for side, bid in (('a', a), ('b', b)):
                if bid not in bgcs:
                    row['identity_' + side] = (f"IDENTITY_HOLD: bgc_{side} {bid!r} absent from the manifest; "
                                               f"held from {row['verdict']}")
            row['verdict'] = UNBOUND_HOLD
        if policy in POSITION_POLICIES and a in bgcs and b in bgcs:
            states = [class_state(bgcs[x], domains.get(x)) for x in (a, b)]
            # One side can hold accessory genes; positive non-KS core on either
            # side is sufficient, but any observed KS keeps the KS protocol.
            eligible = 'NON_KS_CLASS_OBSERVED' in states and 'KS_PRESENT' not in states and bgcs[a]['contig'] != bgcs[b]['contig']
            score = scores.get(frozenset((a, b)), {})
            pos = score.get('layers_verdict', 'NOT_READ')
            row['position_verdict'] = pos
            row['position_reference'] = score.get('relative', '')
            core = score.get('completes_core', '')
            row['core_completion'] = core if isinstance(core, str) else ''
            if eligible and policy == CLASS_ROUTED_POLICY:
                # Non-KS proof 2 = biosynthetic logic: together the pieces complete their class core, which neither
                # completes alone. A duplicated single-copy marker (CONFLICT) or a far-apart complete relative
                # (APART_CLOSE) still vetoes; the position reading is recorded as a check on homology.
                row['second_proof_channel'] = 'CORE_COMPLETION'
                if pos in ('APART_CLOSE', 'CONFLICT'):
                    row['verdict'] = 'POSITION_VETO'
                    row['independent_proof_state'] = 'CONTRADICTED'
                elif row['core_completion'].strip():
                    row['independent_proof_state'] = 'PRESENT'
                    if _logic_proof(row) and row.get('rggmci_confidence') == 'HIGH_RG_GMCI_RESCUE':
                        row['verdict'] = 'TWO_PROOF_RESCUE'
                else:
                    row['independent_proof_state'] = 'NOT_READ_OR_UNRESOLVED'
            elif eligible:
                row['second_proof_channel'] = 'INTACT_RELATIVE_POSITION'
                if pos in ('APART_CLOSE', 'CONFLICT'):
                    row['verdict'] = 'POSITION_VETO'
                    row['independent_proof_state'] = 'CONTRADICTED'
                elif pos == 'CONSISTENT' and isinstance(score.get('relative'), str) and score['relative'].strip():
                    row['independent_proof_state'] = 'PRESENT'
                    # Card requires HIGH rather than broad existing MODERATE;
                    # retain the complementarity gate from the governing logic.
                    if _logic_proof(row) and row.get('rggmci_confidence') == 'HIGH_RG_GMCI_RESCUE':
                        row['verdict'] = 'TWO_PROOF_RESCUE'
                else:
                    row['independent_proof_state'] = 'NOT_READ_OR_UNRESOLVED'
            elif 'KS_PRESENT' not in states:
                row['independent_proof_state'] = 'CLASS_EVIDENCE_UNRESOLVED'
        result.append(row)
    return result

def archive_scorecards(rows, manifest, input_zip):
    """Position/marker readings computed from the antiSMASH archive for the candidate pairs in `rows`."""
    from .split_evidence_layers import scorecards_from_archive
    pairs = [(r.get('bgc_a'), r.get('bgc_b')) for r in rows if r.get('bgc_a') and r.get('bgc_b')]
    return scorecards_from_archive(input_zip, manifest['strain_id'], manifest['bgcs'], pairs)


def recompute(package, policy=DEFAULT_POLICY, scorecard=None, out=None, input_zip=None):
    manifest = read_manifest(package)
    candidates = list(Path(package).glob('*_4A_RGGMCI_ranked_pairs.csv'))
    if len(candidates) != 1:
        raise ValueError('NONKS_RGGMCI_INPUT_AMBIGUOUS')
    scores = table(scorecard, ['strain', 'identity_a', 'identity_b', 'layers_verdict', 'relative']) if scorecard else []
    scans = manifest.get('source_scans') or {}
    rows, _, _ = two_proof_join(candidates[0], scans.get('pks_ks_scan') or {})
    position_source = 'SCORECARD' if scorecard else 'NOT_READ'
    if policy == CLASS_ROUTED_POLICY and not scorecard and input_zip:
        scores = archive_scorecards(rows, manifest, input_zip)
        position_source = 'ARCHIVE'
    rows = apply_policy(rows, manifest, scores, policy)
    with publication(package, 'two-proof-rescue', out) as (stage, binding):
        write_4d_csv(rows, stage / (manifest['strain_id'] + '_4D_two_proof_rescue.csv'), manifest['strain_id'])
        write_json(stage / 'receipt.json', {'schema': 'sapote.two-proof-policy.v1', 'rule_policy': policy,
            'package_binding': binding, 'rggmci_sha256': sha256_file(candidates[0]),
            'scorecard_path': str(Path(scorecard).resolve()) if scorecard else None,
            'scorecard_sha256': sha256_file(scorecard) if scorecard else None,
            'position_source': position_source,
            'input_zip_sha256': sha256_file(input_zip) if (input_zip and position_source == 'ARCHIVE') else None,
            'ks_scan_state': 'AVAILABLE' if scans.get('pks_ks_scan') else 'NOT_PROVIDED',
            'claim_ceiling': 'class-level linkage candidate for adjudication; no merge, production or activity claim',
            'default_unchanged': policy == DEFAULT_POLICY})
    return rows
