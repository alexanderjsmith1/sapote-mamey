from argparse import Namespace

from mamey import cli


def _args(**overrides):
    d = dict(
        chatgpt_safe=True,
        chatgpt_followup=False,
        mode="gold",
        brief="standard",
        json_evidence="bounded",
        require_workbook=False,
        locus_maps="auto",
        heartbeat_seconds=20,
        strains=None,
        strain="TEST",
        input_zip="missing.zip",
        outdir="out",
        master=None,
        taxonomy=None,
        source=None,
        bioactivity=None,
        bioactivity_json=None,
        antismash_profile="unknown",
        release=None,
        metadata_csv=None,
        token_budget="standard",
        display_name=None,
    )
    d.update(overrides)
    return Namespace(**d)


def test_capped_session_allows_gold_first_run(monkeypatch):
    """v9.7.160: a capped session may run gold DIRECTLY — the old forced-smoke FATAL is gone.
    This is the fix for the smoke dead-end (empty triage board that looked finished)."""
    calls = []
    def fake_run_one_strain(**kwargs):
        calls.append(kwargs)
        return {"status": "MAMEY_COMPLETE"}
    monkeypatch.setattr(cli, "run_one_strain", fake_run_one_strain)
    rc = cli.run_command(_args(mode="gold", chatgpt_followup=False))
    # gold first-run must NOT be refused any more
    assert rc != 2
    assert calls and calls[0]["mode"] == "gold"


def test_capped_session_gold_is_only_mode(monkeypatch):
    """v9.7.161: smoke removed entirely — --mode smoke is rejected by argparse, and a capped
    session runs gold directly. There is no non-terminal smoke package to warn about any more."""
    import subprocess, sys as _sys
    out = subprocess.run(
        [_sys.executable, "-m", "mamey.cli", "run", "--strain", "T",
         "--input-zip", "x.zip", "--mode", "smoke"],
        capture_output=True, text=True)
    assert out.returncode != 0
    assert "invalid choice: 'smoke'" in out.stderr


def test_chatgpt_safe_followup_allows_non_smoke(monkeypatch):
    calls = []
    def fake_run_one_strain(**kwargs):
        calls.append(kwargs)
        return {"status": "MAMEY_COMPLETE"}
    monkeypatch.setattr(cli, "run_one_strain", fake_run_one_strain)
    rc = cli.run_command(_args(mode="gold", chatgpt_followup=True))
    assert rc == 0
    assert calls and calls[0]["mode"] == "gold"
    assert calls[0]["heartbeat_seconds"] == 20
