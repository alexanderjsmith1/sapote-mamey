# Synthetic regression inputs only.
"""Three small cli.py follow-ups.

- `domain-level` exited 0 for a REFUSED or SKIPPED receipt, so a script could not tell an
  occupied output folder or a mismatched source archive from a success. It now exits 2 for those
  and keeps 0 for OK and the two documented skips.
- `run` resolved where the strain ID came from (`StrainIdentity.source`) and dropped it. It is now
  passed into `RunContext.strain_id_source` and written to `<strain>_1_intake.json`, separate from
  the isolation source.
- The `write-narrative --force` help described a retired meaning; it now names the exit-4 refusal.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import mamey.domain_level as dl
from mamey import cli
from mamey.models import RunContext

BGC = {"bgc_id": "BGC001", "strain": "TEST", "assembly_locator": "NODE_1 region001",
       "products": "NRPS", "contig": "NODE_1", "start": 0, "end": 5000,
       "rank": 1, "kcb_top": "", "ab_score": 0, "af_score": 0}
DOMAINS = {"BGC001": [{"locus_tag": "ctg1_1", "start": 100, "end": 900, "strand": 1,
                       "domain_name": "AMP-binding", "domain_description": "full", "evalue": "1e-20"}]}


def _pkg(tmp_path, monkeypatch, digest=None, bgcs=(BGC,), domains=DOMAINS):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"input_zip_sha256": digest}), encoding="utf-8")
    monkeypatch.setattr(dl, "_top_bgcs_from_package", lambda *_a, **_k: ("TEST", list(bgcs)))
    monkeypatch.setattr(dl, "domains_from_gene_context", lambda *_a, **_k: domains)
    monkeypatch.setattr(dl, "domains_from_source_zip", lambda *_a, **_k: domains)
    monkeypatch.setattr(dl, "modules_from_source_zip", lambda *_a, **_k: {})
    return pkg


def _dl(pkg, out, *extra):
    return cli.main(["domain-level", "--package", str(pkg), "--top-n", "1", "--out", str(out), *extra])


def test_domain_level_success_is_0_and_an_occupied_folder_is_2(tmp_path, monkeypatch):
    pkg = _pkg(tmp_path, monkeypatch)
    out = tmp_path / "out"
    assert _dl(pkg, out) == 0
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    assert _dl(pkg, out, "--emit-figures") == 2
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before


def test_domain_level_mismatched_source_archive_is_2(tmp_path, monkeypatch):
    pkg = _pkg(tmp_path, monkeypatch, digest="0" * 64)
    z = tmp_path / "other.zip"
    z.write_bytes(b"another genome")
    assert _dl(pkg, tmp_path / "out", "--source-antismash", str(z)) == 2
    receipt = json.loads((tmp_path / "out" / "domain_level_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "SKIPPED" and receipt["reason"].startswith("SOURCE_ZIP_DIGEST_MISMATCH")


@pytest.mark.parametrize("case", ["no_domain_context", "no_eligible_bgcs"])
def test_domain_level_documented_skips_stay_0(tmp_path, monkeypatch, case):
    if case == "no_domain_context":
        pkg = _pkg(tmp_path, monkeypatch, domains={})
    else:
        pkg = _pkg(tmp_path, monkeypatch, bgcs=())
    out = tmp_path / "out"
    assert _dl(pkg, out) == 0
    receipt = json.loads((out / "domain_level_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "SKIPPED"


def test_domain_level_missing_manifest_is_2(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    assert _dl(pkg, tmp_path / "out") == 2


def _capture_run(monkeypatch):
    seen = {}

    def fake_run_one_strain(**kw):
        seen.update(kw)
        return {"status": "MAMEY_COMPLETE", "written": True, "issues": []}

    monkeypatch.setattr(cli, "run_one_strain", fake_run_one_strain)
    return seen


@pytest.mark.parametrize("strain_args, expected", [(["--strain", "Synthetic_sp_TESTID"], "supplied"),
                                                   ([], None)])
def test_run_passes_where_the_strain_id_came_from(tmp_path, monkeypatch, strain_args, expected,
                                                  synthetic_single_contig_admitted_zip):
    seen = _capture_run(monkeypatch)
    try:
        cli.main(["run", "--input-zip", str(synthetic_single_contig_admitted_zip),
                  "--outdir", str(tmp_path / "runs"),
                  "--source", "soil", *strain_args])
    except SystemExit:
        pass
    assert seen, "run_one_strain was not reached"
    assert seen["source"] == "soil"
    if expected:
        assert seen["strain_id_source"] == expected
    else:
        assert seen["strain_id_source"] in {"archive", "zip_stem"}


def test_run_context_keeps_strain_id_source_apart_from_isolation_source():
    ctx = RunContext(strain_id="X", display_name="X", version="v", analysis_mode="gold",
                     input_zip="x.zip", outdir=".", source="soil", strain_id_source="zip_stem")
    assert (ctx.source, ctx.strain_id_source) == ("soil", "zip_stem")
    assert RunContext(strain_id="X", display_name="X", version="v", analysis_mode="gold",
                      input_zip="x.zip", outdir=".").strain_id_source == "not recorded"


def test_write_narrative_force_help_names_the_exit_4_refusal():
    sub = cli.build_parser()._subparsers._group_actions[0].choices["write-narrative"]
    text = " ".join(sub.format_help().split())
    assert "exit 4" in text and "RESERVED" not in text
