"""Card 464_verify_modeb_recorded_rescue_table: a v2 card emitted from a gap-rescue run names its
gap_rescue.tsv and SHA-256 under §26 "Source receipts". verify-modeb now uses that table when no
--rescue-tsv is given, and only while its bytes still match the recorded hash.

Synthetic fixtures only; no real card, package or sequence is read.
"""
import hashlib
import json
from types import SimpleNamespace

from mamey import authored_verify
from mamey.modeb_current50_v2 import recorded_rescue_tables
from .test_447_consolidated_modeb_integration import HEADER, ROSTER, ROWS, card

RESCUE = 'best_locus\tbest_region_identity\nctg9_6\tAS-999 / NODE_9_length_8000_cov_1 (no antiSMASH region)\n'


def _receipt_line(path, digest):
    return f'**Source receipts:**\n- `{path}` — SHA-256 `{digest}`\n'


def _card_with_receipt(tmp_path, tamper=False, missing=False):
    rescue = tmp_path / 'run' / 'gap_rescue.tsv'
    rescue.parent.mkdir()
    rescue.write_text(RESCUE)
    digest = hashlib.sha256(rescue.read_bytes()).hexdigest()
    if tamper:
        rescue.write_text(RESCUE + 'ctg9_7\tAS-999 / NODE_9_length_8000_cov_1 (no antiSMASH region)\n')
    if missing:
        rescue.unlink()
    md = card(HEADER + ''.join(ROWS)).replace(
        'ctg9_6 is an existence-only context identifier; focal membership remains unassigned.\n',
        'ctg9_6 is an existence-only context identifier; focal membership remains unassigned.\n'
        + _receipt_line(rescue, digest))
    return md, rescue


def test_matching_recorded_table_is_used(tmp_path):
    md, rescue = _card_with_receipt(tmp_path)
    paths, notes = recorded_rescue_tables(md)
    assert paths == [str(rescue)] and 'SHA-256 matches' in notes[0]


def test_changed_or_missing_recorded_table_is_not_used(tmp_path):
    md, _ = _card_with_receipt(tmp_path, tamper=True)
    paths, notes = recorded_rescue_tables(md)
    assert paths == [] and 'no longer matches' in notes[0]
    other = tmp_path / 'missing'
    other.mkdir()
    md, _ = _card_with_receipt(other, missing=True)
    paths, notes = recorded_rescue_tables(md)
    assert paths == [] and 'not on disk' in notes[0]


def test_receipt_outside_section_26_is_ignored(tmp_path):
    md, _ = _card_with_receipt(tmp_path)
    moved = md.replace(md[md.index('**Source receipts:**'):md.index('## §27')], '')
    start = moved.index('## §27'); end = moved.index('\n', start) + 1
    moved = moved[:end] + _receipt_line('elsewhere/gap_rescue.tsv', '0' * 64) + moved[end:]
    assert recorded_rescue_tables(moved) == ([], [])


def _verify(tmp_path, monkeypatch, md, rescue_tsv=None):
    ctx = {'known_loci': set(ROSTER), 'n_core_genes': 2, 'known_locus_tags': list(ROSTER)}
    monkeypatch.setattr(authored_verify, '_bgc_context_from_package', lambda *args: ctx)
    path, receipt = tmp_path / 'synthetic.md', tmp_path / 'receipt.json'
    path.write_text(md)
    result = authored_verify.verify_modeb_command(SimpleNamespace(
        file=str(path), contract='current50_v2', rescue_tsv=rescue_tsv,
        report_json=str(receipt), summary_only=True))
    return result, json.loads(receipt.read_text()), ctx


def test_verify_binds_the_recorded_table_without_the_flag(tmp_path, monkeypatch):
    md, _ = _card_with_receipt(tmp_path)
    result, receipt, ctx = _verify(tmp_path, monkeypatch, md)
    assert result == 0 and 'admitted for existence only (ctg9_6)' in receipt['profile']
    assert ctx['known_locus_tags'] == ROSTER and 'ctg9_6' in ctx['known_loci']


def test_verify_refuses_a_changed_recorded_table(tmp_path, monkeypatch):
    md, _ = _card_with_receipt(tmp_path, tamper=True)
    result, receipt, ctx = _verify(tmp_path, monkeypatch, md)
    assert 'ctg9_6' not in ctx['known_loci']
    assert result == 1 and any(f['code'] == 'PHANTOM_LOCUS' for f in receipt['findings'])


def test_explicit_flag_takes_precedence(tmp_path, monkeypatch):
    md, _ = _card_with_receipt(tmp_path, tamper=True)
    good = tmp_path / 'good_gap_rescue.tsv'
    good.write_text(RESCUE)
    result, receipt, ctx = _verify(tmp_path, monkeypatch, md, rescue_tsv=[str(good)])
    assert result == 0 and 'ctg9_6' in ctx['known_loci']
