"""v9.7.196 fix — CLI-level end-to-end guard for Patch B. The unit tests called _scope_feats
directly and never exercised blastp_online_command -> extract_cds_features -> _find_crosswalk, so a
NameError (Path out of scope) and a ValueError (package dir has no proteins) shipped green. These
tests reach the CLI path and assert it does not crash on the two invocations the audit reproduced."""
import os
from types import SimpleNamespace

import pytest

from mamey.blastp_online import _derive_kcb_anchor, _find_crosswalk, blastp_online_command
from mamey import blastp_online as bo

_ZIP = "/tmp/as421_region.zip"
_PKG = "/data/mamey-local/work/strain_intake/runs_v184/AS-421/package"


def test_find_crosswalk_no_nameerror_on_zip():
    """_find_crosswalk must not NameError (the Path-out-of-scope crash) on a ZIP path."""
    args = SimpleNamespace(package="/tmp/does_not_matter.zip", bgc="BGC001", crosswalk=None, region=None)
    # returns None (no crosswalk) but must not raise NameError
    assert _find_crosswalk(args) is None


@pytest.mark.skipif(not os.path.isdir(_PKG), reason="AS-421 package not present")
def test_command_package_dir_refuses_cleanly_not_crash():
    """--package <pkg_dir> --bgc: a package dir has no proteins → the command must refuse (rc=1),
    not crash with ValueError."""
    args = SimpleNamespace(package=_PKG, bgc="BGC041", crosswalk=None, region=None,
                           database="nr", evalue="1e-5", batch_size=10, outdir="/tmp/bo_e2e")
    rc = blastp_online_command(args)
    assert rc == 1  # clean refusal, not an exception


def test_find_crosswalk_explicit_dir(tmp_path):
    """--crosswalk pointing at a dir with a crosswalk CSV resolves it."""
    csv = tmp_path / "AS-x_2b_bgc_crosswalk.csv"
    csv.write_text("bgc_id,contig,start,end\nBGC001,NODE_1,100,200\n")
    args = SimpleNamespace(package="/tmp/x.zip", bgc="BGC001", crosswalk=str(tmp_path), region=None)
    xw = _find_crosswalk(args)
    assert xw is not None and "BGC001" in xw


def test_invalid_crosswalk_window_is_a_typed_scope_hold():
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 cannot widen to a contig."""
    feature = SimpleNamespace(contig="NODE_1_length_1000_cov_20", start=120, end=180)
    crosswalk = {
        "BGC001": {"contig": "NODE_1_length_1000_cov_20", "start": "bad", "end": "200"}
    }
    with pytest.raises(bo.BlastpScopeError, match="BLASTP_SCOPE_HOLD"):
        bo._scope_feats([feature], bgc="BGC001", crosswalk=crosswalk)


def test_valid_crosswalk_window_preserves_exact_scoping():
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 returns only its window."""
    inside = SimpleNamespace(contig="NODE_1_length_1000_cov_20", start=120, end=180)
    outside = SimpleNamespace(contig="NODE_1_length_1000_cov_20", start=300, end=380)
    crosswalk = {
        "BGC001": {"contig": "NODE_1_length_1000_cov_20", "start": "100", "end": "200"}
    }
    assert bo._scope_feats([inside, outside], bgc="BGC001", crosswalk=crosswalk) == [inside]


def test_cli_refuses_unresolved_bgc_instead_of_submitting_unscoped(monkeypatch, capsys):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 must resolve before submit."""
    feature = SimpleNamespace(
        contig="NODE_1_length_1000_cov_20", start=120, end=180,
        locus_tag="gene_1", translation="M" * 100,
    )
    monkeypatch.setattr("mamey.parsers.extract_cds_features", lambda _path: [feature])
    monkeypatch.setattr(bo, "_find_crosswalk", lambda _args: {
        "BGC002": {"contig": "NODE_2_length_1000_cov_20", "start": "100", "end": "200"}
    })
    called = {"submit": False}

    def refuse_network(*_args, **_kwargs):
        called["submit"] = True
        raise AssertionError("unresolved scope reached network submission")

    monkeypatch.setattr(bo, "run_batches_online", refuse_network)
    args = SimpleNamespace(
        package="fixture.zip", bgc="BGC001", region=None, crosswalk=None,
        database="nr", evalue="1e-5", batch_size=10,
    )
    assert blastp_online_command(args) == 1
    assert called["submit"] is False
    assert "REFUSING" in capsys.readouterr().out


def test_unreadable_existing_crosswalk_is_a_typed_hold(tmp_path, monkeypatch):
    crosswalk = tmp_path / "AS-x_2b_bgc_crosswalk.csv"
    crosswalk.write_text("bgc_id,contig,start,end\nBGC001,NODE_1,100,200\n")
    original_open = open

    def refuse_crosswalk(path, *args, **kwargs):
        if os.fspath(path) == os.fspath(crosswalk):
            raise PermissionError("fixture denies crosswalk read")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", refuse_crosswalk)
    args = SimpleNamespace(package="/tmp/x.zip", bgc="BGC001", crosswalk=str(crosswalk))
    with pytest.raises(bo.BlastpCrosswalkError, match="BLASTP_CROSSWALK_HOLD"):
        _find_crosswalk(args)


def test_missing_inferred_crosswalk_remains_absence(tmp_path):
    args = SimpleNamespace(package=str(tmp_path / "input.zip"), bgc="BGC001", crosswalk=None)
    assert _find_crosswalk(args) is None


def test_invalid_kcb_coverage_is_a_typed_hold(tmp_path):
    profile = tmp_path / "AS-x_3_mibig_profile.csv"
    profile.write_text(
        "bgc_id,dominant_mibig_compound,dominant_distinct_query_genes\n"
        "BGC001,example class,not-a-number\n",
        encoding="utf-8",
    )
    args = SimpleNamespace(package=str(tmp_path), crosswalk=None, bgc="BGC001",
                           kcb_top=None, kcb_coverage_genes=None)
    with pytest.raises(bo.BlastpKcbAnchorError, match="BLASTP_KCB_ANCHOR_HOLD"):
        _derive_kcb_anchor(args)


def test_missing_kcb_profile_remains_undetermined(tmp_path):
    args = SimpleNamespace(package=str(tmp_path), crosswalk=None, bgc="BGC001",
                           kcb_top=None, kcb_coverage_genes=None)
    assert _derive_kcb_anchor(args) == ("", None)


def test_cli_refuses_kcb_hold_before_network_or_output(tmp_path, monkeypatch, capsys):
    feature = SimpleNamespace(
        contig="NODE_1_length_1000_cov_20", start=120, end=180,
        locus_tag="gene_1", translation="M" * 100,
    )
    monkeypatch.setattr("mamey.parsers.extract_cds_features", lambda _path: [feature])
    monkeypatch.setattr(bo, "_find_crosswalk", lambda _args: {
        "BGC001": {"contig": feature.contig, "start": "100", "end": "200"}
    })
    monkeypatch.setattr(
        bo, "_derive_kcb_anchor",
        lambda _args: (_ for _ in ()).throw(bo.BlastpKcbAnchorError("BLASTP_KCB_ANCHOR_HOLD: injected")),
    )
    called = {"submit": False}

    def refuse_network(*_args, **_kwargs):
        called["submit"] = True
        raise AssertionError("KCB hold reached network")

    monkeypatch.setattr(bo, "run_batches_online", refuse_network)
    args = SimpleNamespace(
        package="fixture.zip", bgc="BGC001", region=None, crosswalk=None,
        database="nr", evalue="1e-5", batch_size=10, outdir=str(tmp_path / "out"),
    )
    assert blastp_online_command(args) == 1
    assert called["submit"] is False
    assert not (tmp_path / "out").exists()
    assert "BLASTP_KCB_ANCHOR_HOLD" in capsys.readouterr().out
