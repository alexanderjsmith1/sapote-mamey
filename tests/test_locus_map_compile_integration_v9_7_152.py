"""test_locus_map_compile_integration.py — tests for W5 (v9.7.149c).

Post-seal locus map rendering for the compile-report flow. Reads from
`<strain>_gene_by_gene_all_bgcs.csv` (canonical input — no GBK zip required)
and emits SVG via the canonical matplotlib renderer with `.svg` extension.

Wishlist test set (5 required + 2 bonus):
- SVG output is valid XML
- SVG contains at least one vector-element (gene arrows render as <path>
  from matplotlib's FancyArrow; wishlist asked for <rect>|<polygon> — see
  W5 findings doc for the drift note)
- Strand orientation reflected (forward vs reverse arrows differ)
- Colour varies by domain class
- Non-blocking when a gene-table row is malformed
- bonus: top-N selection from triage_board's Corrected_rank
- bonus: per-BGC failure doesn't block other BGCs in the same batch

Fixtures use AS-XXX only.
"""
from __future__ import annotations

import json
import pathlib
import xml.etree.ElementTree as ET

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _gene_csv_text(bgc_strands: dict[str, list[tuple[int, str]]],
                   domain_blob: str = "Condensation_LCL;AMP-binding") -> str:
    """Build a synthetic gene_by_gene CSV.

    `bgc_strands` maps BGC ID → list of (gene_index, strand) tuples.
    `domain_blob` is the sec_met_domains string used for every gene
    (same blob → same role/colour after palette classification). Use ';'
    as the inner separator since ',' is the CSV delimiter — using ',' here
    would shift column alignment downstream and is exactly the F3-pattern
    bug we hardened against.
    """
    rows = ["bgc_id,locus_tag,gene_start,gene_end,strand,sec_met_domains,aa_length"]
    for bgc_id, genes in bgc_strands.items():
        for i, (idx, strand) in enumerate(genes, start=1):
            start = 1000 + idx * 1500
            end = start + 1000
            rows.append(f"{bgc_id},ctg1_{idx},{start},{end},{strand},"
                        f"{domain_blob},333")
    return "\n".join(rows) + "\n"


def _make_pkg(tmp_path: pathlib.Path,
              strain_id: str = "AS-XXX",
              *,
              gene_csv_content: str | None = None,
              top_bgcs: tuple[str, ...] = ("BGC001",),
              with_triage: bool = True) -> pathlib.Path:
    """Build a synthetic Mamey package with the files the locus_map flow needs.

    Triage board lists `top_bgcs` in Corrected_rank order. Gene CSV defaults to
    one forward + one reverse gene for BGC001 if not provided.
    """
    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)

    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain_id}))
    (pkg / "manifest_short.json").write_text(json.dumps(
        {"strain_id": strain_id}))

    if with_triage:
        # BC2-408: Region column added (was missing) -- render_bgc_v8 (mamey/locus_map_v8.py,
        # P004 "V8 combined repair") requires strain/node/REGION/bgc_alias all populated and
        # raises "complete locus identity unavailable: region" otherwise. This fixture predates
        # that check and never carried one, breaking every test in this file that reaches the
        # default v8 renderer once P004 landed (confirmed: 10-11 of ~13 tests failed with exactly
        # that error on both the pre-seal composing tree and the sealed .407 release -- reported
        # pre-seal and independently confirmed by a peer review lane's own tracking note this
        # session; applied here on the .408 rebase).
        rows = ["BGC_ID,Node_ID,Products,Corrected_rank,Region"]
        for i, bgc in enumerate(top_bgcs, 1):
            rows.append(f"{bgc},NODE_{i},NRPS,{i},region{i:03d}")
        (pkg / f"{strain_id}_4_triage_board.csv").write_text("\n".join(rows) + "\n")

    if gene_csv_content is None:
        gene_csv_content = _gene_csv_text({"BGC001": [(1, "+"), (2, "-")]})
    (pkg / f"{strain_id}_gene_by_gene_all_bgcs.csv").write_text(gene_csv_content)

    return pkg


def _read_svg(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_render_for_compile_report_emits_svg_file(tmp_path):
    """Headline: the function produces a `<BGC_ID>_locus_map.svg` file."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = _make_pkg(tmp_path)
    res = render_for_compile_report(pkg)
    assert res["rendered"] == ["BGC001"], f"got: {res}"
    svg = pkg / "locus_maps" / "BGC001_locus_map.svg"
    assert svg.exists()


def test_svg_output_is_valid_xml(tmp_path):
    """W5 #1: SVG output parses as XML."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = _make_pkg(tmp_path)
    render_for_compile_report(pkg)
    svg_path = pkg / "locus_maps" / "BGC001_locus_map.svg"
    # ET.parse will raise ParseError if the SVG is malformed
    tree = ET.parse(svg_path)
    root = tree.getroot()
    # tag has the SVG namespace: '{http://www.w3.org/2000/svg}svg'
    assert root.tag.endswith("svg"), f"root not <svg>: {root.tag}"


# ---------------------------------------------------------------------------
# Regression: fmt="png" fallback for PDF pipelines without an SVG rasterizer
# (v9.7.151c+ — found via direct functional reproduction: a one-line
# markdown file containing a single `\includesvg{...}` reference is a HARD,
# FATAL xelatex error under `-halt-on-error` in any environment lacking
# Inkscape shell-escape or an rsvg-convert delegate, e.g. a sandboxed CI
# container with neither installed. `tools/md_to_pdf.sh` swallowed the
# failure inside its `set -e` trap with no PDF written and no error
# surfaced to the caller beyond a buried xelatex log. SVG output remains
# the correct default — it embeds fine in DOCX via pandoc's native
# .svgz support, and most LaTeX toolchains do have Inkscape — but a PNG
# escape hatch needs to exist and be regression-tested for the toolchains
# that don't.)
# ---------------------------------------------------------------------------

# BC2-408: v9.7.405 changed the DEFAULT renderer to "v8" (LOCUS_MAP_V8, an owner ruling --
# see render_for_compile_report's own docstring), which *always* emits both PNG and SVG and
# explicitly `del fmt` (locus_map_v8.py::render_for_compile_report_v8: "v8 always emits both
# PNG and SVG; `fmt` is accepted for API compatibility."). These two tests predate that change
# and assert the single-exclusive-format contract that only the "legacy" renderer still
# implements -- under the new default they failed not because of a regression, but because the
# tests were never updated to say which renderer they mean. Pin `renderer="legacy"` explicitly
# so each test keeps testing exactly what it always tested (the fmt parameter really does pick
# one exclusive format, on the renderer that honors that contract) instead of silently
# asserting something the current default was deliberately changed to no longer do.

def test_default_format_is_still_svg_no_signature_break(tmp_path):
    """Existing callers that don't pass fmt= must see identical behaviour
    to before this parameter was added — same filename, same extension.
    (legacy renderer only — v8 is covered by test_v8_default_emits_both_svg_and_png below)"""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = _make_pkg(tmp_path)
    res = render_for_compile_report(pkg, renderer="legacy")
    assert res["rendered"] == ["BGC001"]
    assert (pkg / "locus_maps" / "BGC001_locus_map.svg").exists()
    assert not (pkg / "locus_maps" / "BGC001_locus_map.png").exists()


def test_fmt_png_emits_png_not_svg(tmp_path):
    """legacy renderer only — see the BC2-408 note above test_default_format_is_still_svg."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = _make_pkg(tmp_path)
    res = render_for_compile_report(pkg, fmt="png", renderer="legacy")
    assert res["rendered"] == ["BGC001"]
    png_path = pkg / "locus_maps" / "BGC001_locus_map.png"
    assert png_path.exists()
    assert not (pkg / "locus_maps" / "BGC001_locus_map.svg").exists()
    # Real raster content, not a zero-byte stub.
    assert png_path.stat().st_size > 1000
    # PNG magic bytes.
    assert png_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_v8_default_emits_both_svg_and_png_regardless_of_fmt(tmp_path):
    """The CURRENT default renderer's actual, documented contract (v9.7.405 owner ruling):
    v8 always emits both formats and ignores fmt for format SELECTION. This is what was
    genuinely missing coverage for — the two tests above only ever pinned the legacy
    single-format contract, never the new default's real behaviour, so a regression in the
    default path (e.g. v8 silently dropping the PNG or SVG output) had no test to catch it."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = _make_pkg(tmp_path)
    res = render_for_compile_report(pkg)  # no renderer= -> current default (v8)
    assert res["rendered"] == ["BGC001"]
    assert res.get("renderer") == "v8"
    svg_path = pkg / "locus_maps" / "BGC001_locus_map.svg"
    png_path = pkg / "locus_maps" / "BGC001_locus_map.png"
    assert svg_path.exists()
    assert png_path.exists()
    assert png_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    # fmt is accepted but ignored for v8 (API compatibility only) -- both still emitted.
    res2 = render_for_compile_report(pkg, fmt="png")
    assert (pkg / "locus_maps" / "BGC001_locus_map.svg").exists()
    assert (pkg / "locus_maps" / "BGC001_locus_map.png").exists()


def test_fmt_invalid_value_falls_back_to_svg(tmp_path):
    """An unrecognised fmt string degrades to the safe default rather than
    raising or silently writing a garbage extension."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = _make_pkg(tmp_path)
    res = render_for_compile_report(pkg, fmt="jpeg")
    assert res["rendered"] == ["BGC001"]
    assert (pkg / "locus_maps" / "BGC001_locus_map.svg").exists()


def test_fmt_accepts_leading_dot_and_mixed_case(tmp_path):
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = _make_pkg(tmp_path)
    res = render_for_compile_report(pkg, fmt=".PNG")
    assert res["rendered"] == ["BGC001"]
    assert (pkg / "locus_maps" / "BGC001_locus_map.png").exists()


def test_svg_contains_vector_elements_for_gene_arrows(tmp_path):
    """W5 #2 (wishlist asked <rect>|<polygon>; matplotlib emits <path> for
    FancyArrow — relaxed to 'any vector primitive'). See W5 findings doc."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = _make_pkg(tmp_path)
    render_for_compile_report(pkg)
    svg = _read_svg(pkg / "locus_maps" / "BGC001_locus_map.svg")
    has_path = "<path " in svg
    has_polygon = "<polygon " in svg
    has_rect = "<rect " in svg
    assert has_path or has_polygon or has_rect, (
        "SVG must contain a vector primitive for the gene arrows"
    )


def test_strand_orientation_is_reflected_in_svg(tmp_path):
    """W5 #3: forward (+) and reverse (-) BGCs produce visibly different SVG.

    Compare a BGC with all-forward genes against one with all-reverse genes
    — the SVG path data must differ.
    """
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report

    # Two packages: same gene layout, different strands
    pkg_fwd = _make_pkg(
        tmp_path / "fwd",
        gene_csv_content=_gene_csv_text(
            {"BGC001": [(1, "+"), (2, "+"), (3, "+")]}),
    )
    pkg_rev = _make_pkg(
        tmp_path / "rev",
        gene_csv_content=_gene_csv_text(
            {"BGC001": [(1, "-"), (2, "-"), (3, "-")]}),
    )
    render_for_compile_report(pkg_fwd)
    render_for_compile_report(pkg_rev)

    fwd_svg = _read_svg(pkg_fwd / "locus_maps" / "BGC001_locus_map.svg")
    rev_svg = _read_svg(pkg_rev / "locus_maps" / "BGC001_locus_map.svg")
    # Drop matplotlib's per-render IDs/timestamps so we compare geometry
    import re
    norm_fwd = re.sub(r'id="[^"]*"', "", fwd_svg)
    norm_rev = re.sub(r'id="[^"]*"', "", rev_svg)
    assert norm_fwd != norm_rev, (
        "Forward and reverse strands should produce different SVG geometry"
    )


def test_svg_colour_varies_by_domain_class(tmp_path):
    """W5 #4: different gene_functions / sec_met_domains blobs (mapping to
    different palette roles) produce different SVG colours."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report

    # NRPS-like vs regulator — palette assigns different colours
    pkg_nrps = _make_pkg(
        tmp_path / "nrps",
        gene_csv_content=_gene_csv_text(
            {"BGC001": [(1, "+"), (2, "+")]},
            domain_blob="Condensation_LCL;AMP-binding;PCP"),
    )
    pkg_reg = _make_pkg(
        tmp_path / "reg",
        gene_csv_content=_gene_csv_text(
            {"BGC001": [(1, "+"), (2, "+")]},
            domain_blob="regulator"),
    )
    render_for_compile_report(pkg_nrps)
    render_for_compile_report(pkg_reg)

    nrps_svg = _read_svg(pkg_nrps / "locus_maps" / "BGC001_locus_map.svg")
    reg_svg  = _read_svg(pkg_reg / "locus_maps" / "BGC001_locus_map.svg")

    # Extract colour-like hex values from each SVG
    import re
    nrps_colours = set(re.findall(r"#[0-9a-fA-F]{6}", nrps_svg))
    reg_colours  = set(re.findall(r"#[0-9a-fA-F]{6}", reg_svg))
    assert nrps_colours != reg_colours, (
        f"Different domain classes must produce different colours; "
        f"NRPS={nrps_colours}, REG={reg_colours}"
    )


def test_non_blocking_when_csv_row_is_malformed(tmp_path):
    """W5 #5: a row with garbage start/end must not crash the renderer;
    valid sibling rows in the same BGC still render."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report

    bad_csv = (
        "bgc_id,locus_tag,gene_start,gene_end,strand,sec_met_domains,aa_length\n"
        "BGC001,ctg1_1,xxx,not-a-number,+,Condensation_LCL;AMP-binding,333\n"
        "BGC001,ctg1_2,2500,3500,+,Condensation_LCL;AMP-binding,333\n"
        "BGC001,ctg1_3,4000,5000,-,Condensation_LCL;AMP-binding,333\n"
    )
    pkg = _make_pkg(tmp_path, gene_csv_content=bad_csv)
    res = render_for_compile_report(pkg)
    # Should NOT have raised; BGC001 should still render (from the 2 valid rows)
    assert "BGC001" in res["rendered"], f"got: {res}"
    assert (pkg / "locus_maps" / "BGC001_locus_map.svg").exists()


def test_top_n_selection_from_triage_board(tmp_path):
    """Bonus: top-N is honored — only the first N BGCs by Corrected_rank get
    rendered. The remaining BGCs in the gene CSV are not rendered."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report

    # 4 BGCs in triage + gene CSV; top_n=2 should render only BGC001, BGC002
    pkg = _make_pkg(
        tmp_path,
        gene_csv_content=_gene_csv_text({
            "BGC001": [(1, "+"), (2, "+")],
            "BGC002": [(1, "+"), (2, "-")],
            "BGC003": [(1, "+"), (2, "+")],
            "BGC004": [(1, "-"), (2, "-")],
        }),
        top_bgcs=("BGC001", "BGC002", "BGC003", "BGC004"),
    )
    res = render_for_compile_report(pkg, top_n=2)
    assert set(res["rendered"]) == {"BGC001", "BGC002"}, f"got: {res}"
    assert not (pkg / "locus_maps" / "BGC003_locus_map.svg").exists()
    assert not (pkg / "locus_maps" / "BGC004_locus_map.svg").exists()


def test_missing_gene_csv_degrades_silently(tmp_path):
    """Bonus: no gene_by_gene CSV → empty rendered, no raise."""
    pytest.importorskip("matplotlib")
    from mamey.locus_map import render_for_compile_report
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-XXX"}))
    res = render_for_compile_report(pkg)
    assert res["rendered"] == []
    assert "gene_by_gene" in (res["skipped_reason"] or "")
