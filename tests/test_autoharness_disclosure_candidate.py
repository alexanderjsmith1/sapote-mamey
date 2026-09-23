from types import SimpleNamespace
import pytest
from mamey import blastp_autoharness as ah


def args(tmp_path, **changes):
    return SimpleNamespace(**(dict(package=str(tmp_path/"package"), strain="TEST", dry_run=False, submit=False, confirm_public_upload=False)|changes))


@pytest.mark.parametrize("submit,confirm,expected", [(False,False,0),(True,False,1)])
def test_command_never_enters_runner_without_both_flags(tmp_path,monkeypatch,submit,confirm,expected):
    calls=[]
    monkeypatch.setattr(ah,"run",lambda *a,**k:calls.append(k) or {})
    monkeypatch.setattr(ah,"status_line",lambda _: "done")
    monkeypatch.setattr(ah,"dry_run_report",lambda *a,**k:dict(strain="TEST",channel="nr",priority="af_first",n_bgcs=0,n_proteins=0,n_units=0,est_submit_span_min=0,worklist=[]))
    assert ah.auto_blastp_command(args(tmp_path,submit=submit,confirm_public_upload=confirm))==expected
    assert not calls and not (tmp_path/"package").exists()


def test_command_passes_explicit_ack_to_runner(tmp_path,monkeypatch):
    seen={}
    monkeypatch.setattr(ah,"run",lambda *a,**k:seen.update(k) or {})
    monkeypatch.setattr(ah,"status_line",lambda _: "done")
    assert ah.auto_blastp_command(args(tmp_path,submit=True,confirm_public_upload=True))==0
    assert seen["confirm_public_upload"] is True


def test_real_driver_refuses_before_state_creation(tmp_path,monkeypatch):
    monkeypatch.setattr(ah,"init_state",lambda *a,**k:pytest.fail("state initialized before acknowledgement"))
    with pytest.raises(ValueError,match="public.*upload|disclosure"):
        ah.run(tmp_path/"absent","TEST")


def test_direct_real_submit_factory_requires_ack(monkeypatch):
    with pytest.raises(ValueError,match="public.*upload|disclosure"):
        ah.default_submit_fn()


def test_acknowledged_submit_discloses_exact_batch(monkeypatch,capsys):
    import mamey.blastp_online as bo
    calls=[]
    def submit(batch,**kw):
        calls.append((batch,kw,capsys.readouterr().out))
        return SimpleNamespace(ok=True,rid="TEST_RID",reason="")
    monkeypatch.setattr(bo,"_submit_batch",submit)
    unit={"batch":[["protein_a","MAA"],["protein_b","MKKK"]]}
    result=ah.default_submit_fn(channel="clustered_nr",confirm_public_upload=True)(unit)
    assert result["ok"] and len(calls)==1
    text=calls[0][2]
    assert "OUTBOUND SEQUENCE DISCLOSURE" in text and "2 proteins" in text and "7 aa" in text
    import hashlib
    expected=hashlib.sha256(b"protein_a\x00MAA\nprotein_b\x00MKKK\n").hexdigest()
    assert expected in text and bo.NCBI_URL in text


def test_cli_flags_are_wired():
    from mamey.cli import build_parser
    parser=build_parser()
    args=parser.parse_args(["auto-blastp","--package","example","--strain","TEST"])
    assert not args.submit and not args.confirm_public_upload
    args=parser.parse_args(["auto-blastp","--package","example","--strain","TEST","--submit","--confirm-public-sequence-upload"])
    assert args.submit and args.confirm_public_upload


def test_dry_run_takes_precedence_over_submit(tmp_path,monkeypatch):
    monkeypatch.setattr(ah,"run",lambda *a,**k:pytest.fail("dry-run entered runner"))
    monkeypatch.setattr(ah,"dry_run_report",lambda *a,**k:dict(strain="TEST",channel="nr",priority="af_first",n_bgcs=0,n_proteins=0,n_units=0,est_submit_span_min=0,worklist=[]))
    assert ah.auto_blastp_command(args(tmp_path,submit=True,confirm_public_upload=True,dry_run=True))==0
