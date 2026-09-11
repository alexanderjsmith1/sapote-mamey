from pathlib import Path
import csv
from mamey.wise_fragmented_pks import RankedProteinRecord, split_ranked_fasta_by_residues, write_wise_batches, plan_cpu_failure_recovery

def rec(rank, n):
    return RankedProteinRecord(rank=rank, header=f"AS-X|NODE_{rank}|ctg{rank}|aa={n}|rank={rank}", sequence="M"*n, strain="AS-X", region=f"NODE_{rank}", locus=f"ctg{rank}")

def test_85k_batches_fill_past_top30_when_room(tmp_path):
    records=[rec(i, 4000 if i <= 30 else 2000) for i in range(1,45)]
    batches=split_ranked_fasta_by_residues(records, target_residues=85000)
    assert sum(r.residues for r in batches[0]) <= 100000
    assert max(r.rank for r in batches[1]) > 30

def test_write_wise_batches_emits_unique_q_ids_and_ledger(tmp_path):
    records=[rec(i, 5000) for i in range(1,30)]
    summary=write_wise_batches(records, tmp_path, active_files=2, start_q=8)
    rows=list(csv.DictReader((tmp_path/'ACTIVE_AND_DEFERRED_QUEUE_FILES.csv').open()))
    qids=[r['queue_id'] for r in rows]
    assert qids[0].startswith('BLASTP_Q008')
    assert len(qids) == len(set(qids))
    assert all(int(r['residue_count']) <= 100000 for r in rows)
    assert (tmp_path/'STABLE_QUEUE_LEDGER.csv').exists()

def test_cpu_failure_recovery_keeps_failed_pending_and_splits_10():
    active=[{'rank':i,'queue_id':'BLASTP_Q006','status':'pending'} for i in range(53,65)]
    recovery=plan_cpu_failure_recovery(active, {'BLASTP_Q006'}, next_q=8, max_proteins=10)
    assert recovery[0]['queue_id'] == 'BLASTP_Q008_CPU_RETRY_10'
    assert recovery[0]['sequence_count'] == 10
    assert recovery[1]['sequence_count'] == 2


def test_exactly_hard_cap_is_not_isolated():
    """F003 boundary: a sequence of exactly NCBI_WEB_HARD_CAP residues is within the
    web BLASTP limit, so it must flow into normal batching, not be flagged as oversized."""
    from mamey.wise_fragmented_pks import NCBI_WEB_HARD_CAP
    records=[rec(1, NCBI_WEB_HARD_CAP)]
    batches=split_ranked_fasta_by_residues(records)
    assert len(batches) == 1 and len(batches[0]) == 1
    assert not batches[0][0].warning, "exactly-cap sequence must not carry an oversized warning"

def test_over_hard_cap_is_isolated_and_warned():
    """A sequence strictly above the cap is still isolated and warned."""
    from mamey.wise_fragmented_pks import NCBI_WEB_HARD_CAP
    records=[rec(1, NCBI_WEB_HARD_CAP + 1)]
    batches=split_ranked_fasta_by_residues(records)
    assert len(batches) == 1 and len(batches[0]) == 1
    assert batches[0][0].warning is not None

def test_extra_safe_uses_conservative_target():
    """F004: extra_safe=True wires EXTRA_SAFE_TARGET_RESIDUES so the constant is reachable."""
    from mamey.wise_fragmented_pks import EXTRA_SAFE_TARGET_RESIDUES
    # two 30k records: under the 85k default they share a batch; under the 50k extra-safe
    # target the second record opens a new batch.
    records=[rec(1, 30000), rec(2, 30000)]
    default_batches=split_ranked_fasta_by_residues(records)
    safe_batches=split_ranked_fasta_by_residues(records, extra_safe=True)
    assert len(default_batches) == 1
    assert len(safe_batches) == 2
    assert EXTRA_SAFE_TARGET_RESIDUES == 50_000
