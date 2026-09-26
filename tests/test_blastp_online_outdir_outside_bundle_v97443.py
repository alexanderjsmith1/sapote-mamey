"""v9.7.443: `mamey blastp-online` refuses to write its panel inside the code bundle.

The panel defaults to the current directory, and tools run from the bundle root, so a submitting
run with no --outdir wrote its CSV and cluster-reads JSON into the sealed bundle. The refusal sits
after the plan-only exit (which writes nothing) and before the NCBI submission, so a finished web
run is never thrown away at write time.
"""
import os
import types
from pathlib import Path

import pytest

from mamey import blastp_online

ROOT = Path(__file__).resolve().parents[1]


class _Feat:
    def __init__(self, locus_tag, translation):
        self.locus_tag, self.translation = locus_tag, translation
        self.qualifiers = {}


@pytest.fixture
def spy(monkeypatch):
    calls = []
    monkeypatch.setattr("mamey.parsers.extract_cds_features",
                        lambda p: [_Feat("cds_1", "MKTAYIAK"), _Feat("cds_2", "MSTNPKPQR")])
    monkeypatch.setattr(blastp_online, "run_batches_online",
                        lambda batches, **kw: calls.append(batches) or [])
    return calls


def _args(**over):
    base = dict(package="stub", bgc=None, region=None, database="nr", evalue="1e-5",
                batch_size=10, outdir=None, crosswalk=None, kcb_top=None, kcb_coverage_genes=None,
                submit=True, confirm_public_upload=True)
    base.update(over)
    return types.SimpleNamespace(**base)


def test_submitting_run_from_the_bundle_root_is_refused_before_the_network(spy, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    assert blastp_online.blastp_online_command(_args()) == 1
    assert spy == []  # nothing was sent
    assert "OUTPUT_INSIDE_BUNDLE" in capsys.readouterr().out


def test_plan_only_run_from_the_bundle_root_is_not_refused(spy, monkeypatch, capsys):
    monkeypatch.chdir(ROOT)
    assert blastp_online.blastp_online_command(_args(submit=False, confirm_public_upload=False)) == 0
    assert "OUTPUT_INSIDE_BUNDLE" not in capsys.readouterr().out


def test_an_outdir_outside_the_bundle_reaches_the_network(spy, tmp_path):
    blastp_online.blastp_online_command(_args(outdir=str(tmp_path)))
    assert len(spy) == 1
