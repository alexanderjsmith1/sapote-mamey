"""Card 464_v2_core_grid_reads_the_matrix: the current50_v2 core-gene BLASTp check must read the complete
named-match matrix in §50.

The template places the engine's gene table, with ● on core genes, in §50 ahead of the matrix. That table
never carries identity or a CONFIRM/REFINE/OVERTURN verdict. Unless an expanded-locus marker bound the
roster, the check read only the ● rows and reported BLASTP_ABSENT for a card whose matrix was complete.
Synthetic fixtures only.
"""
import json
from types import SimpleNamespace

from mamey import authored_verify
from .test_447_consolidated_modeb_integration import HEADER, ROSTER, ROWS, card

ENGINE_GRID = ('| Core | Locus tag | aa | sec_met domains |\n|:---:|---|---:|---|\n'
               + ''.join(f'| ● | `{tag}` | 300 | PKS_KS |\n' for tag in ROSTER) + '\n')


def _verify(tmp_path, monkeypatch, table):
    ctx = {'known_loci': set(ROSTER), 'n_core_genes': 2, 'known_locus_tags': list(ROSTER)}
    monkeypatch.setattr(authored_verify, '_bgc_context_from_package', lambda *args: ctx)
    path, receipt = tmp_path / 'synthetic.md', tmp_path / 'receipt.json'
    path.write_text(card(table))
    result = authored_verify.verify_modeb_command(SimpleNamespace(
        file=str(path), contract='current50_v2', rescue_tsv=None, report_json=str(receipt), summary_only=True))
    return result, json.loads(receipt.read_text()), ctx


def test_complete_matrix_satisfies_the_core_grid_check(tmp_path, monkeypatch):
    result, receipt, ctx = _verify(tmp_path, monkeypatch, ENGINE_GRID + HEADER + ''.join(ROWS))
    codes = {f['code'] for f in receipt['findings']}
    assert not codes & {'BLASTP_ABSENT', 'BLASTP_THIN'}, codes
    assert ctx['modeb_matrix_locus_tags'] == ROSTER


def test_matrix_without_verdicts_is_still_reported(tmp_path, monkeypatch):
    bare = [r.replace('CONFIRM ', '') for r in ROWS]
    _, receipt, _ = _verify(tmp_path, monkeypatch, ENGINE_GRID + HEADER + ''.join(bare))
    assert {f['code'] for f in receipt['findings']} & {'BLASTP_ABSENT', 'BLASTP_THIN'}
