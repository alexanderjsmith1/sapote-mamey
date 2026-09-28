"""Small adversarial metadata/hit controls; no private isolate material.

Protein strings are taken from the public BGC0000055 reference fixture. Arrangements
and hit values are perturbations for code tests, never biological truth observations.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey import rescue_groups


def load(name):
    spec = importlib.util.spec_from_file_location('task40_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gdr = load('gap_directed_rescue')
gsm = load('gene_synteny_map')
hg = load('handoff_gate')


def reference():
    from Bio import SeqIO
    rec = SeqIO.read(ROOT / 'tests/fixtures/task40_F007_public.gbk', 'genbank')
    aa = next(f.qualifiers['translation'][0] for f in rec.features if f.type == 'CDS' and f.qualifiers.get('translation'))
    return [dict(id=f'g{i:03}', i=i, name=f'public_reference_gene_{i}', product='enzyme',
                 kind='biosynthetic-additional', ks=0, aa=aa) for i in range(1, 4)]


def genome():
    aa = reference()[0]['aa']
    return {'p1': dict(contig='AVCN01000003.1', shown='DEFINITION: Saccharopolyspora erythraea D scaffold00003, whole genome shotgun sequence / AVCN01000003.1', start=0,
                       end=900, tag='public_protein_1', aa=aa, contig_len=8000)}, [], dict(
                       contig='AVCN01000004.1', start=0, end=1000, edge='True')



def packet(tmp_path):
    q = tmp_path / 'patches'
    card = q / 'public_control'
    card.mkdir(parents=True)
    (card / 'CARD.md').write_text('# Public control\n')
    (card / 'fix.diff').write_text('--- a/x.txt\n+++ b/x.txt\n@@ -1 +1 @@\n-a\n+b\n')
    import hashlib
    digest = hashlib.sha256((card / 'fix.diff').read_bytes()).hexdigest()
    (card / 'HASHES.txt').write_text(digest + '  fix.diff\n')
    (q / '00_QUEUE_1.md').write_text('`fix.diff` sha256 `' + digest[:8] + '`\n')
    s = tmp_path / 'compose.sh'
    s.write_text('Q="unused"\nstep "one" "$Q/public_control/fix.diff"\n')
    return q, s


def test_F007_weak_hits_do_not_fill_coverage_labelled_ge60():
    aa = reference()[0]['aa']
    gene = dict(id='g001', i=1, name='public_reference_gene', len=len(aa), modules=[], role_text='enzyme')
    prots = {'p1': dict(region='DEFINITION: Saccharopolyspora erythraea D scaffold00003, whole genome shotgun sequence / AVCN01000003.1 / region001 / BGC001', order=0, locus='public_tag')}
    hit = dict(qseqid='p1', sseqid='g001', pident=45, bitscore=500, sstart=1, send=len(aa))
    rows, _ = gsm.assign([gene], prots, [hit], {})
    assert rows[0]['best_cov'] == 100
    assert rows[0]['total_cov'] == 0, '45 percent identity is not coverage by matches at least 60 percent'

