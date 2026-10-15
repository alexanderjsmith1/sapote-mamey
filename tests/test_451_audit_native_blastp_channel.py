"""Actual native BLASTp command with mocked transport, then actual novelty consumer."""
from argparse import Namespace
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

SRC = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SRC), str(SRC / 'tools')]


def native():
    import mamey.blastp_online as baseline
    path = os.environ.get('W2_NATIVE_TOOL')
    if not path:
        return baseline
    spec = importlib.util.spec_from_file_location('mamey.native_overlay_trial', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def region(path):
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    # Synthetic full identity: XS-001 / NODE_1_length_90_cov_1 / region001 / BGC001.
    rec = SeqRecord(Seq('N' * 90), id='NODE_1_length_90_cov_1')
    rec.annotations['molecule_type'] = 'DNA'
    rec.features = [SeqFeature(FeatureLocation(0, 90, strand=1), type='CDS',
                               qualifiers={'locus_tag': ['syn1_1'], 'translation': ['M' * 30]})]
    SeqIO.write(rec, path, 'genbank')


@pytest.mark.parametrize('database', ['nr', 'swissprot', 'refseq_protein'])
def test_native_output_declares_actual_runtime_database_and_consumer_admission(tmp_path, monkeypatch, database):
    module = native()
    gbk, out = tmp_path / 'NODE_1_length_90_cov_1.region001.gbk', tmp_path / 'package/blastp_online'
    region(gbk)
    calls = []
    def mocked_batches(batches, **kwargs):
        calls.append({'batches': batches, 'database': kwargs['database']})
        return [module.OnlineResult(ok=True, rid='OFFLINE_SYNTHETIC', hits=[module.BlastpHit(
            locus_tag='syn1_1', aa_length=30, antismash_domains='',
            blastp_top_def='synthetic protein', blastp_organism='Synthetic species',
            pct_identity=82.0, query_coverage=100.0, bitscore=100.0, evalue=1e-9)])]
    monkeypatch.setattr(module, 'run_batches_online', mocked_batches)
    # A transport tripwire proves no live request can occur even if the mock is bypassed.
    monkeypatch.setattr(module, '_post', lambda *a, **k: pytest.fail('live transport forbidden'))
    args = Namespace(package=str(gbk), bgc=None, region=None, database=database,
                     batch_size=10, evalue='1e-5', outdir=str(out), submit=True,
                     confirm_public_upload=True)
    before = gbk.read_bytes()
    assert module.blastp_online_command(args) == 0
    assert len(calls) == 1 and calls[0]['database'] == database
    assert gbk.read_bytes() == before
    import csv
    path = out / 'region_online_blastp.csv'
    rows = list(csv.DictReader(path.open()))
    from mamey.genome_explore import _nr_observation_from_file
    observation = _nr_observation_from_file(path)
    print('consumer_observation', json.dumps(observation, sort_keys=True))
    assert rows[0].get('channel') == database
    assert rows[0].get('source_channel') == database
    if database == 'nr':
        assert observation['status'] == 'ADMITTED'
        assert observation['median_id'] == 82.0 and observation['n_genes'] == 1
    else:
        assert observation['status'] == 'INVALID'
        assert observation['median_id'] is None
