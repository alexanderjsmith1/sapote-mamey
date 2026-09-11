import sys
import types
import csv

from mamey import compile_report as CR


def test_unreadable_blastp_channel_table_is_not_no_evidence(tmp_path):
    store = tmp_path / "blastp_nr"
    store.mkdir()
    (store / "query_top10.csv").write_bytes(b"\xff\xfe")
    text = CR._blastp_from_channel_stores(tmp_path)
    assert "BLASTP_CHANNEL_INPUT_INVALID" in text
    assert "nr=1" in text
    assert "not interpreted as no-hit evidence" in text


def test_malformed_blastp_schema_and_score_are_not_zero_hits(tmp_path):
    store = tmp_path / "blastp_nr"
    store.mkdir()
    (store / "bad_schema_top10.csv").write_text("arbitrary,columns\na,b\n", encoding="utf-8")
    (store / "bad_score_top10.csv").write_text(
        "hit_rank,pct_identity,pct_positives,subject_def\n1,invalid,50,subject\n", encoding="utf-8")
    text = CR._blastp_from_channel_stores(tmp_path)
    assert "BLASTP_CHANNEL_INPUT_INVALID" in text
    assert "nr=2" in text
    assert "| 0% |" not in text


def test_measured_zero_blastp_scores_remain_valid_observations(tmp_path):
    store = tmp_path / "blastp_nr"
    store.mkdir()
    (store / "measured_top10.csv").write_text(
        "hit_rank,pct_identity,pct_positives,subject_def\n1,0,0,measured zero\n", encoding="utf-8")
    text = CR._blastp_from_channel_stores(tmp_path)
    assert "BLASTP_CHANNEL_INPUT_INVALID" not in text
    assert "| 0% | 0% | measured zero |" in text


def test_fermentation_draft_types_both_source_failures(tmp_path, monkeypatch):
    (tmp_path / "TEST-STRAIN_4_triage_board.csv").write_bytes(b"\xff\xfe")
    from mamey import modeb_subsections
    monkeypatch.setattr(modeb_subsections, "_genus_of",
                        lambda pkg: (_ for _ in ()).throw(RuntimeError("bad genus source")))
    text = CR._fermentation_draft(tmp_path)
    assert "TRIAGE_INPUT_INVALID:UnicodeDecodeError" in text
    assert "GENUS_INPUT_INVALID:RuntimeError" in text
    assert "fallbacks are unresolved, not observed absence" in text


def test_compile_report_surfaces_locus_map_failure(tmp_path, monkeypatch):
    (tmp_path / "manifest.json").write_text('{"strain_id":"TEST-STRAIN"}', encoding="utf-8")
    locus_map = types.ModuleType("mamey.locus_map")
    locus_map.render_for_compile_report = (
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("renderer failed"))
    )
    import mamey
    monkeypatch.setattr(mamey, "locus_map", locus_map, raising=False)
    monkeypatch.setitem(sys.modules, "mamey.locus_map", locus_map)
    monkeypatch.setattr(CR, "_try_generate_figures", lambda pkg: "")
    text = CR.build_report(tmp_path, generate_figures=True)
    assert "LOCUS_MAP_RENDER_INVALID: RuntimeError" in text
    assert "without treating the failure as absence" in text


def test_compile_report_no_figures_mode_has_no_false_locus_error(tmp_path):
    (tmp_path / "manifest.json").write_text('{"strain_id":"TEST-STRAIN"}', encoding="utf-8")
    text = CR.build_report(tmp_path, generate_figures=False)
    assert "LOCUS_MAP_RENDER_INVALID" not in text


def test_key_findings_does_not_convert_malformed_kcb_score_to_zero(tmp_path):
    table = tmp_path / "TEST-STRAIN_4_triage_board.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "BGC_ID", "Contig", "antiSMASH_Region", "Corrected_rank",
            "KCB_score", "KCB_top", "Products",
        ])
        writer.writeheader()
        writer.writerow({"BGC_ID": "BGC001", "Contig": "NODE_1", "antiSMASH_Region": "region001",
                         "Corrected_rank": "1", "KCB_score": "not-a-number",
                         "KCB_top": "unresolved comparator", "Products": "NRPS"})
    text = CR._key_findings(tmp_path, {
        "assembly_tier": "TEST", "raw_bgcs": 1, "corrected_bgcs": 1,
    })
    assert "KCB_SCORE_INPUT_INVALID: 1 row(s)" in text
    assert "1 low/zero-KCB BGC(s)" not in text


def test_key_findings_preserves_measured_zero_kcb_score(tmp_path):
    table = tmp_path / "TEST-STRAIN_4_triage_board.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "BGC_ID", "Contig", "antiSMASH_Region", "Corrected_rank",
            "KCB_score", "KCB_top", "Products",
        ])
        writer.writeheader()
        writer.writerow({"BGC_ID": "BGC001", "Contig": "NODE_1", "antiSMASH_Region": "region001",
                         "Corrected_rank": "1", "KCB_score": "0",
                         "KCB_top": "", "Products": "NRPS"})
    text = CR._key_findings(tmp_path, {
        "assembly_tier": "TEST", "raw_bgcs": 1, "corrected_bgcs": 1,
    })
    assert "KCB_SCORE_INPUT_INVALID" not in text
    assert "1 low/zero-KCB BGC(s)" in text


def test_decision_matrix_does_not_convert_malformed_scores_or_rank_to_low():
    score_action, score_reason = CR._decision_for({
        "AB_auto": "not-a-number", "AF_auto": "0", "Corrected_rank": "12",
    })
    rank_action, rank_reason = CR._decision_for({
        "AB_auto": "0", "AF_auto": "0", "Corrected_rank": "not-a-rank",
    })
    assert score_action == "UNRESOLVED"
    assert "AB_auto" in score_reason
    assert rank_action == "UNRESOLVED"
    assert "Corrected_rank/Rank" in rank_reason


def test_decision_matrix_preserves_measured_zero_scores():
    action, reason = CR._decision_for({
        "AB_auto": "0", "AF_auto": "0", "Corrected_rank": "12",
    })
    assert action == "LOW"
    assert "score 0.00" in reason
