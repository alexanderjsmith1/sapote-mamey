"""PC-3 (v9.7.253 Bunny Hop session 2): pin the BLASTP batch business rules.

`mamey/blastp_batch_emitter.py` enforces exact rules (batch size 3 — not 5, not 10 — and
sequential integer batch numbering with no gaps or letter suffixes). These are the kind of
exact constants that regress silently; the module was previously untested.
"""
import pytest

from mamey.blastp_batch_emitter import (
    DEFAULT_BATCH_SIZE,
    BlastpBatchEmitter,
)


def test_default_batch_size_is_three():
    assert DEFAULT_BATCH_SIZE == 3
    assert BlastpBatchEmitter().batch_size == 3


def test_batches_never_exceed_batch_size():
    em = BlastpBatchEmitter(batch_size=3)
    for i in range(7):
        em.add(header=f"prot{i}", sequence="M" * 50)
    batches = em.emit()
    assert [len(b.entries) for b in batches] == [3, 3, 1]  # 7 proteins -> 3+3+1


def test_batch_numbering_is_sequential_no_gaps():
    em = BlastpBatchEmitter(batch_size=3)
    for i in range(8):
        em.add(header=f"p{i}", sequence="M" * 20)
    nums = [b.batch_number for b in em.emit()]
    assert nums == list(range(1, len(nums) + 1))  # 1,2,3,... no gaps, no suffixes


def test_start_batch_offset_respected():
    em = BlastpBatchEmitter(batch_size=3)
    for i in range(4):
        em.add(header=f"p{i}", sequence="M" * 20)
    nums = [b.batch_number for b in em.emit(start_batch=5)]
    assert nums == [5, 6]


def test_invalid_batch_size_rejected():
    with pytest.raises(ValueError):
        BlastpBatchEmitter(batch_size=0)
