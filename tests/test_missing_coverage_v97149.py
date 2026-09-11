"""test_missing_coverage_v97149.py

Covers three gaps identified in the v9.7.149a audit:
  - Item 2: f-string in multi-strain gold-figures skip message
  - Item 3: emit_for_bgc round-trip (FASTA emission + manifest return)
  - Item 4: _load_panel_sequences BGC filtering (no bgc_id dead parameter)

All tests use tmp_path and synthetic fixtures — no real package required.
"""
import csv
import json
import pathlib
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Item 2 — f-string in multi-strain skip message
# ─────────────────────────────────────────────────────────────────────────────

def test_multi_strain_skip_message_is_fstring():
    """Guard against a missing f-prefix producing literal {len(results)}."""
    import ast
    src = pathlib.Path(__file__).resolve().parents[1] / "mamey" / "cli.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))

    # Find the node that calls print() with the gold-figures skip message
    # It must be an f-string (JoinedStr), not a plain string (Constant)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "print":
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and "len(results)" in str(arg.value):
                        raise AssertionError(
                            "Found bare string containing 'len(results)' passed to print() — "
                            "f-prefix is missing (literal '{len(results)}' will be printed)."
                        )


def test_multi_strain_skip_message_contains_count():
    """The skip message must interpolate the strain count, not print a placeholder."""
    src = (pathlib.Path(__file__).resolve().parents[1] / "mamey" / "cli.py").read_text()
    # The correct line should look like: f"...only 1 of {len(results)} strains..."
    # It must NOT appear as a raw string with curly braces
    import re
    # v9.7.407: match the EMISSION, not the spelling. mamey/ now routes terminal output through
    # mamey.console.emit (a pass-through to builtins.print), so a test anchored to the literal
    # token `print` stopped testing the moment the call site was renamed -- the same defect class
    # as the repo_health print ratchet (see CLAUDE_407_metric_measures_token_not_behaviour).
    _EMIT = r'(?:print|emit)'
    bad = re.search(_EMIT + r'\(["\'].*?\{len\(results\)\}.*?["\']', src)
    assert bad is None, (
        f"f-string missing — found literal braces in the emission call at char {bad.start()}"
    )
    good = re.search(_EMIT + r'\(f["\'].*?len\(results\).*?["\']', src)
    assert good is not None, "Expected an f-string print()/emit() with len(results) interpolation"


# ─────────────────────────────────────────────────────────────────────────────
# Item 3 — emit_for_bgc round-trip
# ─────────────────────────────────────────────────────────────────────────────

def _make_panel_package(tmp_path: pathlib.Path, bgc_id: str = "BGC003") -> pathlib.Path:
    """Build a minimal fake package with a BLASTP panel."""
    pkg = tmp_path / "AS-XXX" / "package"
    panel = pkg / "bgc_blastp_panel"
    panel.mkdir(parents=True)

    # Manifest CSV
    manifest_path = panel / "AS-XXX_BGC_BLASTP_PANEL_selection_manifest.csv"
    with manifest_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["bgc_id", "locus_tag", "panel_scope",
                                           "aa_length", "priority_rank", "note"])
        w.writeheader()
        w.writerow({"bgc_id": bgc_id, "locus_tag": "ctg107_3",
                    "panel_scope": "curated", "aa_length": "619",
                    "priority_rank": "1", "note": ""})
        w.writerow({"bgc_id": bgc_id, "locus_tag": "ctg107_5",
                    "panel_scope": "curated", "aa_length": "1591",
                    "priority_rank": "2", "note": ""})
        w.writerow({"bgc_id": "BGC999", "locus_tag": "ctg999_1",
                    "panel_scope": "curated", "aa_length": "400",
                    "priority_rank": "1", "note": ""})

    # FASTA file (curated scope)
    fasta = panel / f"AS-XXX_{bgc_id}_curated_2_for_BLASTP.faa"
    fasta.write_text(
        f">ctg107_3 gene=ctg107_3 bgc={bgc_id} aa=619\n"
        "MSTLKGAVIV" * 61 + "MSTLKGAVIV\n"
        f">ctg107_5 gene=ctg107_5 bgc={bgc_id} aa=1591\n"
        "MSTLKGAVIV" * 159 + "M\n"
        ">ctg999_1 gene=ctg999_1 bgc=BGC999 aa=400\n"
        "MSTLKGAVIV" * 40 + "\n",
        encoding="utf-8",
    )
    return pkg


def test_emit_for_bgc_returns_ok_status(tmp_path):
    from mamey.modeb_blastp import emit_for_bgc
    pkg = _make_panel_package(tmp_path, "BGC003")
    result = emit_for_bgc(pkg, "BGC003", out_dir=tmp_path / "out_BGC003")
    assert result["status"] == "OK", f"Expected OK, got: {result}"
    assert result["proteins_found"] == 2
    assert result["batch_count"] >= 1


def test_emit_for_bgc_writes_fasta_files(tmp_path):
    from mamey.modeb_blastp import emit_for_bgc
    pkg = _make_panel_package(tmp_path, "BGC003")
    out = tmp_path / "out_BGC003"
    emit_for_bgc(pkg, "BGC003", out_dir=out)
    fasta_files = list(out.glob("*.fasta"))  # v9.7.151: emit_for_bgc writes .fasta, not .faa
    assert len(fasta_files) >= 1, "No FASTA files written"
    content = fasta_files[0].read_text()
    assert ">ctg107_3" in content or ">ctg107_5" in content


def test_emit_for_bgc_filters_to_requested_bgc(tmp_path):
    """BGC999 sequences must not appear in BGC003 output."""
    from mamey.modeb_blastp import emit_for_bgc
    pkg = _make_panel_package(tmp_path, "BGC003")
    out = tmp_path / "out_BGC003"
    emit_for_bgc(pkg, "BGC003", out_dir=out)
    for fasta in out.glob("*.fasta"):  # v9.7.151: emit_for_bgc writes .fasta, not .faa
        content = fasta.read_text()
        assert "ctg999_1" not in content, "BGC999 sequence leaked into BGC003 batch"


def test_emit_for_bgc_skips_unknown_bgc(tmp_path):
    from mamey.modeb_blastp import emit_for_bgc
    pkg = _make_panel_package(tmp_path, "BGC003")
    result = emit_for_bgc(pkg, "BGC999_NONEXISTENT", out_dir=tmp_path / "out_X")
    assert result["status"] == "SKIPPED"
    assert result["proteins_found"] == 0


def test_emit_for_bgc_skips_when_no_panel(tmp_path):
    from mamey.modeb_blastp import emit_for_bgc
    pkg = tmp_path / "empty" / "package"
    pkg.mkdir(parents=True)
    result = emit_for_bgc(pkg, "BGC003", out_dir=tmp_path / "out_X")
    assert result["status"] == "SKIPPED"
    assert "no panel manifest" in result.get("note", "").lower()


# ─────────────────────────────────────────────────────────────────────────────
# Item 4 — _load_panel_sequences (no bgc_id parameter — filtering is caller's job)
# ─────────────────────────────────────────────────────────────────────────────

def test_load_panel_sequences_no_bgc_id_parameter():
    """_load_panel_sequences must NOT have a bgc_id parameter (A001 — dead param removed)."""
    import inspect
    from mamey.modeb_blastp import _load_panel_sequences
    sig = inspect.signature(_load_panel_sequences)
    assert "bgc_id" not in sig.parameters, (
        "bgc_id parameter is dead code and was supposed to be removed (A001). "
        "Filtering is done by the caller, not by _load_panel_sequences."
    )


def test_load_panel_sequences_returns_all_tags_no_filtering(tmp_path):
    """_load_panel_sequences returns ALL sequences; caller filters by BGC."""
    from mamey.modeb_blastp import _load_panel_sequences
    panel = tmp_path / "panel"
    panel.mkdir()
    fasta = panel / "test_curated_1_for_BLASTP.faa"
    fasta.write_text(
        ">ctg1_1 gene=ctg1_1 bgc=BGC001\nAAAAAAAAAAAAAAAAAAAA\n"
        ">ctg2_1 gene=ctg2_1 bgc=BGC002\nMMMMMMMMMMMMMMMMMMMM\n",
        encoding="utf-8",
    )
    seqs = _load_panel_sequences(panel)
    assert "ctg1_1" in seqs
    assert "ctg2_1" in seqs  # both present — no filtering


def test_load_panel_sequences_empty_dir(tmp_path):
    from mamey.modeb_blastp import _load_panel_sequences
    panel = tmp_path / "empty_panel"
    panel.mkdir()
    seqs = _load_panel_sequences(panel)
    assert seqs == {}


def test_load_panel_sequences_curated_takes_priority(tmp_path):
    """Curated files take priority over first_pass files."""
    from mamey.modeb_blastp import _load_panel_sequences
    panel = tmp_path / "panel"
    panel.mkdir()
    # curated file has tag_A; first_pass has tag_B
    (panel / "test_curated_2_for_BLASTP.faa").write_text(
        ">tag_A gene=tag_A\nAAAAAAAAAAAAAAAAAAAA\n", encoding="utf-8"
    )
    (panel / "test_FIRST_PASS_5_for_BLASTP.faa").write_text(
        ">tag_B gene=tag_B\nMMMMMMMMMMMMMMMMMMMM\n", encoding="utf-8"
    )
    seqs = _load_panel_sequences(panel)
    assert "tag_A" in seqs
    # tag_B should not be present because curated was found first (priority escalation stops)
    assert "tag_B" not in seqs


