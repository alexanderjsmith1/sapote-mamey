"""ClusteredNR RID runner: optional search settings.

curl is faked: each test reads the arguments submit() would send; no network calls."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/blastp_crawl/nr_rid_runner.py"
SID_FASTA = ">SID1046|JAAGLU010000047.1|region001|T1PKS|GT352_40840 len=60\nMSTNPKPQRK\n"
AS_FASTA = ">AS-683|NODE_1|region001|NRPS|ctg1_1 len=60\nMSTNPKPQRK\n"
ENV = ("RID_HITLIST", "RID_EXPECT", "RID_ENTREZ_QUERY", "RID_ENTREZ_SELF", "RID_ENTREZ_SELF_REGEX", "RID_ENTREZ_SELF_TEMPLATE")


def sent(tmp_path, monkeypatch, fasta, **env):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RID_DATABASE", "nr_cluster_seq")
    monkeypatch.setenv("RID_QUERIES", "_QUERIES_T")
    monkeypatch.setenv("RID_BASE", "_LANE_T")
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location("rid_runner_465_switches", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    calls = []
    monkeypatch.setattr(mod, "_curl", lambda a, t: calls.append(a) or "RID = R1\nRTOE = 30\n")
    assert mod.submit(fasta) == ("R1", 30)
    args = calls[0]
    return [args[i + 1] for i, x in enumerate(args) if x == "--data-urlencode"]


def test_defaults_send_the_request_unchanged(tmp_path, monkeypatch):
    fields = sent(tmp_path, monkeypatch, SID_FASTA)
    assert "HITLIST_SIZE=10" in fields
    assert not any(f.startswith(("EXPECT=", "ENTREZ_QUERY=")) for f in fields)
    assert fields[-1].startswith("QUERY@")


def test_hitlist_and_expect(tmp_path, monkeypatch):
    fields = sent(tmp_path, monkeypatch, AS_FASTA, RID_HITLIST="100", RID_EXPECT="1e-5")
    assert "HITLIST_SIZE=100" in fields and "EXPECT=1e-5" in fields


@pytest.mark.parametrize("bad", ["0", "ten", "-5"])
def test_bad_hitlist_refused(tmp_path, monkeypatch, bad):
    with pytest.raises(SystemExit):
        sent(tmp_path, monkeypatch, AS_FASTA, RID_HITLIST=bad)


def test_bad_expect_refused(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        sent(tmp_path, monkeypatch, AS_FASTA, RID_EXPECT="small")


def test_self_exclusion_only_for_matching_header(tmp_path, monkeypatch):
    sid = sent(tmp_path, monkeypatch, SID_FASTA, RID_ENTREZ_SELF="1")
    assert 'ENTREZ_QUERY=NOT "Streptomyces sp. SID1046"[orgn]' in sid
    as_ = sent(tmp_path, monkeypatch, AS_FASTA, RID_ENTREZ_SELF="1")
    assert not any(f.startswith("ENTREZ_QUERY=") for f in as_)


def test_self_exclusion_template_and_regex(tmp_path, monkeypatch):
    f = sent(tmp_path, monkeypatch, AS_FASTA, RID_ENTREZ_SELF="1", RID_ENTREZ_SELF_REGEX=r">\s*(AS-\d+)\|",
             RID_ENTREZ_SELF_TEMPLATE='NOT "{id}"[strain]')
    assert 'ENTREZ_QUERY=NOT "AS-683"[strain]' in f


def test_explicit_entrez_query_wins(tmp_path, monkeypatch):
    f = sent(tmp_path, monkeypatch, SID_FASTA, RID_ENTREZ_SELF="1", RID_ENTREZ_QUERY="Actinomycetota[orgn]")
    assert [x for x in f if x.startswith("ENTREZ_QUERY=")] == ["ENTREZ_QUERY=Actinomycetota[orgn]"]
