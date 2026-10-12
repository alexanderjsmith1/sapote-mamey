"""Invented saved-result fixtures for M5 diagnostic and admission repairs."""
import copy
import json
from pathlib import Path

import pytest

from tests.test_public_master_scope import cohort, _load
from tests._gold_identity_fixture import bind_synthetic_gold_package
from mamey import cohort_figures as cf
from mamey import deep_data, figures_smoke, gold_bgc_identity
from mamey.cohort_synthesis import PublicCohortScopeError


def test_unreadable_private_metadata_stays_excluded_with_diagnostic(cohort):
    held = cohort.packages["held_scientific_sentinel"]
    (held / "manifest.json").write_text("{invalid synthetic metadata")
    with pytest.warns(RuntimeWarning, match="^PRIVATE_PACKAGE_METADATA_UNREADABLE_EXCLUDED$") as caught:
        scope = _load(cohort)
    assert len(caught) == 1
    assert set(scope["strains"]) == {"public_alpha", "public_beta"}
    assert "held_scientific_sentinel" in scope["_blocked"]
    assert "held_scientific_sentinel" not in str(caught[0].message)


def test_public_metadata_reread_failure_refuses_before_payload(cohort, monkeypatch):
    target = cohort.packages["public_alpha"] / "manifest.json"
    original = Path.read_text
    reads = 0

    def read(path, *args, **kwargs):
        nonlocal reads
        if path == target:
            reads += 1
            if reads == 2:
                raise OSError("SYNTHETIC_DIAGNOSTIC_MUST_NOT_LEAK")
        if path.name in {"deep_data.json", "gene_data.json"}:
            pytest.fail("Scientific payload opened after metadata reread refusal")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    with pytest.raises(PublicCohortScopeError, match="^PUBLIC_PRIVACY_METADATA_UNREADABLE$") as caught:
        _load(cohort)
    assert reads == 2
    assert "SYNTHETIC_DIAGNOSTIC_MUST_NOT_LEAK" not in str(caught.value)


def test_smoke_issue_log_failure_retains_hold_and_independent_figure(tmp_path, monkeypatch, capsys):
    package = tmp_path / "package"
    package.mkdir()
    (package / "SYNTHETIC_REFERENCE_2_inventory.csv").write_text("BGC_ID\nSYNTHETIC_REGION\n")
    monkeypatch.setattr(figures_smoke, "_import_matplotlib", lambda: object())

    def ranking(*args, **kwargs):
        raise figures_smoke.ExactLocusIdentityError("SYNTHETIC_IDENTITY_MUST_NOT_LEAK")

    def independent(*args, **kwargs):
        path = package / "smoke_figures" / "independent.png"
        path.write_bytes(b"synthetic renderer output")
        return path

    original_open = Path.open

    def open_path(path, *args, **kwargs):
        if path == package / "issue_log.md":
            raise OSError("SYNTHETIC_DIAGNOSTIC_MUST_NOT_LEAK")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_path)
    monkeypatch.setattr(figures_smoke, "_fig_bgc_ranking", ranking)
    monkeypatch.setattr(figures_smoke, "_fig_class_composition", independent)
    monkeypatch.setattr(figures_smoke, "_fig_assembly_tier", lambda *a, **k: None)
    result = figures_smoke.generate(package)
    assert result["identity_holds"] == ["fig_bgc_ranking: HOLD_IDENTITY_UNRESOLVED",
                                        "issue_log: HOLD_DIAGNOSTIC_WRITE_FAILED"]
    assert result["figures"] == 1
    assert result["files"] == ["independent.png"]
    assert (package / "smoke_figures" / "independent.png").read_bytes() == b"synthetic renderer output"
    captured = capsys.readouterr()
    assert "MUST_NOT_LEAK" not in json.dumps(result) + captured.out + captured.err


@pytest.mark.parametrize("error_type", [OSError, ValueError, TypeError])
def test_deep_context_read_failure_records_hold_without_erasing_legacy_evidence(tmp_path, monkeypatch, error_type):
    strain = "SYNTHETIC_REFERENCE_DIAGNOSTIC"
    package = tmp_path / "package"
    bound = bind_synthetic_gold_package(package, strain,
        deep={"bgc_profile": [{"bgc_id": "BGC001", "PKS_KS": 2}], "active_sites": []})
    evidence = {"by_region": {"ctg1_c1": [{"domains": [{"domain_id": "synthetic_domain",
        "locus": "synthetic_gene", "active_site_calls": "SYNTHETIC_MEASUREMENT"}]}]}}
    (package / f"{strain}_AntiSMASH_Evidence_Parse.json").write_text(json.dumps(evidence))

    def unavailable(*args, **kwargs):
        raise error_type("SYNTHETIC_DIAGNOSTIC_MUST_NOT_LEAK")

    original_loader = gold_bgc_identity.load_gold_identity_context
    monkeypatch.setattr(gold_bgc_identity, "load_gold_identity_context", unavailable)
    deep_data.build_deep_data_files(package, strain)
    deep = json.loads((package / "deep_data.json").read_text())
    gene = json.loads((package / "gene_data.json").read_text())
    expected = {"schema_version": gold_bgc_identity.SCHEMA, "status": "HOLD",
                "reason": "GOLD_IDENTITY_CONTEXT_UNREADABLE", "error_type": error_type.__name__}
    assert deep["bgc_identity_contract"] == gene["bgc_identity_contract"] == expected
    assert deep["bgc_profile"][0]["PKS_KS"] == 2
    assert "bgc_identity" not in deep["bgc_profile"][0]
    assert deep["active_sites"][0]["active_site_calls"] == "SYNTHETIC_MEASUREMENT"
    assert "MUST_NOT_LEAK" not in json.dumps(deep) + json.dumps(gene)
    monkeypatch.setattr(gold_bgc_identity, "load_gold_identity_context", original_loader)
    with pytest.raises(gold_bgc_identity.GoldBGCIdentityError):
        gold_bgc_identity.admit_gold_profiles(package, strain, deep, gene)
    assert bound["context"]["receipt"]["status"] != "HOLD"


def test_canonical_figure_equal_integer_counts_are_admitted(cohort):
    scope = _load(cohort)
    selected = cf.load(cohort.runs, public_only=True, privacy_profile=cohort.profile, canonical_scope=scope)
    assert set(selected) == {"public_alpha", "public_beta"}
    for strain, entry in selected.items():
        count = len(scope["_manifests"][strain]["bgcs"])
        assert entry["ms"]["raw_bgcs"] == entry["ms"]["corrected_bgcs"] == count


@pytest.mark.parametrize("short_value", ["ABSENT", None, "", 3])
def test_canonical_figure_corrected_short_boundary_refuses(cohort, monkeypatch, short_value):
    scope = _load(cohort)
    original = cf._load_manifest_short
    # Exercise the comparison boundary independently of the earlier required-field
    # validator: a second validator must not admit normalized missing == missing.
    scope["_manifests"]["public_alpha"]["bgc_counts"]["corrected"] = None

    def read_short(package, strain):
        value = copy.deepcopy(original(package, strain))
        if strain == "public_alpha":
            if short_value == "ABSENT":
                value.pop("corrected_bgcs")
            else:
                value["corrected_bgcs"] = short_value
        return value

    monkeypatch.setattr(cf, "_load_manifest_short", read_short)
    with pytest.raises(PublicCohortScopeError, match="^PUBLIC_FIGURE_MANIFEST_CONFLICT$"):
        cf.load(cohort.runs, public_only=True, privacy_profile=cohort.profile, canonical_scope=scope)
