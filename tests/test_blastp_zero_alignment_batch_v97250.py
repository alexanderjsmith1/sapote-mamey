"""v9.7.250 — a batch that returns zero alignments for every query is a transport failure, not data.

P1, reported by an analysis chat on 2026-07-09 (bundle v9.7.246, engine 1.9.109). At
`--batch-size 30`, one whole submission batch reproducibly (3x, real nr, AS-678 BGC034) returned zero
alignments. `reconcile()` maps an empty `hit_def` to `NO_HIT`, so all 30 genes were written into
`<BGC>_online_blastp.csv` as **tested negatives**. Re-running the identical protein set at
`--batch-size 10` recovered them at 61-99% identity.

Those NO_HIT rows feed `conservation_median_id`, the input to `NOVELTY_CONTRADICTION`. It is the
v9.7.241 P7a shape -- a biased subset silently arming the novelty guard -- through a different door.

**The mechanism is not established, and this test does not pretend otherwise.** It pins the behaviour
that does not depend on one: a multi-query batch with zero alignments everywhere is refused, and a
solo giant with no homolog is not.

The report's fix #4 is the reason this file exists at all:

    "P7a survived .239 because every test ingested one round. This survives because every test
     submits one batch, or a batch of <=10. Any test of the submission path should submit MORE THAN
     ONE BATCH, AT THE CONFIGURED MAX_BATCH, and assert per-gene hit recovery."

So `test_multi_batch_at_max_batch_recovers_every_gene` submits 83 proteins at `MAX_BATCH`, through a
fake transport, and asserts per-gene recovery -- and its sibling makes batch 2 come back empty and
asserts we refuse it.
"""
from __future__ import annotations
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mamey import blastp_online as bo  # noqa: E402


def _hit(defn=""):
    return bo.BlastpHit(locus_tag="x", aa_length=100, antismash_domains="", blastp_top_def=defn)


# --------------------------------------------------------------------- the guard itself
def test_all_zero_multiquery_batch_is_flagged():
    assert bo._zero_alignment_batch([_hit() for _ in range(30)]) is True


def test_one_real_hit_rescues_the_batch():
    assert bo._zero_alignment_batch([_hit() for _ in range(29)] + [_hit("SDR family")]) is False


def test_solo_giant_with_no_homolog_is_not_flagged():
    """Giants are submitted solo. One gene with no nr homolog is an ordinary, real outcome."""
    assert bo._zero_alignment_batch([_hit()]) is False


def test_empty_batch_is_not_flagged():
    assert bo._zero_alignment_batch([]) is False


def test_whitespace_only_hit_def_counts_as_zero():
    assert bo._zero_alignment_batch([_hit("  "), _hit("\t")]) is True


# --------------------------------------------------------------------- batching contract
def test_safe_batch_is_ten_and_max_batch_is_not_silently_lowered():
    """SAFE_BATCH is the vetted default; MAX_BATCH stays 30 (an independent 36-RID AS-705 campaign
    ran five 30-query batches with 27-28/30 hit, so >10 is not universally broken)."""
    assert bo.SAFE_BATCH == 10
    assert bo.DEFAULT_BATCH == 10
    assert bo.MAX_BATCH == 30


def test_chunk_proteins_defaults_to_safe_batch():
    proteins = [(f"ctg1_{i}", "A" * 100) for i in range(60)]
    assert [len(b) for b in bo.chunk_proteins(proteins)] == [10] * 6


def test_chunk_proteins_warns_above_safe_batch(capsys):
    proteins = [(f"ctg1_{i}", "A" * 100) for i in range(30)]
    bo.chunk_proteins(proteins, batch_size=30)
    err = capsys.readouterr().err
    assert "SAFE_BATCH" in err and "zero alignments" in err


def test_chunk_proteins_silent_at_safe_batch(capsys):
    bo.chunk_proteins([(f"ctg1_{i}", "A" * 100) for i in range(30)], batch_size=10)
    assert "WARNING" not in capsys.readouterr().err


# --------------------------------------------------------------------- the submission path
class _FakeNCBI:
    """Minimal stand-in for `_post`. `empty_batches` are the 1-based batch numbers that come back
    with zero alignments -- exactly the reported failure."""

    def __init__(self, empty_batches=()):
        self.empty = set(empty_batches)
        self.n_put = 0
        self.rid_batch = {}

    def __call__(self, data, timeout=120):
        cmd = data.get("CMD")
        if cmd == "Put":
            self.n_put += 1
            rid = f"RID{self.n_put:03d}"
            self.rid_batch[rid] = self.n_put
            return f"    RID = {rid}\n"
        rid = data.get("RID")
        if data.get("FORMAT_OBJECT") == "SearchInfo":
            return f"Status=READY\n"
        # a Get for XML
        n = self.rid_batch[rid]
        if n in self.empty:
            return "<BlastOutput></BlastOutput>"     # parses to zero alignments
        return f"<BlastOutput>HITS-{n}</BlastOutput>"


def _install(monkeypatch, fake, hits_per_batch):
    monkeypatch.setattr(bo, "_post", fake)
    monkeypatch.setattr(bo.time, "sleep", lambda *_a, **_k: None)

    def fake_parse(xml_text, batch, top_n=6):
        if "HITS-" not in xml_text:
            return [bo.BlastpHit(locus_tag=lt, aa_length=len(s), antismash_domains="")
                    for lt, s in batch]
        return [bo.BlastpHit(locus_tag=lt, aa_length=len(s), antismash_domains="",
                             blastp_top_def="NDP-hexose 2,3-dehydratase family protein",
                             pct_identity=98.8)
                for lt, s in batch]
    monkeypatch.setattr(bo, "parse_blast_xml", fake_parse)
    return hits_per_batch


def test_multi_batch_at_max_batch_recovers_every_gene(monkeypatch):
    """The test the report asked for: >1 batch, at MAX_BATCH, assert per-gene recovery."""
    proteins = [(f"ctg4_{i}", "A" * 300) for i in range(83)]
    _install(monkeypatch, _FakeNCBI(), None)
    batches = bo.chunk_proteins(proteins, batch_size=bo.MAX_BATCH)
    assert len(batches) > 1, "fixture must exercise more than one batch"
    assert max(len(b) for b in batches) == bo.MAX_BATCH

    results = bo.run_batches_online(batches, poll_seconds=0, submit_gap_seconds=0)
    assert all(r.ok for r in results)
    recovered = {h.locus_tag for r in results for h in r.hits}
    assert recovered == {lt for lt, _ in proteins}, "every gene must be recovered"


def test_zero_alignment_batch_is_refused_not_recorded(monkeypatch):
    """Batch 2 comes back empty -- exactly the reported failure. It must NOT become 30 negatives."""
    proteins = [(f"ctg4_{i}", "A" * 300) for i in range(83)]
    _install(monkeypatch, _FakeNCBI(empty_batches=(2,)), None)
    batches = bo.chunk_proteins(proteins, batch_size=bo.MAX_BATCH)

    results = bo.run_batches_online(batches, poll_seconds=0, submit_gap_seconds=0)
    bad = [r for r in results if not r.ok]
    assert len(bad) == 1, f"exactly one batch should be refused, got {[r.reason for r in bad]}"
    assert "zero alignments" in bad[0].reason
    assert "batch-size 10" in bad[0].reason

    # and none of that batch's genes leaked into the recorded hits as NO_HIT
    recorded = [h for r in results if r.ok for h in r.hits]
    assert all((h.blastp_top_def or "").strip() for h in recorded), (
        "a refused batch's genes must not appear as tested-negatives"
    )
    assert len(recorded) == 83 - len(batches[1]), "only the refused batch's genes are missing"


def test_solo_giant_empty_result_is_still_recorded(monkeypatch):
    """A giant is submitted solo; a genuine no-hit for it must survive as data."""
    proteins = [("ctg4_152", "A" * 4485)]
    _install(monkeypatch, _FakeNCBI(empty_batches=(1,)), None)
    batches = bo.chunk_proteins(proteins, batch_size=bo.MAX_BATCH)
    assert [len(b) for b in batches] == [1]
    results = bo.run_batches_online(batches, poll_seconds=0, submit_gap_seconds=0)
    assert results[0].ok, "a solo no-hit is a real negative, not a transport failure"
    assert len(results[0].hits) == 1
