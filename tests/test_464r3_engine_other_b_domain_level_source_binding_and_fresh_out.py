# Synthetic regression inputs only.
"""domain-level binds the source archive to the package digest and refuses an occupied --out.

Before: any archive that shared contig names was joined to the package by coordinates, the receipt
kept only its basename, and a rerun replaced earlier tables and receipts in place.
"""
from __future__ import annotations

import hashlib
import json

import mamey.domain_level as dl

BGC = {"bgc_id": "BGC001", "strain": "TEST", "assembly_locator": "NODE_1 region001",
       "products": "NRPS", "contig": "NODE_1", "start": 0, "end": 5000,
       "rank": 1, "kcb_top": "", "ab_score": 0, "af_score": 0}
DOMAINS = {"BGC001": [{"locus_tag": "ctg1_1", "start": 100, "end": 900, "strand": 1,
                       "domain_name": "AMP-binding", "domain_description": "full", "evalue": "1e-20"}]}


def _pkg(tmp_path, monkeypatch, digest):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"input_zip_sha256": digest}), encoding="utf-8")
    monkeypatch.setattr(dl, "_top_bgcs_from_package", lambda *_a, **_k: ("TEST", [BGC]))
    monkeypatch.setattr(dl, "domains_from_gene_context", lambda *_a, **_k: DOMAINS)
    calls = []

    def fake_source(path, bgcs):
        calls.append(str(path))
        return DOMAINS

    monkeypatch.setattr(dl, "domains_from_source_zip", fake_source)
    monkeypatch.setattr(dl, "modules_from_source_zip", lambda *_a, **_k: {})
    return pkg, calls


def _zip(tmp_path, payload=b"archive-bytes"):
    z = tmp_path / "source.zip"
    z.write_bytes(payload)
    return z, hashlib.sha256(payload).hexdigest()


def test_matching_archive_is_used_and_its_digest_recorded(tmp_path, monkeypatch):
    z, digest = _zip(tmp_path)
    pkg, calls = _pkg(tmp_path, monkeypatch, digest)
    receipt = dl.run_domain_level(pkg, source_antismash=z, top_n=1, outdir=tmp_path / "out")
    assert receipt["status"] == "OK" and receipt["mode"] == "full_source"
    assert receipt["source_binding"] == "MATCHES_MANIFEST_INPUT_ZIP_SHA256"
    assert receipt["source_antismash_sha256"] == digest
    assert calls == [str(z)]


def test_mismatched_archive_is_held_not_joined(tmp_path, monkeypatch):
    z, _ = _zip(tmp_path)
    pkg, calls = _pkg(tmp_path, monkeypatch, "0" * 64)
    out = tmp_path / "out"
    receipt = dl.run_domain_level(pkg, source_antismash=z, top_n=1, outdir=out)
    assert receipt["status"] == "SKIPPED"
    assert receipt["source_binding"] == "SOURCE_ZIP_DIGEST_MISMATCH"
    assert calls == []
    assert (out / "DOMAIN_LEVEL_SOURCE_ZIP_MISMATCH.md").is_file()
    assert not (out / "domain_rows_long.csv").exists()


def test_unbound_package_digest_does_not_use_the_archive(tmp_path, monkeypatch):
    z, _ = _zip(tmp_path)
    pkg, calls = _pkg(tmp_path, monkeypatch, None)
    receipt = dl.run_domain_level(pkg, source_antismash=z, top_n=1, outdir=tmp_path / "out")
    assert calls == []
    assert receipt["mode"] == "limited_gene_context"
    assert receipt["source_binding"] == "SOURCE_ZIP_DIGEST_UNBOUND"
    assert any("SOURCE_ZIP_DIGEST_UNBOUND" in w for w in receipt["warnings"])


def test_missing_archive_is_reported(tmp_path, monkeypatch):
    pkg, calls = _pkg(tmp_path, monkeypatch, "0" * 64)
    receipt = dl.run_domain_level(pkg, source_antismash=tmp_path / "absent.zip", top_n=1,
                                  outdir=tmp_path / "out")
    assert calls == []
    assert receipt["source_binding"] == "SOURCE_ZIP_UNAVAILABLE"


def test_occupied_output_folder_is_refused_and_kept(tmp_path, monkeypatch):
    pkg, _ = _pkg(tmp_path, monkeypatch, None)
    out = tmp_path / "out"
    first = dl.run_domain_level(pkg, top_n=1, outdir=out)
    assert first["status"] == "OK"
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    second = dl.run_domain_level(pkg, top_n=1, outdir=out)
    assert second["status"] == "REFUSED"
    assert "domain_level_receipt.json" in second["reason"]
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before


def test_a_prior_skip_card_also_blocks_a_rerun(tmp_path, monkeypatch):
    pkg, _ = _pkg(tmp_path, monkeypatch, None)
    out = tmp_path / "out"
    out.mkdir()
    (out / "DOMAIN_LEVEL_SKIPPED_NO_GBK.md").write_text("earlier\n", encoding="utf-8")
    assert dl.run_domain_level(pkg, top_n=1, outdir=out)["status"] == "REFUSED"
    assert (out / "DOMAIN_LEVEL_SKIPPED_NO_GBK.md").read_text(encoding="utf-8") == "earlier\n"


def test_parent_traversal_out_has_its_own_wording(tmp_path, monkeypatch):
    pkg, _ = _pkg(tmp_path, monkeypatch, None)
    (tmp_path / "x").mkdir()
    out = tmp_path / "x" / ".." / "out"
    receipt = dl.run_domain_level(pkg, top_n=1, outdir=out)
    assert receipt["status"] == "REFUSED"
    assert receipt["reason"] == ("refused: --out contains '..' (parent traversal is not admitted); "
                                 "choose a direct path")
    assert "not fresh" not in receipt["reason"]
    assert not (tmp_path / "out").exists()
