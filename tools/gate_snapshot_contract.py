#!/usr/bin/env python3
"""Experimental consumer checks for a structured gate snapshot.

A self-reported receipt cannot authenticate its producer or establish that a
process ran. A future audit must separately control and bind the invocation.
"""
import json
import re


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def _names(value, field, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(field + ' must be a list' + ('' if allow_empty else ' with entries'))
    if any(not isinstance(x, str) or not x or x != x.strip() for x in value):
        raise ValueError(field + ' contains invalid names')
    if len(value) != len(set(value)):
        raise ValueError(field + ' contains duplicate names')
    return set(value)


def compare(raw_json, *, tree_sha256, gate_sha256, declared_outgroups, expected_arguments):
    """Return HOLD for a consistent mechanical comparison, never approval."""
    try:
        for label, value in (('tree', tree_sha256), ('gate', gate_sha256)):
            if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
                raise ValueError(label + ' expected SHA-256 invalid')
        declared = _names(declared_outgroups, 'declared_outgroups')
        _names(expected_arguments, 'expected_arguments', allow_empty=True)
        record = json.loads(raw_json, object_pairs_hook=_unique)
        if not isinstance(record, dict) or record.get('schema') != 'tree-sanity-snapshot-v1' or record.get('status') != 'OBSERVED':
            raise ValueError('unsupported or unobserved result')
        if record.get('tree_sha256') != tree_sha256 or record.get('gate_sha256') != gate_sha256:
            raise ValueError('tree or gate binding mismatch')
        if record.get('effective_outgroup_arguments') != expected_arguments:
            raise ValueError('effective arguments differ from expected invocation')
        tips = _names(record.get('tip_names'), 'tip_names')
        recognized = _names(record.get('recognized_outgroup_tips'), 'recognized_outgroup_tips', allow_empty=True)
        if not declared < tips or not recognized <= tips:
            raise ValueError('outgroup names are not valid tree-tip subsets')
        if type(record.get('gate_pass')) is not bool or not isinstance(record.get('gate_report'), str):
            raise ValueError('gate result or report missing or invalid')
        if not record['gate_pass']:
            return {'status': 'FAIL', 'reason': 'gate reported failure'}
        missing = sorted(declared - recognized)
        extra = sorted(recognized - declared)
        return {'status': 'MISMATCH' if missing or extra else 'HOLD',
                'declared_not_recognized': missing, 'unexpected_recognized': extra,
                'scope': 'Mechanical consistency only; JSON is not proof of producer, invocation, or biological validity.'}
    except (ValueError, TypeError, UnicodeError) as exc:
        return {'status': 'ERROR', 'reason': str(exc)}
