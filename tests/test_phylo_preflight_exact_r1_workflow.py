"""R1 verifies only exact versioned accessions against hash-bound local records."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('preflight_exact_r1', ROOT / 'tools/phylo_preflight.py')
pf = importlib.util.module_from_spec(spec); spec.loader.exec_module(pf)


def fixture(tmp_path, claimed='Genus species', accession='GCF_000000001.1', records=None):
    registry = tmp_path/'registry.tsv'
    registry.write_text('assembly_accession\toutgroup_species_strain\n'+accession+'\t'+claimed+'\n')
    entries = []
    for i, rec in enumerate(records or []):
        path = tmp_path/f'record{i}.json'; path.write_text(json.dumps(rec))
        entries.append({'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = tmp_path/'evidence.json'; manifest.write_text(json.dumps({'records':entries}))
    return registry, manifest


def record(acc='GCF_000000001.1', name='Genus species'):
    return {'assembly_accession':acc,'organism_name':name}


def test_exact_identity_and_binomial_pass_without_writing(tmp_path):
    reg, evidence = fixture(tmp_path, records=[record()])
    before = {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    report = pf.Report()
    result = pf.check_registry_accessions(report, reg, evidence)
    assert result[0]['verdict'] == 'VERIFIED_BINOMIAL' and report.items[0]['status'] == 'PASS'
    assert before == {p.name:p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('different', ['GCA_000000001.1','GCF_000000001.2','GCA_000000999.1'])
def test_neither_numeric_body_nor_version_or_unrecorded_pair_verifies(tmp_path, different):
    reg, evidence = fixture(tmp_path, records=[record(different)])
    result = pf.verify_registry_accessions(reg,evidence)
    assert result[0]['verdict'] == 'UNVERIFIED'


@pytest.mark.parametrize('bad', ['', 'GCF_000000001', 'prefixGCF_000000001.1', 'GCF_000000001.0', 'GCF_000000001.1 trailing'])
def test_incomplete_or_embedded_accession_is_not_an_identity(tmp_path, bad):
    reg, evidence = fixture(tmp_path,accession=bad,records=[record()])
    assert pf.verify_registry_accessions(reg,evidence)[0]['verdict'] == 'UNVERIFIED'


@pytest.mark.parametrize('name', ['Another species','Genus different'])
def test_label_mismatch_fails(tmp_path, name):
    reg, evidence = fixture(tmp_path,records=[record(name=name)])
    report=pf.Report(); pf.check_registry_accessions(report,reg,evidence)
    assert report.items[0]['status']=='FAIL'


@pytest.mark.parametrize('claimed', ['', 'Genus', 'Genus sp.', 'G. species'])
def test_missing_claimed_binomial_never_passes(tmp_path,claimed):
    reg,evidence=fixture(tmp_path,claimed=claimed,records=[record()])
    assert pf.verify_registry_accessions(reg,evidence)[0]['verdict']=='UNVERIFIED'


def test_conflicting_records_fail(tmp_path):
    reg,evidence=fixture(tmp_path,records=[record(),record(name='Another species')])
    report=pf.Report(); rows=pf.check_registry_accessions(report,reg,evidence)
    assert rows[0]['verdict']=='CONFLICT' and report.fails()


def test_hash_drift_is_unverified(tmp_path):
    reg,evidence=fixture(tmp_path,records=[record()])
    (tmp_path/'record0.json').write_text(json.dumps(record(name='Another species')))
    report=pf.Report(); pf.check_registry_accessions(report,reg,evidence)
    assert report.items[0]['status']=='WARN' and 'hash mismatch' in report.items[0]['detail']


def test_missing_evidence_and_empty_registry_are_not_passes(tmp_path):
    reg,evidence=fixture(tmp_path)
    report=pf.Report(); pf.check_registry_accessions(report,reg,None)
    assert report.items[0]['status']=='WARN'
    reg.write_text('assembly_accession\toutgroup_species_strain\n')
    report=pf.Report(); pf.check_registry_accessions(report,reg,evidence)
    assert report.items[0]['status']=='WARN'


def test_malformed_registry_retains_unverified_check(tmp_path):
    reg,evidence=fixture(tmp_path,records=[record()])
    reg.write_text('wrong_header\nvalue\n')
    report=pf.Report(); pf.check_registry_accessions(report,reg,evidence)
    assert report.items[0]['check']=='R1' and report.items[0]['status']=='WARN'
