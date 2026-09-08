"""Async BLASTp submit path (run_batches_online) — offline, fail-closed behavior.

Verifies the submit-all-then-poll-together runner introduced to replace the serial per-batch loop.
These tests do NOT hit NCBI; they exercise the fail-closed contract and the submit/poll split with
the network monkeypatched, so they run offline and deterministically. The live path is exercised
only where NCBI is reachable (protocol §6)."""
import mamey.blastp_online as bo


def test_empty_batches_returns_empty():
    assert bo.run_batches_online([]) == []


def test_oversized_batch_fails_closed_in_submit():
    r = bo._submit_batch([("x", "M" * 20)] * 31)  # v9.7.240: >MAX_BATCH(30) proteins
    assert r.ok is False
    assert "protocol" in r.reason


def test_submit_all_then_poll_together(monkeypatch):
    """Two batches: both submit, both come back READY on the first poll. Assert order preserved,
    hits parsed, and that submission happened for ALL batches before polling (the async property)."""
    calls = []

    def fake_post(data, timeout=120):
        cmd = data.get("CMD")
        calls.append((cmd, data.get("RID")))
        if cmd == "Put":
            # RID echoes the first locus tag so we can assert order
            qtag = data["QUERY"].splitlines()[0].lstrip(">")
            return f"RID = RID_{qtag}\n"
        if data.get("FORMAT_OBJECT") == "SearchInfo":
            return "Status=READY\n"
        return "<xml/>"  # FORMAT_TYPE=XML retrieval

    monkeypatch.setattr(bo, "_post", fake_post)
    monkeypatch.setattr(bo, "parse_blast_xml", lambda xml, batch: [("hit", batch[0][0])])
    monkeypatch.setattr(bo.time, "sleep", lambda *_: None)  # no real waiting

    batches = [[("locusA", "MAAA")], [("locusB", "MBBB")]]
    results = bo.run_batches_online(batches, poll_seconds=1, submit_gap_seconds=0)

    assert len(results) == 2
    assert results[0].rid == "RID_locusA"
    assert results[1].rid == "RID_locusB"
    assert all(r.ok for r in results)
    # async property: both Puts issued before any Get (poll) call
    put_idx = [i for i, (c, _) in enumerate(calls) if c == "Put"]
    get_idx = [i for i, (c, _) in enumerate(calls) if c == "Get"]
    assert max(put_idx) < min(get_idx), "all submissions must precede polling (async submit)"


def test_failed_submit_is_final_and_ordered(monkeypatch):
    """A batch whose Put returns no RID stays ok=False in place; a good batch still resolves."""
    def fake_post(data, timeout=120):
        if data.get("CMD") == "Put":
            q = data["QUERY"]
            return "no rid here\n" if "BAD" in q else "RID = RID_ok\n"
        if data.get("FORMAT_OBJECT") == "SearchInfo":
            return "Status=READY\n"
        return "<xml/>"

    monkeypatch.setattr(bo, "_post", fake_post)
    monkeypatch.setattr(bo, "parse_blast_xml", lambda xml, batch: [])
    monkeypatch.setattr(bo.time, "sleep", lambda *_: None)

    results = bo.run_batches_online([[("BAD", "M")], [("good", "M")]],
                                    poll_seconds=1, submit_gap_seconds=0)
    assert results[0].ok is False
    assert results[1].ok is True and results[1].rid == "RID_ok"
