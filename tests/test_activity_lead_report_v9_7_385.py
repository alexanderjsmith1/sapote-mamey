import csv
import json

from mamey.activity_lead_report import build_activity_leads, run


FIELDS = [
    "BGC_ID", "Contig", "Node_ID", "antiSMASH_Region", "Products",
    "Boundary", "Lead_tier_auto", "Corrected_rank", "AB_auto", "AF_auto",
    "Novelty_auto", "KCB_top", "KCB_score", "CCTT_triggers",
    "Standing_rule", "Primary_metab_flag", "Misanchor_Flag", "Mobile_element_flag",
]


def _row(alias, node, region, ab, af, *, corrected="1", standing="", boundary="Interior"):
    return {
        "BGC_ID": alias,
        "Contig": node,
        "Node_ID": node,
        "antiSMASH_Region": region,
        "Products": "RiPP; test-class",
        "Boundary": boundary,
        "Lead_tier_auto": "High",
        "Corrected_rank": corrected,
        "AB_auto": str(ab),
        "AF_auto": str(af),
        "Novelty_auto": "40",
        "KCB_top": "BGC0000001 / navigation only",
        "KCB_score": "100",
        "CCTT_triggers": "T43-LAN_lanthipeptide",
        "Standing_rule": standing,
        "Primary_metab_flag": "",
        "Misanchor_Flag": "",
        "Mobile_element_flag": "",
    }


def _package(root, strain, engine, source_rows):
    package = root / strain / "package"
    package.mkdir(parents=True)
    with (package / f"{strain}_4_triage_board.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(source_rows)
    (package / "manifest.json").write_text(
        json.dumps({"strain_id": strain, "workflow_version": engine}), encoding="utf-8"
    )


def _crosswalk(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strain", "full_node_or_contig", "region", "bgc_alias"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_builds_independent_top_n_boards_with_complete_identity(tmp_path):
    runs = tmp_path / "runs"
    _package(
        runs,
        "STRAIN-A",
        "Mamey v1.2.3",
        [
            _row("BGC001", "CONTIG_A", "region001", 70, 20),
            _row("BGC002", "CONTIG_B", "region001", 40, 80),
            _row("BGC003", "CONTIG_C", "region002", 60, 50),
        ],
    )
    rows, unbound, meta = build_activity_leads(str(runs), top_n=2)
    assert unbound == []
    assert meta["complete"] is True
    assert len(rows) == 4
    ab = [row for row in rows if row["axis"] == "antibacterial"]
    af = [row for row in rows if row["axis"] == "antifungal"]
    assert [row["bgc_alias"] for row in ab] == ["BGC001", "BGC003"]
    assert [row["bgc_alias"] for row in af] == ["BGC002", "BGC003"]
    assert ab[0]["exact_locus"] == "STRAIN-A / CONTIG_A / region001 / BGC001"
    assert all(row["identity_state"] == "SOURCE_PACKAGE_LOCATOR_ONLY" for row in rows)


def test_crosswalk_rebinds_alias_by_physical_key(tmp_path):
    runs = tmp_path / "runs"
    _package(runs, "STRAIN-A", "Mamey v1.2.3", [_row("BGC999", "CONTIG_A", "region001", 70, 60)])
    crosswalk = tmp_path / "crosswalk.csv"
    _crosswalk(crosswalk, [{
        "strain": "STRAIN-A",
        "full_node_or_contig": "CONTIG_A",
        "region": "region001",
        "bgc_alias": "BGC001",
    }])
    rows, unbound, meta = build_activity_leads(
        str(runs), top_n=1, canonical_crosswalk=str(crosswalk), require_crosswalk=True
    )
    assert unbound == []
    assert meta["complete"] is True
    assert {row["bgc_alias"] for row in rows} == {"BGC001"}
    assert {row["source_local_bgc_alias"] for row in rows} == {"BGC999"}
    assert {row["alias_binding_state"] for row in rows} == {
        "PHYSICAL_KEY_REBOUND_TO_CANONICAL_ALIAS"
    }
    assert rows[0]["exact_locus"] == "STRAIN-A / CONTIG_A / region001 / BGC001"


def test_required_crosswalk_holds_unmatched_rows_and_reports_incomplete(tmp_path):
    runs = tmp_path / "runs"
    _package(
        runs,
        "STRAIN-A",
        "Mamey v1.2.3",
        [
            _row("BGC001", "CONTIG_A", "region001", 70, 60),
            _row("BGC002", "CONTIG_B", "region001", 60, 50),
        ],
    )
    crosswalk = tmp_path / "crosswalk.csv"
    _crosswalk(crosswalk, [{
        "strain": "STRAIN-A",
        "full_node_or_contig": "CONTIG_A",
        "region": "region001",
        "bgc_alias": "BGC010",
    }])
    rows, unbound, meta = build_activity_leads(
        str(runs), top_n=2, canonical_crosswalk=str(crosswalk), require_crosswalk=True
    )
    assert len(unbound) == 1
    assert unbound[0]["source_local_bgc_alias"] == "BGC002"
    assert len(rows) == 2  # one admitted locus appears once per axis
    assert meta["complete"] is False
    assert meta["incomplete_strains"] == {
        "STRAIN-A": {"antifungal": 1, "antibacterial": 1}
    }


def test_excluded_high_score_does_not_displace_eligible_rows(tmp_path):
    runs = tmp_path / "runs"
    _package(
        runs,
        "STRAIN-A",
        "Mamey v1.2.3",
        [
            _row("BGC001", "CONTIG_A", "region001", 99, 99, standing="RULE-001"),
            _row("BGC002", "CONTIG_B", "region001", 60, 50),
            _row("BGC003", "CONTIG_C", "region001", 50, 60),
        ],
    )
    rows, _, meta = build_activity_leads(str(runs), top_n=2)
    assert meta["complete"] is True
    assert "BGC001" not in {row["bgc_alias"] for row in rows}
    assert all(row["lead_eligible"] == "YES" for row in rows)


def test_mixed_engine_and_writers_are_explicit(tmp_path):
    runs = tmp_path / "runs"
    _package(runs, "STRAIN-A", "Mamey v1.2.3", [_row("BGC001", "CONTIG_A", "region001", 70, 60)])
    _package(runs, "STRAIN-B", "Mamey v1.2.4", [_row("BGC001", "CONTIG_B", "region001", 60, 70)])
    out = tmp_path / "out"
    meta = run(str(runs), str(out), top_n=1)
    assert meta["mixed_engine"] is True
    assert meta["complete"] is True
    assert sorted(meta["engine_versions"]) == ["Mamey v1.2.3", "Mamey v1.2.4"]
    report = (out / "PER_STRAIN_ACTIVITY_LEADS_REPORT.md").read_text(encoding="utf-8")
    assert "Mixed-engine hold" in report
    assert "STRAIN-A / CONTIG_A / region001 / BGC001" in report
    assert "AF_auto and AB_auto are routing priors, not measured bioactivity" in report
    assert (out / "PER_STRAIN_ACTIVITY_LEADS.csv").is_file()
    assert (out / "PER_STRAIN_ACTIVITY_LEADS_UNBOUND.csv").is_file()
    assert (out / "PER_STRAIN_ACTIVITY_LEADS_META.json").is_file()
