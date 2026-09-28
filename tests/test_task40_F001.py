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
    rec = SeqIO.read(ROOT / 'tests/fixtures/task40_F001_public.gbk', 'genbank')
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


def test_F001_cross_hits_do_not_inflate_partner_genes():
    prots, regions, core = genome()
    hits = [dict(qseqid=g['id'], sseqid='p1', pident=90-i, qcovhsp=99, bitscore=500-i)
            for i, g in enumerate(reference())]
    rows, partners = gdr.search(reference(), prots, regions, hits, core)
    assert sum(bool(r.get('reciprocal_best')) for r in rows) == 1
    assert partners == [], 'one physical protein must not become three biosynthetic finds'

