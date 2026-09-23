"""blastp-online must not send sequence to NCBI until someone says so.

`blastp-round` has required an explicit `--run` since v9.7.180, with the help text "actually submit
to NCBI (default: dry-run plan only)". Its sibling `blastp-online` submitted the moment it was
invoked: `blastp_online_command` fell straight through to `run_batches_online`. The scoping and
oversized-unscoped guards bound how MUCH leaves the machine; nothing established that it was
allowed to leave at all. Two commands that both disclose sequence to a third party should not
disagree about whether disclosure is the default.

These tests pin the gate by the only thing that matters: whether the network function is reached.
"""
import types

import pytest

from mamey import blastp_online


class _Feat:
    def __init__(self, tag, translation):
        self.locus_tag = tag
        self.translation = translation


@pytest.fixture
def no_network(monkeypatch):
    """Record whether the submitting function was reached; never actually call out."""
    calls = []

    def _spy(batches, **kw):
        calls.append((batches, kw))
        raise AssertionError("run_batches_online was reached — the gate did not hold")

    monkeypatch.setattr(blastp_online, "run_batches_online", _spy)
    monkeypatch.setattr(blastp_online, "extract_cds_features",
                        lambda p: [_Feat("cds_1", "MKT"), _Feat("cds_2", "MAAA")],
                        raising=False)
    # the command imports extract_cds_features from .parsers inside the function body
    monkeypatch.setattr("mamey.parsers.extract_cds_features",
                        lambda p: [_Feat("cds_1", "MKT"), _Feat("cds_2", "MAAA")])
    return calls


def _args(**over):
    base = dict(package="unused-because-extraction-is-stubbed", bgc=None, region=None,
                database="nr", evalue="1e-5", batch_size=10, outdir=None,
                crosswalk=None, kcb_top=None, kcb_coverage_genes=None,
                submit=False, confirm_public_upload=False)
    base.update(over)
    return types.SimpleNamespace(**base)


def test_default_invocation_plans_and_sends_nothing(no_network, capsys):
    rc = blastp_online.blastp_online_command(_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "PLAN ONLY" in out
    assert "nothing was sent" in out
    assert no_network == []


def test_the_plan_discloses_what_would_leave(no_network, capsys):
    blastp_online.blastp_online_command(_args())
    out = capsys.readouterr().out
    assert "OUTBOUND SEQUENCE DISCLOSURE" in out
    assert blastp_online.NCBI_URL in out
    assert "2 protein(s), 7 aa" in out          # MKT + MAAA
    assert "sequence sha256" in out
    assert "UNSCOPED" in out


def test_submit_alone_is_refused(no_network, capsys):
    """One flag is a typo away from an accident. The second is where someone states the
    sequences may be disclosed."""
    rc = blastp_online.blastp_online_command(_args(submit=True))
    out = capsys.readouterr().out
    assert rc == 1
    assert "REFUSING" in out
    assert no_network == []


def test_both_flags_reach_the_network_call(no_network):
    """The gate must open when it is supposed to, or it is not a gate, it is a wall."""
    with pytest.raises(AssertionError, match="run_batches_online was reached"):
        blastp_online.blastp_online_command(
            _args(submit=True, confirm_public_upload=True))


def test_digest_is_stable_and_follows_the_sequences(no_network, capsys, monkeypatch):
    blastp_online.blastp_online_command(_args())
    first = [l for l in capsys.readouterr().out.splitlines() if "sequence sha256" in l][0]
    blastp_online.blastp_online_command(_args())
    again = [l for l in capsys.readouterr().out.splitlines() if "sequence sha256" in l][0]
    assert first == again
    monkeypatch.setattr("mamey.parsers.extract_cds_features",
                        lambda p: [_Feat("cds_1", "MKT"), _Feat("cds_2", "MAAC")])
    blastp_online.blastp_online_command(_args())
    changed = [l for l in capsys.readouterr().out.splitlines() if "sequence sha256" in l][0]
    assert changed != first


def test_the_flag_exists_on_the_parser_and_defaults_to_false():
    """A gate that the CLI cannot express is not reachable by a user."""
    from mamey.cli import build_parser
    ns = build_parser().parse_args(["blastp-online", "--package", "x"])
    assert ns.submit is False
    assert ns.confirm_public_upload is False
    ns2 = build_parser().parse_args(["blastp-online", "--package", "x", "--submit"])
    assert ns2.submit is True
    # `--run` is accepted too, so muscle memory from blastp-round does not silently do nothing
    ns3 = build_parser().parse_args(["blastp-online", "--package", "x", "--run"])
    assert ns3.submit is True
