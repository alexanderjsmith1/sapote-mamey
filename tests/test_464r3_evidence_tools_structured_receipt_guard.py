"""The structured-domain receipt and database may not replace a consumed package file or land in the source tree."""
import json
import pytest
from mamey import structured_domain_motif_extension as mod
from tests.test_structured_domain_motif_extension import fixture


def _args(tmp_path, source, base, inv, out, receipt, extra=()):
    return ['--inventory', str(inv), '--inventory-pin', mod.sha(inv), '--source-root', str(source),
            '--base', str(base), '--base-pin', mod.sha(base), '--out', str(out),
            '--allowed-root', str(tmp_path), '--receipt', str(receipt), *extra]


def test_receipt_equal_to_consumed_manifest_is_refused_in_resume_mode(tmp_path):
    source, base, row = fixture(tmp_path)
    inv = tmp_path / 'inventory.json'; inv.write_text(json.dumps([row]))
    manifest = source / 'pkg' / 'package' / 'manifest.json'
    before = manifest.read_bytes()
    with pytest.raises(ValueError, match='RECEIPT_PATH_COLLISION'):
        mod.main(_args(tmp_path, source, base, inv, tmp_path / 'side.sqlite', manifest, ['--resume']))
    assert manifest.read_bytes() == before


def test_receipt_inside_source_root_is_refused(tmp_path):
    source, base, row = fixture(tmp_path)
    inv = tmp_path / 'inventory.json'; inv.write_text(json.dumps([row]))
    with pytest.raises(ValueError, match='RECEIPT_PATH_COLLISION'):
        mod.main(_args(tmp_path, source, base, inv, tmp_path / 'side.sqlite', source / 'pkg' / 'receipt.json'))
    assert not (source / 'pkg' / 'receipt.json').exists()


def test_database_inside_source_root_is_refused(tmp_path):
    source, base, row = fixture(tmp_path)
    inv = tmp_path / 'inventory.json'; inv.write_text(json.dumps([row]))
    with pytest.raises(ValueError, match='OUTPUT_PATH_COLLISION'):
        mod.main(_args(tmp_path, source, base, inv, source / 'side.sqlite', tmp_path / 'receipt.json'))
    assert not (source / 'side.sqlite').exists()
