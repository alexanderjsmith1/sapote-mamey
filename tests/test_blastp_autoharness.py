"""blastp_autoharness — the resumable priority BLASTp scheduler (v9.7.345).

Offline + deterministic. Verifies:
  * worklist ordering (AF-first) and that already-ingested BGCs are excluded via the ledger;
  * the scheduler respects the 8-min submit gap and the hourly ingest cadence under a FAKE clock;
  * resumability: state round-trips through disk with no double-submit;
  * mock submit/poll/ingest (transport is injectable — NCBI is never contacted);
  * NO email / personal id is ever placed in an outbound request payload.
No test here touches the network.
"""
import json
import csv
from pathlib import Path

import pytest

import mamey.blastp_autoharness as ah


# --------------------------------------------------------------------------------------------
# a tiny synthetic sealed package (no external data)
# --------------------------------------------------------------------------------------------
def _make_pkg(tmp_path, ingested_nr=("BGC003",)):
    pkg = tmp_path / "package"
    pkg.mkdir()
    strain = "AS-TST"
    # triage board: BGC001 high AF, BGC002 high AB, BGC003 already ingested, BGC004 low
    cols = ["Rank", "BGC_ID", "Products", "Contig", "Node_ID", "AB_auto", "AF_auto",
            "Novelty_auto", "Lead_tier_auto", "Corrected_rank"]
    rows = [
        ["1", "BGC001", "NRPS", "ctgA", "ctgA", "20", "90", "50", "HIGH", "2"],
        ["2", "BGC002", "T1PKS", "ctgB", "ctgB", "88", "10", "40", "HIGH", "1"],
        ["3", "BGC003", "RiPP", "ctgC", "ctgC", "30", "70", "60", "MEDIUM", "3"],
        ["4", "BGC004", "terpene", "ctgD", "ctgD", "5", "5", "10", "LOW", "4"],
    ]
    with (pkg / f"{strain}_4_triage_board.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows)
    # manifest_short.json — how _gene_rows_for_bgc resolves the {strain}_gene_context.jsonl name
    (pkg / "manifest_short.json").write_text(json.dumps({"strain_id": strain}), encoding="utf-8")
    # manifest.json — sealed-package identity; PATCH007 five-part ingest guard (_package_strain)
    # requires a readable package manifest before writing any channel store (real packages always
    # carry this; the pre-PATCH007 fixture omitted it because .344 predated this test).
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain}), encoding="utf-8")
    # gene_context.jsonl — one object per BGC with its CDS loci
    gc = []
    for bgc in ("BGC001", "BGC002", "BGC003", "BGC004"):
        gc.append({"bgc_id": bgc, "cds": [
            # aa_length matches the 43-aa proteins.faa entries below ("MKV" + 40); PATCH007's
            # five-part guard reads the authoritative current aa length from the gene context.
            {"locus_tag": f"{bgc}_g1", "start": 1, "aa_length": 43},
            {"locus_tag": f"{bgc}_g2", "start": 2, "aa_length": 43},
        ]})
    (pkg / f"{strain}_gene_context.jsonl").write_text(
        "\n".join(json.dumps(o) for o in gc), encoding="utf-8")
    # proteins.faa — sequences for every locus
    faa = []
    for bgc in ("BGC001", "BGC002", "BGC003", "BGC004"):
        for g in ("g1", "g2"):
            faa.append(f">{bgc}_{g}\nMKV" + "A" * 40)
    (pkg / f"{strain}_proteins.faa").write_text("\n".join(faa) + "\n", encoding="utf-8")
    # an ingest ledger marking some BGCs already done on nr
    store = pkg / "blastp_online"
    store.mkdir()
    ledger = {"nr": {b: {"n_genes": 2} for b in ingested_nr}}
    (store / "_ingest_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
    return pkg, strain


# --------------------------------------------------------------------------------------------
# worklist
# --------------------------------------------------------------------------------------------
def test_worklist_af_first_ordering_and_ledger_exclusion(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=("BGC003",))
    wl = ah.build_worklist(pkg, strain, priority="af_first", channel="nr")
    bgcs = [it["bgc_id"] for it in wl]
    # BGC003 is already ingested on nr -> excluded
    assert "BGC003" not in bgcs
    # AF-first: BGC001 (AF=90) before BGC002 (AF=10) before BGC004 (AF=5)
    assert bgcs == ["BGC001", "BGC002", "BGC004"]
    assert wl[0]["af"] == 90.0 and wl[0]["n_proteins"] == 2


def test_worklist_ab_first_ordering(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    wl = ah.build_worklist(pkg, strain, priority="ab_first", channel="nr")
    bgcs = [it["bgc_id"] for it in wl]
    # AB-first: BGC002 (AB=88) leads; BGC003 now included (nothing ingested)
    assert bgcs[0] == "BGC002"
    assert "BGC003" in bgcs


def test_worklist_rank_priority(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    wl = ah.build_worklist(pkg, strain, priority="rank", channel="nr")
    # corrected_rank order: BGC002(1), BGC001(2), BGC003(3), BGC004(4)
    assert [it["bgc_id"] for it in wl] == ["BGC002", "BGC001", "BGC003", "BGC004"]


# --------------------------------------------------------------------------------------------
# payload safety — NO email / personal id
# --------------------------------------------------------------------------------------------
def test_submit_payload_has_no_email_or_personal_id():
    payload = ah.build_submit_payload(">g\nMKVAAA", database="nr")
    assert "email" not in payload
    assert "EMAIL" not in payload
    # the anonymous common-pool tag is the ONLY identifier
    assert payload["tool"] == "SapoteMamey"
    blob = json.dumps(payload).lower()
    for personal in ("example_user", "@gmail.com", "@", "maintainer"):
        assert personal not in blob, f"personal id leaked into payload: {personal!r}"


def test_default_submit_fn_uses_no_email(monkeypatch):
    """The real submit path (blastp_online._submit_batch) must post NO email. Capture the payload."""
    import mamey.blastp_online as bo
    captured = {}

    def fake_post(data, timeout=120):
        captured.update(data)
        return "RID = ABC123\n"
    monkeypatch.setattr(bo, "_post", fake_post)
    fn = ah.default_submit_fn(channel="nr")
    res = fn({"unit_id": "BGC001#0", "bgc_id": "BGC001",
              "batch": [["BGC001_g1", "MKVAAA"]], "batch_index": 0, "n_proteins": 1})
    assert res["ok"] and res["rid"] == "ABC123"
    assert "email" not in captured and "EMAIL" not in captured
    assert captured.get("tool") == "SapoteMamey"


# --------------------------------------------------------------------------------------------
# scheduler cadence with a fake clock + mock fns
# --------------------------------------------------------------------------------------------
def _mock_fns():
    calls = {"submit": [], "poll": [], "ingest": []}

    def submit_fn(unit):
        calls["submit"].append(unit["unit_id"])
        return {"ok": True, "rid": f"RID_{unit['unit_id']}", "reason": ""}

    def poll_fn(entry):
        calls["poll"].append(entry["unit_id"])
        return {"status": "READY", "result_ref": {"unit": entry["unit_id"]}}

    def ingest_fn(entries, state):
        calls["ingest"].append([e["unit_id"] for e in entries])
        return {"ingested": [e["unit_id"] for e in entries]}

    return calls, submit_fn, poll_fn, ingest_fn


def test_submit_respects_8min_gap(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    wl = ah.build_worklist(pkg, strain, priority="af_first")
    state = ah.new_state(pkg, strain, wl)
    calls, submit_fn, poll_fn, ingest_fn = _mock_fns()

    # t=0: first submit fires (last_submit_ts is None)
    ah.tick(0.0, state, submit_fn, poll_fn, ingest_fn)
    assert len(calls["submit"]) == 1
    # t=100s (<480): NO second submit
    ah.tick(100.0, state, submit_fn, poll_fn, ingest_fn)
    assert len(calls["submit"]) == 1
    # t=480s: second submit allowed
    ah.tick(480.0, state, submit_fn, poll_fn, ingest_fn)
    assert len(calls["submit"]) == 2


def test_hourly_ingest_cadence(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    wl = ah.build_worklist(pkg, strain, priority="af_first")
    state = ah.new_state(pkg, strain, wl)
    calls, submit_fn, poll_fn, ingest_fn = _mock_fns()

    # submit + poll at t=0 -> unit retrieved, but ingest is NOT yet due (last_ingest_ts None ->
    # first retrieved triggers ingest immediately on the first tick where retrieved is non-empty).
    ah.tick(0.0, state, submit_fn, poll_fn, ingest_fn)
    # first retrieved -> ingest runs (due because last_ingest_ts is None)
    assert len(calls["ingest"]) == 1
    # next submit at t=480, retrieved again; ingest NOT due until +3600 from last ingest (t=0)
    ah.tick(480.0, state, submit_fn, poll_fn, ingest_fn)
    assert len(calls["ingest"]) == 1  # still 1 — hourly gate holds
    # t=3600: ingest due again
    ah.tick(3600.0, state, submit_fn, poll_fn, ingest_fn)
    assert len(calls["ingest"]) == 2


def test_adjustable_ingest_interval(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    wl = ah.build_worklist(pkg, strain, priority="af_first")
    # short submit interval so a fresh unit is retrieved on each tick to feed the ingest gate
    state = ah.new_state(pkg, strain, wl, submit_interval_s=1, ingest_interval_s=120)
    calls, submit_fn, poll_fn, ingest_fn = _mock_fns()
    ah.tick(0.0, state, submit_fn, poll_fn, ingest_fn)   # submit+retrieve u1; ingest #1 (last None)
    ah.tick(60.0, state, submit_fn, poll_fn, ingest_fn)  # submit+retrieve u2; ingest <120 -> held
    assert len(calls["ingest"]) == 1
    ah.tick(120.0, state, submit_fn, poll_fn, ingest_fn)  # submit+retrieve u3; ingest due
    assert len(calls["ingest"]) == 2


# --------------------------------------------------------------------------------------------
# resumability / idempotency
# --------------------------------------------------------------------------------------------
def test_state_round_trips_and_no_double_submit(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    wl = ah.build_worklist(pkg, strain, priority="af_first")
    state = ah.new_state(pkg, strain, wl)
    calls, submit_fn, poll_fn, ingest_fn = _mock_fns()

    ah.tick(0.0, state, submit_fn, poll_fn, ingest_fn)
    first_submitted = list(calls["submit"])
    ah.save_state(pkg, state)

    # reload from disk (simulate process restart)
    reloaded = ah.load_state(pkg)
    assert reloaded is not None
    # the already-submitted unit is not in the queue anymore
    queued_ids = {u["unit_id"] for u in reloaded["queue"]}
    assert first_submitted[0] not in queued_ids
    # resuming and ticking BEFORE the gap does NOT re-submit the same unit
    ah.tick(10.0, reloaded, submit_fn, poll_fn, ingest_fn)
    assert calls["submit"].count(first_submitted[0]) == 1


def test_init_state_resumes_existing(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    wl = ah.build_worklist(pkg, strain, priority="af_first")
    state = ah.new_state(pkg, strain, wl)
    state["n_submits"] = 5
    ah.save_state(pkg, state)
    resumed = ah.init_state(pkg, strain, resume=True)
    assert resumed["n_submits"] == 5   # progress preserved


# --------------------------------------------------------------------------------------------
# full run driver with fake clock + mocks (no network, no real sleep)
# --------------------------------------------------------------------------------------------
def test_run_completes_offline(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=("BGC003",))
    calls, submit_fn, poll_fn, ingest_fn = _mock_fns()

    # fake clock that advances by the submit interval each read so the whole queue drains
    t = {"v": 0.0}

    def clock():
        return t["v"]

    def sleep_fn(_s):
        t["v"] += 480.0   # jump a full submit window each loop

    state = ah.run(pkg, strain, submit_fn=submit_fn, poll_fn=poll_fn, ingest_fn=ingest_fn,
                   clock=clock, sleep_fn=sleep_fn, poll_gap_s=480.0)
    assert ah.is_done(state)
    # 3 BGCs x 1 batch each (small panels) = 3 units, all submitted + ingested exactly once
    assert sorted(state["ingested"]) == ["BGC001#0", "BGC002#0", "BGC004#0"]
    assert len(state["provenance"]) == 3
    # provenance carries channel + RID + timestamps
    p0 = state["provenance"][0]
    assert p0["channel"] == "nr" and p0["rid"].startswith("RID_")
    assert "submit_ts" in p0 and "ingest_ts" in p0


def test_max_submits_caps_puts(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    wl = ah.build_worklist(pkg, strain, priority="af_first")
    state = ah.new_state(pkg, strain, wl)
    calls, submit_fn, poll_fn, ingest_fn = _mock_fns()
    ah.tick(0.0, state, submit_fn, poll_fn, ingest_fn, max_submits=1)
    ah.tick(480.0, state, submit_fn, poll_fn, ingest_fn, max_submits=1)
    ah.tick(960.0, state, submit_fn, poll_fn, ingest_fn, max_submits=1)
    assert state["n_submits"] == 1   # capped


# --------------------------------------------------------------------------------------------
# dry-run report never contacts network
# --------------------------------------------------------------------------------------------
def test_dry_run_report_no_network(tmp_path, monkeypatch):
    import mamey.blastp_online as bo

    def boom(*a, **k):
        raise AssertionError("network contacted during dry run")
    monkeypatch.setattr(bo, "_post", boom)
    pkg, strain = _make_pkg(tmp_path, ingested_nr=("BGC003",))
    rep = ah.dry_run_report(pkg, strain, priority="af_first")
    assert rep["n_bgcs"] == 3
    assert rep["worklist"][0]["bgc_id"] == "BGC001"
    assert rep["submit_interval_s"] == ah.DEFAULT_SUBMIT_INTERVAL_S


# --------------------------------------------------------------------------------------------
# default ingest_fn actually reuses install_channel_top10 (unmixed store + ledger), offline
# --------------------------------------------------------------------------------------------
def test_default_ingest_writes_unmixed_store_and_ledger(tmp_path):
    pkg, strain = _make_pkg(tmp_path, ingested_nr=())
    # a retrieved unit whose cached result has one gene with pct_identity AND pct_positives
    store = pkg / "blastp_online"
    cache = store / "_autoharness_cache"
    cache.mkdir(parents=True)
    ref = cache / "BGC001_0.json"
    ref.write_text(json.dumps({"bgc_id": "BGC001", "rows": [{
        "strain": strain, "bgc_id": "BGC001", "gene": "BGC001_g1", "aa_length": 43,
        "role": "", "hit_rank": 1, "subject_acc": "WP_1", "subject_organism": "Streptomyces sp.",
        "subject_def": "NRPS", "pct_identity": "62.0", "pct_positives": "75.0",
        "query_coverage": "98", "evalue": "1e-40", "bitscore": "120"}]}), encoding="utf-8")
    entries = [{"unit_id": "BGC001#0", "bgc_id": "BGC001", "channel": "nr",
                "rid": "RID_X", "result_ref": str(ref)}]
    fn = ah.default_ingest_fn(pkg, strain, channel="nr")
    out = fn(entries, {})
    assert out["ingested"] == ["BGC001#0"]
    # unmixed store written
    nr_store = pkg / "blastp_nr" / "BGC001_top10.csv"
    assert nr_store.exists()
    got = list(csv.DictReader(nr_store.open()))
    assert got[0]["pct_identity"] == "62.0" and got[0]["pct_positives"] == "75.0"
    # ledger updated so the gate is satisfied
    from mamey.blastp_ingest import read_ingest_ledger
    assert "BGC001" in read_ingest_ledger(pkg).get("nr", {})
