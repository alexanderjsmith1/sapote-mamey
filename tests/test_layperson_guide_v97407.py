from __future__ import annotations

from argparse import Namespace
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

import mamey.layperson_guide as guide
from mamey.crosswalk import enrich_bgc_crosswalk
from mamey.figure_theme import CLAIM_SAFETY
from mamey.models import BGCRecord
from mamey.sapote_markdown import parse_path, validate_model


def _package(tmp_path: Path, *, node: str = "NODE_1_length_20000_cov_50") -> Path:
    package = tmp_path / "package"
    package.mkdir()
    manifest = {
        "strain_id": "DEMO_STRAIN",
        "taxonomy": "Synthetic sp.",
        "source": "fixture",
        "mode": "gold",
        "terminal_status": "MAMEY_COMPLETE",
        "assembly": {
            "genome_bp": 2_000_000,
            "contigs": 2,
            "n50": 1_500_000,
            "quality": {"caveat": "One region touches a sequence boundary."},
        },
        "bgc_counts": {"raw": 1, "corrected": 0.5, "interior_pct": 0, "assembly_tier": "VERY_POOR"},
        "bioassay_scope": {"assay_data_state": "NOT_PROVIDED"},
        "bioactivity": {"metadata_state": "NOT_SUPPLIED"},
        "recommended_next_steps": [],
        "bgcs": [{
            "bgc_id": "BGC001",
            "node_id": node,
            "contig": node,
            "antismash_region": "region001",
            "region_number": 1,
            "products": ["NRPS"],
            "edge_status": "Edge",
            "length_kb": 9.0,
            "corrected_rank": 1,
            "kcb_evidence_state": "UNKNOWN_KCB",
            "kcb_top": None,
        }],
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return package


def _mutate(package: Path, edit) -> dict:
    path = package / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    edit(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_render_uses_complete_identity_and_canonical_claim_ceiling(tmp_path: Path) -> None:
    package = _package(tmp_path)
    text = guide.render_markdown(package)
    identity = "DEMO_STRAIN / NODE_1_length_20000_cov_50 / region001 / BGC001"
    assert identity in text
    assert CLAIM_SAFETY in text
    assert "product is not established" in text
    assert "MIBiG similarity" not in text
    source = tmp_path / "guide.md"
    source.write_text(text, encoding="utf-8")
    model = parse_path(source)
    assert validate_model(model, require_assets=True).ok


def test_render_fails_closed_when_complete_identity_is_unavailable(tmp_path: Path) -> None:
    package = _package(tmp_path, node="")
    with pytest.raises(ValueError, match="exact-locus identity is fail-closed"):
        guide.render_markdown(package)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("node_id", "NODE_1", "not a full node-or-contig"),
        ("node_id", "ctg1", "producer normalization"),
        ("antismash_region", "region1", "required regionNNN"),
        ("antismash_region", "unknown", "exact-locus identity is fail-closed"),
        ("bgc_id", "?", "exact-locus identity is fail-closed"),
    ],
)
def test_strict_exact_locus_owner_rejects_invalid_parts(
    tmp_path: Path, field: str, value: str, match: str
) -> None:
    package = _package(tmp_path)
    def edit(manifest: dict) -> None:
        manifest["bgcs"][0][field] = value
        if field == "node_id" and value == "NODE_1":
            manifest["bgcs"][0]["contig"] = value
    _mutate(package, edit)
    with pytest.raises(ValueError, match=match):
        guide.render_markdown(package)


def test_conflicting_full_node_and_contig_fails_closed(tmp_path: Path) -> None:
    package = _package(tmp_path)
    _mutate(package, lambda manifest: manifest["bgcs"][0].update(contig="other_full_contig"))
    with pytest.raises(guide.LaypersonGuideError, match="EXACT_LOCUS_IDENTITY_REQUIRED"):
        guide.render_markdown(package)


def test_human_guide_specific_validator_rejects_bare_alias(tmp_path: Path) -> None:
    package = _package(tmp_path)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    text = guide.render_markdown(package) + "\nThis extra sentence names BGC001 alone.\n"
    with pytest.raises(guide.LaypersonGuideError, match="BARE_BGC_ALIAS_FORBIDDEN"):
        guide.validate_locus_mentions(text, strain="DEMO_STRAIN", rows=manifest["bgcs"])


def test_unstructured_package_caveat_is_withheld_not_disclaimed(tmp_path: Path) -> None:
    package = _package(tmp_path)
    _mutate(
        package,
        lambda manifest: manifest["assembly"]["quality"].update(
            caveat="BGC999 is genuinely novel and makes ExampleDrug."
        ),
    )
    text = guide.render_markdown(package, top_n=1)
    assert "BGC999" not in text
    assert "ExampleDrug" not in text
    assert "PRESENT_BUT_NOT_LOCUS_BOUND" in text


@pytest.mark.parametrize(
    ("state", "top", "locator", "expected"),
    [
        ("KNOWNCLUSTERBLAST_OBSERVED", "ExampleCompound", "results/knowncluster.txt", "MATCH:"),
        ("KNOWNCLUSTERBLAST_OBSERVED", "ExampleCompound", None, "PARTIAL:"),
        ("CLUSTERBLAST_FALLBACK_OBSERVED", "ExampleCompound", None, "PARTIAL:"),
        ("UNKNOWN_KCB", "ExampleCompound", "results/knowncluster.txt", "MISSING:"),
        ("CANNOT_FROM_PACKAGE", "ExampleCompound", "results/knowncluster.txt", "CANNOT_FROM_PACKAGE:"),
        ("UNRECOGNIZED_STATE", "ExampleCompound", "results/knowncluster.txt", "CANNOT_FROM_PACKAGE:"),
    ],
)
def test_comparison_states_do_not_collapse_or_echo_dynamic_label(
    state: str, top: str, locator: str | None, expected: str
) -> None:
    text = guide._comparison_text(
        {"kcb_evidence_state": state, "kcb_top": top, "source_kcb_locator": locator, "kcb_cumulative": 87.7}
    )
    assert text.startswith(expected)
    assert top not in text
    assert "87.7" not in text


def test_unknown_class_label_is_withheld_and_not_promoted(tmp_path: Path) -> None:
    package = _package(tmp_path)
    _mutate(package, lambda manifest: manifest["bgcs"][0].update(products=["ExampleDrug"]))
    text = guide.render_markdown(package)
    assert "ExampleDrug" not in text
    assert "Unreviewed package label withheld" in text


def test_dynamic_claim_bearing_fields_are_not_echoed(tmp_path: Path) -> None:
    package = _package(tmp_path)
    def edit(manifest: dict) -> None:
        manifest["terminal_status"] = "ExampleDrug produced and active"
        manifest["bioassay_scope"]["assay_data_state"] = "ExampleDrug kills Candida"
        manifest["assembly"]["quality"]["caveat"] = "This region is genuinely novel."
        manifest["bgcs"][0].update(
            products=["ExampleDrug"],
            kcb_evidence_state="KNOWNCLUSTERBLAST_OBSERVED",
            kcb_top="ExampleDrug",
            source_kcb_locator="results/knowncluster.txt",
        )
    _mutate(package, edit)
    text = guide.render_markdown(package)
    for unsafe in ("ExampleDrug", "kills Candida", "genuinely novel"):
        assert unsafe not in text


def test_missing_interior_percent_has_no_percent_suffix(tmp_path: Path) -> None:
    package = _package(tmp_path)
    _mutate(package, lambda manifest: manifest["bgc_counts"].pop("interior_pct"))
    text = guide.render_markdown(package)
    assert "Not supplied%" not in text
    assert "Not supplied" in text


@pytest.mark.parametrize("bgcs", [[], ["not-a-row"]])
def test_empty_or_invalid_bgc_list_is_a_typed_package_gap(tmp_path: Path, bgcs: list) -> None:
    package = _package(tmp_path)
    _mutate(package, lambda manifest: manifest.update(bgcs=bgcs))
    with pytest.raises(guide.LaypersonGuideError, match="PACKAGE_BGC_DATA_GAP"):
        guide.render_markdown(package)


def test_mamey_complete_is_described_as_mechanical_not_scientific(tmp_path: Path) -> None:
    text = guide.render_markdown(_package(tmp_path))
    assert "MAMEY_COMPLETE: mechanical package validation completed" in text
    assert "this is not scientific acceptance" in text


def test_markdown_cli_is_post_seal_and_additive(tmp_path: Path) -> None:
    package = _package(tmp_path)
    before = (package / "manifest.json").read_bytes()
    outdir = tmp_path / "rendered"
    result = guide.layperson_command(Namespace(package=str(package), outdir=str(outdir), format="md", top_n=5))
    assert result == 0
    assert (outdir / "DEMO_STRAIN_LAYPERSON_GUIDE.md").is_file()
    assert (outdir / "DEMO_STRAIN_LAYPERSON_GUIDE_RECEIPT.json").is_file()
    assert (package / "manifest.json").read_bytes() == before


def test_cli_writes_typed_refusal_receipt_for_incomplete_identity(tmp_path: Path) -> None:
    package = _package(tmp_path, node="NODE_1")
    outdir = tmp_path / "refused"
    result = guide.layperson_command(
        Namespace(package=str(package), outdir=str(outdir), format="both", top_n=5)
    )
    assert result == 2
    receipt = json.loads((outdir / "DEMO_STRAIN_LAYPERSON_GUIDE_RECEIPT.json").read_text())
    assert receipt["status"] == "CANNOT_FROM_PACKAGE"
    assert receipt["outputs"] == []
    assert "not a full node-or-contig identifier" in receipt["error"]
    assert not list(outdir.glob("*.md"))
    assert not list(outdir.glob("*.docx"))


def test_future_figure_adapter_reuses_canonical_footer(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = {}

    def fake(fig: object, *, provenance: str, authority: str) -> None:
        observed.update(fig=fig, provenance=provenance, authority=authority)

    monkeypatch.setattr(guide, "add_claim_safety_footer", fake)
    figure = object()
    guide.add_guide_figure_footer(figure, manifest_sha256="abc123")
    assert observed == {"fig": figure, "provenance": "manifest sha256 abc123", "authority": "Post-seal guide"}
def test_renderer_uses_only_sealed_package_files(tmp_path):
    package = _package(tmp_path)
    manifest_before = (package / "manifest.json").read_bytes()
    text = guide.render_markdown(package)
    assert "DEMO_STRAIN / NODE_1_length_20000_cov_50 / region001 / BGC001" in text
    assert "product is not established" in text
    assert "MISSING: the expected comparison field is absent or unbound" in text
    assert (package / "manifest.json").read_bytes() == manifest_before


def _native_row(contig: str, alias: str, rank: int) -> dict:
    record = BGCRecord(
        bgc_id=alias,
        contig=contig,
        region_number=1,
        start=1,
        end=1000,
        contig_length=1000,
        products=["NRPS"],
    )
    enrich_bgc_crosswalk(record, "unused.region001.gbk")
    row = asdict(record)
    row["corrected_rank"] = rank
    return row


def _native_package(tmp_path: Path, rows: list[dict]) -> Path:
    first = rows[0]
    root = tmp_path / (
        f"SYNTHETIC-001__{first['contig']}__{first['antismash_region']}__"
        f"{first['bgc_id']}"
    )
    root.mkdir()
    manifest = {
        "strain_id": "SYNTHETIC-001",
        "taxonomy": "Synthetic sp.",
        "source": "fixture",
        "mode": "gold",
        "terminal_status": "MAMEY_COMPLETE",
        "assembly": {"genome_bp": 2_000_000, "contigs": 2, "n50": 1_500_000},
        "bgc_counts": {"raw": len(rows), "corrected": len(rows), "interior_pct": 100,
                       "assembly_tier": "GOOD"},
        "bioassay_scope": {"assay_data_state": "NOT_PROVIDED"},
        "bioactivity": {"metadata_state": "NOT_SUPPLIED"},
        "recommended_next_steps": [],
        "bgcs": rows,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _assert_native_refusal(package: Path, outdir: Path, *, top_n: int) -> dict:
    result = guide.layperson_command(
        Namespace(package=str(package), outdir=str(outdir), format="md", top_n=top_n)
    )
    assert result == 2
    receipt = json.loads(
        (outdir / "SYNTHETIC-001_LAYPERSON_GUIDE_RECEIPT.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["status"] == "CANNOT_FROM_PACKAGE"
    assert receipt["outputs"] == []
    assert receipt["error_type"] == "LaypersonGuideError"
    assert not list(outdir.glob("*.md"))
    assert not list(outdir.glob("*.docx"))
    return receipt


def test_hidden_invalid_native_row_beyond_top_n_refuses_before_output(tmp_path: Path) -> None:
    rows = [_native_row("CP123456.1", "BGC001", 1),
            _native_row("CP123457.1", "BGC002", 99)]
    rows[1]["Full_Node_ID"] = "CP999999.1"
    package = _native_package(tmp_path, rows)
    _assert_native_refusal(package, tmp_path / "refused", top_n=1)


def test_duplicate_native_alias_refuses_without_echoing_alias(tmp_path: Path) -> None:
    rows = [_native_row("CP123456.1", "BGC001", 1),
            _native_row("CP123457.1", "BGC001", 2)]
    package = _native_package(tmp_path, rows)
    receipt = _assert_native_refusal(package, tmp_path / "refused", top_n=1)
    assert receipt["error"] == "DUPLICATE_BGC_ALIAS_AT_MANIFEST_RECORD:2"


def test_duplicate_native_physical_locus_refuses_without_echoing_alias(tmp_path: Path) -> None:
    rows = [_native_row("CP123456.1", "BGC001", 1),
            _native_row("CP123456.1", "BGC002", 2)]
    package = _native_package(tmp_path, rows)
    receipt = _assert_native_refusal(package, tmp_path / "refused", top_n=1)
    assert receipt["error"] == "DUPLICATE_PHYSICAL_LOCUS_AT_MANIFEST_RECORD:2"


def test_distinct_full_contigs_sharing_normalized_node_remain_distinct(tmp_path: Path) -> None:
    rows = [_native_row("NODE_1_length_1000_cov_1.5", "BGC001", 1),
            _native_row("NODE_1_length_1000_cov_1.9", "BGC002", 2)]
    assert rows[0]["node_id"] == rows[1]["node_id"]
    text = guide.render_markdown(_native_package(tmp_path, rows), top_n=2)
    assert "SYNTHETIC-001 / NODE_1_length_1000_cov_1.5 / region001 / BGC001" in text
    assert "SYNTHETIC-001 / NODE_1_length_1000_cov_1.9 / region001 / BGC002" in text


def test_true_native_synonym_conflict_keeps_typed_refusal_receipt(tmp_path: Path) -> None:
    row = _native_row("CP123456.1", "BGC001", 1)
    row["Contig"] = "CP999999.1"
    package = _native_package(tmp_path, [row])
    _assert_native_refusal(package, tmp_path / "refused", top_n=1)


def test_legacy_row_without_lowercase_node_id_uses_generic_owner(tmp_path: Path) -> None:
    row = _native_row("CP123456.1", "BGC001", 1)
    row.pop("node_id")
    text = guide.render_markdown(_native_package(tmp_path, [row]))
    assert "SYNTHETIC-001 / CP123456.1 / region001 / BGC001" in text


def test_direct_cli_renders_native_full_contig_without_traceback(tmp_path: Path) -> None:
    package = _native_package(
        tmp_path, [_native_row("NODE_1_length_1000_cov_1.5", "BGC001", 1)]
    )
    outdir = tmp_path / "rendered"
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "mamey_run.py"),
            "layperson",
            str(package),
            "--outdir",
            str(outdir),
            "--format",
            "md",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "Traceback" not in completed.stderr
    text = (outdir / "SYNTHETIC-001_LAYPERSON_GUIDE.md").read_text(
        encoding="utf-8"
    )
    assert "SYNTHETIC-001 / NODE_1_length_1000_cov_1.5 / region001 / BGC001" in text


def test_direct_cli_native_conflict_writes_refusal_without_traceback(tmp_path: Path) -> None:
    row = _native_row("CP123456.1", "BGC001", 1)
    row["Full_Node_ID"] = "CP999999.1"
    package = _native_package(tmp_path, [row])
    outdir = tmp_path / "refused"
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "mamey_run.py"),
            "layperson",
            str(package),
            "--outdir",
            str(outdir),
            "--format",
            "md",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "Traceback" not in completed.stderr
    receipt = json.loads(
        (outdir / "SYNTHETIC-001_LAYPERSON_GUIDE_RECEIPT.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["status"] == "CANNOT_FROM_PACKAGE"
    assert receipt["outputs"] == []
    assert receipt["error_type"] == "LaypersonGuideError"
    assert not list(outdir.glob("*.md"))
    assert not list(outdir.glob("*.docx"))
