"""Explicit opt-in actual BLAST path control; remaining companions are synthetic.

No installed executable is discovered automatically. This proves only safe native
BLAST filesystem/subject-row transport, not orthology or a scientific MLSA result.
"""
import json
import os
from pathlib import Path

import pytest

from tests.test_build_mlsa_fail_closed_workflow import _write_python_stub, STUB
from tests.test_mlsa_resource_workspace import inputs, safe_root, arguments
from tools import _mlsa_resources as resource
from tools import build_mlsa as mlsa


@pytest.mark.skipif(os.environ.get('MAMEY_RUN_ACTUAL_BLAST_PATH_CONTROL') != '1',
                    reason='actual native BLAST control requires separate explicit execution authorization')
def test_actual_blast_in_safe_cwd_with_spaced_original_inputs_and_outputs(inputs, safe_root, monkeypatch):
    selected = {name: os.environ.get('MAMEY_ACTUAL_' + name.upper()) for name in ('makeblastdb', 'blastp')}
    if not all(selected.values()):
        pytest.fail('explicit MAMEY_ACTUAL_MAKEBLASTDB and MAMEY_ACTUAL_BLASTP are required')
    # Fresh invented high-complexity protein, identical seed for a mechanical exact
    # match; unrelated fabricated CDS tests only subject-id lookup/transport.
    protein = ('MPTKDVLRAGNEHFIQSWCY' * 6)
    genomes, seeds, bins, out = inputs
    assert ' ' in str(genomes) and ' ' in str(seeds) and ' ' in str(out)
    for locus in mlsa.LOCI:
        (seeds / (locus + '.faa')).write_text('>SYNTHETIC_REFERENCE_SEED\n' + protein + '\n')
    body = STUB.replace(">gene\\nMPEP\\n", '>gene\\n' + protein + '\\n').replace(
        ">gene\\nATGCCCGAACCC\\n", '>gene\\n' + 'ATG' * len(protein) + '\\n')
    for name in ('prodigal', 'muscle', 'iqtree'):
        _write_python_stub(bins / name, body)
    monkeypatch.setenv('CALL_LOG', str(out.parent / 'synthetic-companion-calls.jsonl'))
    resolve = mlsa.resolve_bin
    monkeypatch.setattr(mlsa, 'resolve_bin', lambda name, directory=None: selected.get(name) or resolve(name, directory))
    args = arguments(inputs, safe_root, ('--timeout-seconds', '120',
        '--min-free-disk-bytes', '2000000000', '--rss-limit-bytes', '3800000000'))
    assert resource.coordinate(args) == 0  # actual existing whole-worker watcher
    identity = json.loads((out / 'native_blast_identity.json').read_text())
    assert identity['state'] == 'SUCCEEDED'
    assert all(row['source']['sha256'] == row['copy']['sha256']
               for row in identity['source_copies'] + identity['seed_copies'])
    assert 'HIT' in (out / 'loci_report.tsv').read_text()
    attempt = next((out / 'RESOURCE_ATTEMPT').iterdir())
    request = resource.load(attempt / 'REQUEST.json')
    for name, locator in selected.items():
        assert request['tools'][name] == resource.tool_binding(locator)
    assert not Path(request['scratch']['path']).exists()
    watched = resource.load(attempt / 'RESOURCE.json')
    assert watched['exit_code'] == 0 and watched['stop_reason'] is None and watched['cleanup_error'] is None
