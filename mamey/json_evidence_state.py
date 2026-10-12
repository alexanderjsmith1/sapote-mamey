"""Scoped extraction visibility. Source observation is never upstream validation."""
from pathlib import Path
import hashlib
import json

SCHEMA = 'json_evidence_state_v1'

def _natural(value):
    return type(value) is int and value >= 0

def project(evidence):
    ev = evidence if isinstance(evidence, dict) else {}
    requested = ev.get('json_mode_requested', 'UNKNOWN')
    effective = ev.get('json_mode_effective', ev.get('json_mode', 'UNKNOWN'))
    walks = ev.get('json_bounded_walks')
    valid = isinstance(walks, list) and bool(walks)
    required = ('records_closed', 'auxiliary_leaf_cap', 'auxiliary_leaves_kept',
                'riq_group_cap', 'riq_groups_kept', 'riq_observations_seen',
                'riq_observations_mapped', 'riq_observations_unassigned',
                'riq_observations_held', 'riq_mapped_maxima')
    if valid:
        valid = all(isinstance(w, dict) and w.get('schema') == 'bounded_json_walk_receipt_v1'
            and isinstance(w.get('source'), str) and w['source']
            and type(w.get('walk_complete')) is bool and type(w.get('auxiliary_truncated')) is bool
            and all(_natural(w.get(k)) for k in required)
            and w['auxiliary_leaves_kept'] <= w['auxiliary_leaf_cap']
            and w['riq_groups_kept'] <= w['riq_group_cap']
            and w['riq_mapped_maxima'] <= w['riq_groups_kept']
            and w['riq_observations_seen'] == sum(w[k] for k in
                ('riq_observations_mapped', 'riq_observations_unassigned', 'riq_observations_held'))
            for w in walks)
    if valid:
        sources = [w['source'] for w in walks]
        files = ev.get('json_files')
        valid = (isinstance(files, list) and all(isinstance(f, str) for f in files)
                 and len(sources) == len(set(sources)) and set(sources) == set(files))
    complete = valid and all(w['walk_complete'] for w in walks) and not ev.get('json_errors') and not ev.get('json_skipped')
    auxiliary = riq = 'UNKNOWN'
    if effective == 'off':
        auxiliary = riq = 'NOT_RUN'
    elif walks is not None and not valid:
        auxiliary = riq = 'RECEIPT_CONFLICT'
    elif valid:
        auxiliary = ('TRUNCATED' if any(w['auxiliary_truncated'] for w in walks)
                     else 'READ_COMPLETE_FOR_SELECTED_LEAVES' if complete else 'PARSE_HELD')
        riq = ('STORAGE_HELD' if any(w['riq_observations_held'] for w in walks)
               else 'PARSE_HELD' if not complete
               else 'IDENTITY_HELD' if any(w['riq_observations_unassigned'] for w in walks)
               else 'READ_COMPLETE_FOR_SELECTED_SCORES')
    elif ev.get('json_bounded_truncated') is True:
        auxiliary = 'TRUNCATED'
    elif ev.get('json_errors') or ev.get('json_skipped'):
        auxiliary = riq = 'PARSE_HELD'
    totals = {k: sum(w[k] for w in walks) if valid else 'UNKNOWN' for k in required}
    reconciliation = ev.get('riq_member_reconciliation')
    reconciliation_valid = False
    if reconciliation is not None:
        conflicts = ev.get('riq_source_conflicts')
        reconciliation_valid = (valid and isinstance(reconciliation, dict)
            and reconciliation.get('schema') == 'riq_member_reconciliation_v1'
            and all(_natural(reconciliation.get(k)) for k in ('grouped_regions', 'mapped_regions',
                'conflicting_regions', 'member_observations', 'equal_repeat_observations'))
            and reconciliation['grouped_regions'] == reconciliation['mapped_regions'] + reconciliation['conflicting_regions']
            and reconciliation['member_observations'] >= reconciliation['grouped_regions']
            and isinstance(conflicts, list) and len(conflicts) == reconciliation['conflicting_regions']
            and ev.get('riq_mapped_count') == reconciliation['mapped_regions']
            and reconciliation['member_observations'] >= (reconciliation['mapped_regions']
                + reconciliation['equal_repeat_observations'] + 2 * reconciliation['conflicting_regions']))
        if not reconciliation_valid:
            riq = 'RECEIPT_CONFLICT'
        elif valid and reconciliation['conflicting_regions']:
            riq = 'SOURCE_CONFLICT_HELD'
    channels = [
        {'channel': 'Main JSON auxiliary', 'state': auxiliary, 'count': totals['auxiliary_leaves_kept'],
         'interpretation': 'Retained auxiliary leaves only; this cap does not stop record closure or independently bounded RiQ aggregation.'},
        {'channel': 'RiQ', 'state': riq, 'count': reconciliation['mapped_regions'] if reconciliation_valid else totals['riq_mapped_maxima'],
         'interpretation': f"Selected score observations: seen={totals['riq_observations_seen']}, mapped={totals['riq_observations_mapped']}, unassigned={totals['riq_observations_unassigned']}, held={totals['riq_observations_held']}. Archive regional maxima reconciliation={reconciliation if reconciliation_valid else 'UNKNOWN'}. No similarity or biological validation implied."},
    ]
    receipt = ev.get('record_extraction')
    for name, key, handler in (('Record extras', 'record_extras_requested', None), ('TIGRFAM record parse', 'tigrfam_requested', '_tigrfam_from_rec')):
        state = 'UNKNOWN'; count = 'UNKNOWN'
        requested_channel = ev.get(key)
        if requested_channel is False:
            state = 'NOT_RUN'
        elif requested_channel is True and isinstance(receipt, dict) and receipt.get('schema') == 'record_extraction_receipt_v1':
            files = receipt.get('files'); handlers = receipt.get('handlers')
            chosen = ({handler} if handler else {'_nrps_pks_from_rec', '_active_site_from_rec',
                       '_product_class_from_rec', '_ripp_from_rec', '_rrefinder_from_rec'})
            valid_records = (isinstance(files, list) and isinstance(handlers, list) and chosen.issubset(handlers)
                and all(isinstance(f, dict) and _natural(f.get('records_seen')) and isinstance(f.get('error_counts'), dict)
                        and all(_natural(v) for v in f['error_counts'].values()) for f in files))
            if not valid_records:
                state = 'RECEIPT_CONFLICT'
            elif receipt.get('archive_errors') or not files:
                state = 'SOURCE_UNAVAILABLE'
            else:
                count = sum(f['records_seen'] for f in files)
                state = ('PARSE_HELD' if any(f.get('status') != 'READ_COMPLETE' for f in files)
                         else 'HANDLER_FAILED' if any(any(f['error_counts'].get(h, 0) for h in chosen) for f in files)
                         else 'READ_COMPLETE_FOR_SELECTED_RECORDS')
        channels.append({'channel': name, 'state': state, 'count': count,
            'interpretation': 'Record-reader/selected-handler execution only. Missing modules and upstream search completion are separate; empty output is not biological absence.'})
    result = {'schema': SCHEMA, 'requested_mode': requested, 'effective_mode': effective,
              'budget': ev.get('json_parse_budget', 'UNKNOWN'), 'channels': channels,
              'main_errors': ev.get('json_errors', 'UNKNOWN'),
              'main_skipped': ev.get('json_skipped', 'UNKNOWN'),
              'walk_receipts': walks if valid else [],
              'riq_member_reconciliation': reconciliation if reconciliation_valid else 'UNKNOWN',
              'riq_source_conflicts': ev.get('riq_source_conflicts', []) if reconciliation_valid else [],
              'record_extraction': receipt if isinstance(receipt, dict) else 'UNKNOWN',
              'scope': 'Selected extraction paths; not all-schema, upstream-search or biological completeness'}
    result['projection_sha256'] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return result

def read_package_state(package, strain):
    root = Path(package).resolve()
    path = root / (str(strain) + '_AntiSMASH_Evidence_Parse.json')
    try:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Evidence receipt outside package or symlinked')
        data = path.read_bytes()
        state = project(json.loads(data))
        state['source_receipt_sha256'] = hashlib.sha256(data).hexdigest()
        return state
    except (OSError, ValueError, TypeError) as exc:
        state = project({})
        state['read_error'] = type(exc).__name__
        return state

def describe(state):
    if not isinstance(state, dict) or state.get('schema') != SCHEMA:
        state = project({})
    summary = '; '.join(f"{r['channel']}={r['state']} (count={r['count']})" for r in state['channels'])
    limits = '; '.join(f"{w['source']}: auxiliary cap={w['auxiliary_leaf_cap']}, RiQ group cap={w['riq_group_cap']}, records closed={w['records_closed']}" for w in state['walk_receipts'])
    budget = state['budget']
    if isinstance(budget, dict): budget = f"{budget.get('state', 'UNKNOWN')} ({budget.get('seconds', 'UNKNOWN')}s)"
    riq = next(r['interpretation'] for r in state['channels'] if r['channel'] == 'RiQ')
    return (f"JSON evidence: requested={state['requested_mode']}, effective={state['effective_mode']}; {summary}. "
            f"{riq} Limits: {limits or 'UNKNOWN'}. CLI budget: {budget}. "
            f"Main parse errors: {state.get('main_errors', 'UNKNOWN')}; skipped: {state.get('main_skipped', 'UNKNOWN')}. "
            f"Receipt SHA-256: {state.get('source_receipt_sha256', 'not yet serialized')}. {state['scope']}.")
