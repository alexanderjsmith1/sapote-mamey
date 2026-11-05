"""Source-state and byte-binding checks on synthetic GECCO fixtures."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
helper = load('gecco_fixture', ROOT / 'tests/test_457_gecco_cohort_report.py')
from tools import gecco_cohort_report as gcr
helper.gcr = gcr

def invoke(tmp_path, options=()):
    helper.kit(tmp_path)
    args = ['--genomes', str(tmp_path / 'genomes.tsv'), '--out', str(tmp_path / 'out'), '--no-figures']
    rc = gcr.main(args + list(options))
    return rc, tmp_path / 'out'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_no_source_is_distinct_from_supplied_unmatched(tmp_path):
    rc, out = invoke(tmp_path)
    assert rc == 0
    r = json.loads((out / 'receipt.json').read_text())
    assert r['pfam_name_source'] == {'kind': 'none', 'path': None, 'sha256': None, 'state': 'not_supplied', 'entries': 0, 'ignored_hmm': None, 'release': None}
    assert 'Pfam name not supplied' in (out / 'gecco_calls.tsv').read_text()
    assert 'not in the supplied Pfam release' not in (out / 'gecco_calls.tsv').read_text()

def test_tsv_mapping_and_versions_are_bound(tmp_path):
    mapping = tmp_path / 'mapping.tsv'
    mapping.write_text('accession\tname\nPF00109.25\tknown\n')
    rc, out = invoke(tmp_path, ['--pfam-names', str(mapping)])
    assert rc == 0
    r = json.loads((out / 'receipt.json').read_text())
    assert r['pfam_name_source']['sha256'] == r['inputs_sha256'][str(mapping)] == digest(mapping)
    assert r['pfam_name_source']['state'] == 'mapping_loaded' and r['pfam_name_source']['release'] is None
    text = (out / 'gecco_calls.tsv').read_text()
    assert 'PF00109 (known) x2' in text and 'PF02801 (Pfam name not found in supplied mapping)' in text
    assert 'Pfam name not found in supplied mapping' in (out / 'gecco_calls_outside_regions_typed.md').read_text()

@pytest.mark.parametrize('content,state', [('NAME known\nACC PF00109.25\n//\n', 'mapping_loaded'), ('not a parseable profile\n', 'mapping_empty')])
def test_hmm_bytes_and_empty_mapping_are_receipted(tmp_path, content, state):
    hmm = tmp_path / 'profiles.hmm'
    hmm.write_text(content)
    rc, out = invoke(tmp_path, ['--pfam-hmm', str(hmm)])
    assert rc == 0
    r = json.loads((out / 'receipt.json').read_text())
    assert r['pfam_name_source']['kind'] == 'hmm' and r['pfam_name_source']['state'] == state
    assert r['pfam_name_source']['sha256'] == r['inputs_sha256'][str(hmm)] == digest(hmm)

def test_both_sources_preserve_tsv_precedence_and_disclose_ignored_hmm(tmp_path):
    mapping = tmp_path / 'mapping.tsv'
    hmm = tmp_path / 'ignored.hmm'
    mapping.write_text('accession\tname\nPF00109\tchosen\n')
    hmm.write_text('NAME ignored\nACC PF00109.1\n//\n')
    rc, out = invoke(tmp_path, ['--pfam-names', str(mapping), '--pfam-hmm', str(hmm)])
    assert rc == 0
    r = json.loads((out / 'receipt.json').read_text())
    assert r['pfam_name_source']['kind'] == 'tsv' and r['pfam_name_source']['ignored_hmm'] == str(hmm)
    assert str(hmm) not in r['inputs_sha256'] and 'PF00109 (chosen)' in (out / 'gecco_calls.tsv').read_text()

@pytest.mark.parametrize('mode', ['header_only_tsv', 'missing_hmm', 'malformed_name', 'malformed_acc'])
def test_bad_source_refuses_without_output(tmp_path, mode):
    name = tmp_path / ('bad.tsv' if mode == 'header_only_tsv' else 'missing.hmm')
    if mode == 'header_only_tsv':
        name.write_text('accession\tname\n')
    elif mode == 'malformed_name':
        name.write_text('NAME  \n')
    elif mode == 'malformed_acc':
        name.write_text('NAME valid\nACC  \n')
    rc, out = invoke(tmp_path, ['--pfam-names' if mode == 'header_only_tsv' else '--pfam-hmm', str(name)])
    assert rc == 2 and not out.exists()

def test_mutation_during_parse_refuses_before_output(tmp_path, monkeypatch):
    name = tmp_path / 'names_mutable.tsv'
    name.write_text('accession\tname\nPF00109\tinitial\n')
    original = gcr.pfam_names
    def changing(*args):
        result = original(*args)
        name.write_text('accession\tname\nPF00109\tchanged\n')
        return result
    monkeypatch.setattr(gcr, 'pfam_names', changing)
    rc, out = invoke(tmp_path, ['--pfam-names', str(name)])
    assert rc == 2 and not out.exists()

def test_same_hmm_path_new_bytes_changes_receipt_hash(tmp_path):
    helper.kit(tmp_path)
    hmm = tmp_path / 'profiles.hmm'
    base = ['--genomes', str(tmp_path / 'genomes.tsv'), '--pfam-hmm', str(hmm), '--no-figures']
    observed = []
    for i, name in enumerate(('one', 'two')):
        hmm.write_text('NAME ' + name + '\nACC PF00109.25\n//\n')
        out = tmp_path / ('out' + str(i))
        assert gcr.main(base + ['--out', str(out)]) == 0
        observed.append(json.loads((out / 'receipt.json').read_text())['pfam_name_source']['sha256'])
    assert observed[0] != observed[1]

def test_mutation_after_output_started_refuses_success_receipt(tmp_path, monkeypatch):
    name = tmp_path / 'names_late.tsv'
    name.write_text('accession\tname\nPF00109\tinitial\n')
    original = gcr.write_tsv
    state = {'changed': False}
    def changing(*args, **kwargs):
        result = original(*args, **kwargs)
        if not state['changed']:
            state['changed'] = True
            name.write_text('accession\tname\nPF00109\tchanged\n')
        return result
    monkeypatch.setattr(gcr, 'write_tsv', changing)
    rc, out = invoke(tmp_path, ['--pfam-names', str(name)])
    assert rc == 2 and out.exists() and not (out / 'receipt.json').exists()
