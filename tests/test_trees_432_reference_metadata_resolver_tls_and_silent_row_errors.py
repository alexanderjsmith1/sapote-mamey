"""TREES_432_reference_metadata_resolver_tls_and_silent_row_errors — a failed fetch is an ERROR row
with empty metadata cells AND a non-zero exit with a count; --continue-on-error keeps exit 0; the TLS
context honours the documented env override. No network: _http_get is monkeypatched."""
import csv
import ssl
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import resolve_reference_metadata as m  # noqa: E402

GB_OK = (
    "LOCUS       CP129614   1 bp    DNA     linear   BCT\n"
    "FEATURES             Location/Qualifiers\n"
    "     source          1..100\n"
    '                     /organism="Nocardia sp. PE-7"\n'
    '                     /strain="PE-7"\n'
    '                     /isolation_source="an LDPE film in soil"\n'
    '                     /country="South Korea: Jeonju"\n'
    "     gene            1..1000\n"
)


@pytest.fixture
def worklist(tmp_path):
    p = tmp_path / "work.tsv"
    p.write_text("identifier\tchromosome_accession\tstrain\n"
                 "GOOD\tCP129614.1\tPE-7\n"
                 "BAD\tNZ_BROKEN01.1\tX-1\n")
    return p


def _tls_fail(*a, **k):
    raise ssl.SSLCertVerificationError(
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain")


def _read(path):
    return list(csv.DictReader(open(path, newline=""), delimiter="\t"))


def test_all_rows_error_exits_nonzero_and_never_says_not_recorded(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(m, "_http_get", _tls_fail)
    monkeypatch.setattr(m.time, "sleep", lambda *_: None)
    out = tmp_path / "t.tsv"
    rc = m.main(["--accessions", "A1.1", "B2.1", "--out", str(out)])
    assert rc == 1
    rows = _read(out)
    assert [r["verification_status"] for r in rows] == ["ERROR", "ERROR"]
    for r in rows:
        assert r["isolation_source"] == "" and r["location"] == ""   # empty, NOT 'Not recorded'
        assert "CERTIFICATE_VERIFY_FAILED" in r["unresolved_issue"]
    err = capsys.readouterr().err
    assert "2/2 row(s) ERROR" in err and "SSL_CERT_FILE" in err  # count + keychain hint surfaced


def test_partial_failure_exits_nonzero_with_count(monkeypatch, tmp_path, worklist, capsys):
    def get(url, timeout=30):
        if "CP129614.1" in url and "db=nuccore" in url:
            return GB_OK
        raise OSError("connection reset")
    monkeypatch.setattr(m, "_http_get", get)
    monkeypatch.setattr(m, "fetch_biosample_for", lambda *a, **k: {})
    monkeypatch.setattr(m.time, "sleep", lambda *_: None)
    out = tmp_path / "t.tsv"
    rc = m.main(["--tsv", str(worklist), "--strain-col", "strain", "--out", str(out)])
    assert rc == 1
    rows = {r["identifier"]: r for r in _read(out)}
    assert rows["GOOD"]["verification_status"] == "STRAIN_CONFIRMED"
    assert rows["BAD"]["verification_status"] == "ERROR" and rows["BAD"]["isolation_source"] == ""
    assert "1/2 row(s) ERROR" in capsys.readouterr().err


def test_continue_on_error_exits_zero_but_still_counts(monkeypatch, tmp_path, worklist, capsys):
    monkeypatch.setattr(m, "_http_get", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    monkeypatch.setattr(m.time, "sleep", lambda *_: None)
    out = tmp_path / "t.tsv"
    assert m.main(["--tsv", str(worklist), "--continue-on-error", "--out", str(out)]) == 0
    assert all(r["verification_status"] == "ERROR" for r in _read(out))
    assert "2/2 row(s) ERROR" in capsys.readouterr().err
    out2 = tmp_path / "t2.tsv"
    assert m.main(["--tsv", str(worklist), "--allow-partial", "--out", str(out2)]) == 0  # alias


def test_biosample_transport_failure_is_an_error_row_not_a_value(monkeypatch, tmp_path):
    def get(url, timeout=30):
        if "db=nuccore" in url:
            return GB_OK.replace('/strain="PE-7"\n', '/strain="PE-7"\n'
                                 '                     /db_xref="BioSample:SAMN1"\n')
        raise OSError("biosample down")
    monkeypatch.setattr(m, "_http_get", get)
    monkeypatch.setattr(m.time, "sleep", lambda *_: None)
    out = tmp_path / "t.tsv"
    assert m.main(["--accessions", "CP129614.1", "--out", str(out)]) == 1
    row = _read(out)[0]
    assert row["verification_status"] == "ERROR" and row["isolation_source"] == ""


def test_certificate_failure_does_not_retry(monkeypatch):
    n = {"calls": 0}

    def get(url, timeout=30):
        n["calls"] += 1
        _tls_fail()
    monkeypatch.setattr(m, "_http_get", get)
    monkeypatch.setattr(m.time, "sleep", lambda *_: None)
    with pytest.raises(RuntimeError, match="SSL_CERT_FILE"):
        m.efetch_source("A1.1")
    assert n["calls"] == 1


def test_ssl_ctx_env_override_and_default(monkeypatch, tmp_path):
    seen = {}

    def fake_ctx(cafile=None, **k):
        seen["cafile"] = cafile
        c = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        def _record_load(*a, **kw):
            seen.setdefault("loaded", []).append(kw.get("cafile") or a)
        monkeypatch.setattr(c, "load_verify_locations", _record_load, raising=False)
        return c
    monkeypatch.setattr(m.ssl, "create_default_context", fake_ctx)
    monkeypatch.delenv("SAPOTE_EFETCH_INSECURE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    pem = tmp_path / "ca.pem"; pem.write_text("x")
    monkeypatch.setenv("SSL_CERT_FILE", str(pem))
    m._ssl_ctx()
    assert seen["cafile"] == str(pem)            # documented override wins
    seen.clear()
    monkeypatch.delenv("SSL_CERT_FILE")
    m._ssl_ctx()
    assert seen["cafile"] is None                # system store by default
    try:
        import certifi  # noqa: F401
        assert seen.get("loaded")                # certifi merged in when present
    except ImportError:
        pass
