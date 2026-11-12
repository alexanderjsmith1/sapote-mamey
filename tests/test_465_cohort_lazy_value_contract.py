"""Deferred cohort values retain from-import and explicit-binding behavior."""
import importlib
import pytest

CASES = [
    ('mamey.assembly_line', 'EXCLUDE_STRAINS'),
    ('mamey.compound_family_report', 'EXCLUDE_STRAINS'),
    ('mamey.p450_tailoring', 'EXCLUDE_STRAINS'),
    ('mamey.cohort_figures_extended', 'TIER'),
    ('mamey.interactive_figures.widget_data', 'ATTINE_ANT_STRAINS'),
    ('mamey.interactive_figures.widget_data', 'GOVERNANCE_OVERRIDES'),
    ('tools.build_cohort_precompute', 'CO_ASSEMBLY'),
    ('tools.blastp_coverage_wave', 'GOVERNED_EXCLUDE'),
    ('tools.materialize_strain_data', 'SKIP_STRAINS'),
]

@pytest.mark.parametrize('module,name', CASES)
def test_deferred_value_tracks_source_and_preserves_explicit_binding(module, name, monkeypatch):
    mod = importlib.import_module(module)
    state = {'id': 'FIXTURE-A'}
    monkeypatch.delitem(mod.__dict__, name, raising=False)
    for reader in ('raw_analysis_excluded', 'hard_excluded', '_hard_excluded'):
        if reader in mod.__dict__:
            monkeypatch.setattr(mod, reader, lambda: {state['id']})
    if '_raw_assembly_void' in mod.__dict__:
        monkeypatch.setattr(mod, '_raw_assembly_void', lambda: {'FIXTURE-VOID'})
    if '_official_data_json' in mod.__dict__:
        monkeypatch.setattr(mod, '_official_data_json', lambda filename, default: (
            {state['id']: 'fixture-tier'} if filename == 'cohort_assembly_tiers.json'
            else {'strains': [state['id']]}))
    # build_cohort_precompute imports its JSON reader within __getattr__.
    if name == 'CO_ASSEMBLY':
        from mamey import exclusions
        monkeypatch.setattr(exclusions, 'official_data_json', lambda filename, default: {'strains': [state['id']]})
    first = mod._bound(name)
    assert state['id'] in first
    namespace = {}
    exec(f'from {module} import {name}', namespace)
    assert namespace[name] == first
    state['id'] = 'FIXTURE-B'
    assert state['id'] in mod._bound(name)
    assert 'FIXTURE-A' not in mod._bound(name)
    # A from-import is a Python snapshot, while a module override remains authoritative.
    assert 'FIXTURE-A' in namespace[name]
    override = {'EXPLICIT-FIXTURE'}
    monkeypatch.setitem(mod.__dict__, name, override)
    assert mod._bound(name) is override
    with pytest.raises(AttributeError):
        mod.__getattr__('UNKNOWN_FIXTURE_ATTRIBUTE')

@pytest.mark.parametrize('failure', ['wrong_json_shape', 'reader_error'])
def test_coassembly_keeps_existing_empty_fallback(failure, monkeypatch):
    from tools import build_cohort_precompute as mod
    from mamey import exclusions
    def read(filename, default):
        if failure == 'reader_error':
            raise RuntimeError('fixture reader failure')
        return []
    monkeypatch.setattr(exclusions, 'official_data_json', read)
    monkeypatch.delitem(mod.__dict__, 'CO_ASSEMBLY', raising=False)
    assert mod._bound('CO_ASSEMBLY') == set()
