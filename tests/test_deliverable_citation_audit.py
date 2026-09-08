"""deliverable_citation_audit: pre-delivery §15 citation + provenance + collision gate. Hermetic.

Matches the bgc_reconcile test convention (importlib-loaded tool, synthetic tempdir fixtures,
assertions on pure functions). No private strain data.

Covers: the BLOCK bare-in-prose class (the 324-incident failure mode), inline + clause + table
"located" recognition, TOC / cross-ref / SID leniency tiers, provenance presence, cross-file ID
collisions WITH per-strain scoping (so cross-strain reuse is not a false collision), the property
that the rendered report passes the bundle's OWN claim-safety linter, and an ENGINE-CONSISTENCY
test asserting the local regexes agree with mamey.modeb_structure_gate so "located"/"provenance"
here mean what they mean in verify-modeb.
"""
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location(
    "deliverable_citation_audit", ROOT / "tools" / "deliverable_citation_audit.py")
dca = importlib.util.module_from_spec(_s)
_s.loader.exec_module(dca)


def _codes(findings):
    return [f["code"] for f in findings]


def _sev(findings, code):
    return [f["severity"] for f in findings if f["code"] == code]


# ── bare-in-prose: the shipping violation ────────────────────────────────────────────────────────

def test_bare_in_prose_blocks():
    findings, located, prov = dca.scan_text("The strongest lead is BGC008, a nucleoside antifungal.")
    assert "BARE_IN_PROSE" in _codes(findings)
    assert _sev(findings, "BARE_IN_PROSE") == ["BLOCK"]
    assert located == []


def test_inline_locator_is_clean_and_located():
    findings, located, prov = dca.scan_text(
        "BGC008 (NODE_12_length_50000_cov_9 · region001) is the lead. [observed]")
    assert not any(f["code"].startswith("BARE") for f in findings)
    assert len(located) == 1
    num, loc, src, line = located[0]
    assert num == "008" and loc == ("NODE_12", "1")


def test_clause_locator_prose_is_covered():
    # locator lives later in the same clause, not in a parenthetical — the §15 "same clause" allowance
    findings, located, prov = dca.scan_text("BGC008 sits on NODE_12 · r001 in this assembly. [inferred]")
    assert not any(f["code"].startswith("BARE") for f in findings)
    assert located and located[0][0] == "008"


def test_clause_boundary_stops_coverage():
    # locator is in a DIFFERENT clause (after a period) — must NOT cover the bare mention
    findings, _, _ = dca.scan_text("We excluded BGC018. The winner sits on NODE_16 · r001. [observed]")
    assert "BARE_IN_PROSE" in _codes(findings)


# ── tables ───────────────────────────────────────────────────────────────────────────────────────

def test_table_row_with_locator_column_is_clean():
    md = ("| BGC | Node/Region | Reason |\n"
          "|---|---|---|\n"
          "| BGC018 | NODE_16 · r001 | pure saccharide |\n")
    findings, located, prov = dca.scan_text(md)
    assert not any(f["code"] == "BARE_IN_TABLE" for f in findings)
    assert located and located[0][0] == "018"


def test_table_row_bare_is_watch():
    md = "| BGC | Reason |\n|---|---|\n| BGC031 | primary metabolism |\n"
    findings, _, _ = dca.scan_text(md)
    assert _sev(findings, "BARE_IN_TABLE") == ["WATCH"]


# ── leniency tiers ─────────────────────────────────────────────────────────────────────────────

def test_crossref_is_info_not_block():
    findings, _, _ = dca.scan_text("BGC039/BGC027 share a tier here. [computed]")
    assert "BARE_IN_PROSE" not in _codes(findings)
    assert set(_sev(findings, "CROSSREF_NO_LOCATOR")) == {"INFO"}


def test_toc_abbreviation_is_info():
    md = "## Table of Contents\n- BGC028 lassopeptide\n"
    findings, _, _ = dca.scan_text(md)
    assert "BARE_IN_TOC" in _codes(findings)
    assert _sev(findings, "BARE_IN_TOC") == ["INFO"]


def test_sid_prefixed_prose_is_watch():
    findings, _, _ = dca.scan_text("The lead SID-XXX BGC050 is a PTM macrolactam. [corpus]")
    assert "SID_PREFIXED_NO_LOCATOR" in _codes(findings)
    assert _sev(findings, "SID_PREFIXED_NO_LOCATOR") == ["WATCH"]


def test_code_fence_is_skipped():
    md = "```\nBGC008 example command\n```\n"
    findings, _, _ = dca.scan_text(md)
    assert findings == [] or all(f["code"] == "NO_PROVENANCE_TAGS" for f in findings)


def test_heading_bare_id_not_prose_block():
    findings, _, _ = dca.scan_text("# Lead BGC008 overview\nBody sits on NODE_1 · r001. [observed]")
    assert "BARE_IN_PROSE" not in _codes(findings)


# ── provenance ──────────────────────────────────────────────────────────────────────────────────

def test_provenance_missing_flagged():
    findings, _, prov = dca.scan_text("BGC008 (NODE_1 · r001) is the lead.")
    assert prov is not None and prov["code"] == "NO_PROVENANCE_TAGS"


def test_provenance_present_not_flagged():
    findings, _, prov = dca.scan_text("BGC008 (NODE_1 · r001) is the lead [store-backed].")
    assert prov is None


# ── collisions with per-strain scoping ───────────────────────────────────────────────────────────

def _write(tmp, name, text):
    p = Path(tmp) / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_collision_same_strain_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        a = _write(tmp, "AS-705_a.md", "BGC008 (NODE_12_length_5_cov_1 · region001). [observed]")
        b = _write(tmp, "AS-705_b.md", "BGC008 (NODE_5_length_9_cov_3 · region002). [inferred]")
        _, _, located, _, collisions = dca.audit([a, b])
        assert any(c["code"] == "ID_COLLISION" and c["severity"] == "BLOCK" for c in collisions)


def test_no_collision_cross_strain():
    with tempfile.TemporaryDirectory() as tmp:
        a = _write(tmp, "AS-705_a.md", "BGC008 (NODE_12 · region001). [observed]")
        b = _write(tmp, "AS-660_b.md", "BGC008 (NODE_9 · region001). [observed]")
        _, _, _, _, collisions = dca.audit([a, b])
        assert not any(c["code"].startswith("ID_COLLISION") for c in collisions)


def test_no_collision_same_address_repeated():
    with tempfile.TemporaryDirectory() as tmp:
        a = _write(tmp, "AS-705_a.md", "BGC008 (NODE_12 · region001). [observed]")
        b = _write(tmp, "AS-705_b.md", "BGC008 (NODE_12_length_5_cov_1 · region001) again. [inferred]")
        _, _, _, _, collisions = dca.audit([a, b])
        assert not any(c["code"].startswith("ID_COLLISION") for c in collisions)


# ── driver-level BLOCK count (drives --strict) ───────────────────────────────────────────────────

def test_strict_count_semantics():
    with tempfile.TemporaryDirectory() as tmp:
        bad = _write(tmp, "bad.md", "We excluded BGC018 from the set. [observed]")
        good = _write(tmp, "AS-1_good.md", "BGC018 (NODE_16 · r001) excluded. [store-backed]")
        _, fb, _, _, cb = dca.audit([bad])
        _, fg, _, _, cg = dca.audit([good])
        n_block_bad = sum(1 for f in fb + cb if f["severity"] == "BLOCK")
        n_block_good = sum(1 for f in fg + cg if f["severity"] == "BLOCK")
        assert n_block_bad >= 1
        assert n_block_good == 0


# ── self-lint property + engine consistency ─────────────────────────────────────────────────────

def test_rendered_report_passes_own_claim_safety():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from claim_safety_linter import lint_claim_safety
    files, findings, located, counts, collisions = dca.audit(
        [str(ROOT / "examples" / "judgment_18strain" / "Lit_Verification_DAPR_New_Leads.md")])
    rendered = dca.render_md(findings, counts, collisions, files)
    assert lint_claim_safety(rendered) == []


# ── real-artifact edge cases (surfaced by the CNY228 accession-contig genome) ─────────────────────

def test_accession_contig_inline_is_clean():
    # NCBI accession contig, not SPAdes NODE_ — must be recognized as a locator, both citation directions
    fa, _, _ = dca.scan_text("BGC040 (NZ_KB898240.1 · region001) is the lead. [observed]")
    assert not any(f["code"].startswith("BARE") for f in fa)
    fb, _, _ = dca.scan_text("| NZ_KB898240.1 region001 (BGC040) | BGC040 | done |")
    assert not any(f["code"].startswith("BARE") for f in fb)


def test_norm_locator_accession():
    assert dca._norm_locator("NZ_KB898240.1 region001") == ("NZ_KB898240.1", "1")
    assert dca._norm_locator("NODE_1_length_20000_cov_50 · region001") == ("NODE_1", "1")


def test_accession_collision_and_partial_tolerance():
    with tempfile.TemporaryDirectory() as tmp:
        a = _write(tmp, "AS-9_a.md", "BGC008 (NZ_KB111.1 region001). [observed]")
        b = _write(tmp, "AS-9_b.md", "BGC008 (NZ_KB999.1 region002). [inferred]")
        _, _, _, _, cols = dca.audit([a, b])
        assert any(c["code"] == "ID_COLLISION" for c in cols)  # different accessions → real collision
    with tempfile.TemporaryDirectory() as tmp:
        # same contig, one citation omits the region — a partial, NOT a collision
        a = _write(tmp, "AS-9_a.md", "BGC008 (NZ_KB111.1 region005). [observed]")
        b = _write(tmp, "AS-9_b.md", "BGC008 (NZ_KB111.1). [inferred]")
        _, _, _, _, cols = dca.audit([a, b])
        assert not any(c["code"].startswith("ID_COLLISION") for c in cols)


def test_plus_pairing_is_info_not_block():
    findings, _, _ = dca.scan_text("- BGC031+BGC040 co-occur (RGGMCI pair). [computed]")
    assert "BARE_IN_PROSE" not in _codes(findings)
    assert set(_sev(findings, "CROSSREF_NO_LOCATOR")) == {"INFO"}


def test_image_embed_skipped():
    findings, _, _ = dca.scan_text("![BGC005_locus_map](locus_maps/BGC005_locus_map.svg)\n")
    assert not any(f["code"].startswith("BARE") for f in findings)


def test_figure_caption_is_info():
    findings, _, _ = dca.scan_text("*Figure: BGC005 locus map.*\n")
    assert "CAPTION_NO_LOCATOR" in _codes(findings)
    assert _sev(findings, "CAPTION_NO_LOCATOR") == ["INFO"]


def test_field_block_identity_is_covered():
    # the §1 identity block: id on one field line, node/region on the next — must count as covered
    md = ("**BGC:** BGC040\n"
          "**Node / contig:** NZ_KB898240.1\n"
          "**antiSMASH region:** region001\n[observed]\n")
    findings, _, _ = dca.scan_text(md)
    assert not any(f["code"].startswith("BARE") for f in findings)


def test_engine_consistency():
    """Local regexes must agree with mamey.modeb_structure_gate so 'located'/'provenance' don't drift."""
    import mamey.modeb_structure_gate as g
    # provenance vocabulary identical
    assert dca._PROVENANCE_RE.pattern == g._PROVENANCE_RE.pattern
    # any-BGC token identical
    assert dca._ANY_BGC_RE.pattern == g._ANY_BGC_RE.pattern
    # behavioral: what the engine calls "located inline" this tool also calls located
    samples = ["BGC008 (NODE_12 · region001)", "BGC008 (ctg1_2)", "BGC008 (NODE_1_length_5_cov_2 · r001)"]
    for s in samples:
        assert g._LOCATOR_BGC_RE.search(s) is not None
        assert dca._LOCATOR_INLINE_RE.match(s, 0) is not None
