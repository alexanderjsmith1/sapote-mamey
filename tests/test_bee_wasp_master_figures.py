import csv
import zipfile
from pathlib import Path

from mamey.master_figure_atlas import _short, _wrap, read_xlsx_table, render_master_figure_atlas
import pytest

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow


def _sheet_xml(rows):
    def cell_ref(col, row):
        s = ""
        col += 1
        while col:
            col, rem = divmod(col - 1, 26)
            s = chr(65 + rem) + s
        return f"{s}{row}"
    def esc(v):
        return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for r_idx, row in enumerate(rows, 1):
        parts.append(f'<row r="{r_idx}">')
        for c_idx, val in enumerate(row):
            ref = cell_ref(c_idx, r_idx)
            if isinstance(val, (int, float)):
                parts.append(f'<c r="{ref}"><v>{val}</v></c>')
            elif val is None:
                continue
            else:
                parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{esc(val)}</t></is></c>')
        parts.append('</row>')
    parts.append('</sheetData></worksheet>')
    return "".join(parts)


def _make_fixture_xlsx(path: Path):
    sheets = {
        "Strain_Summary": [
            ["strain_id", "display_name", "genome_bp", "contigs", "n50", "gc_pct", "raw_bgcs", "corrected_bgcs", "interior_bgcs", "edge_bgcs", "full_contig_bgcs", "interior_pct", "assembly_tier", "rggmci_high_pairs", "top_antibacterial_locator", "top_antibacterial_products", "top_antibacterial_score", "top_antifungal_locator", "top_antifungal_products", "top_antifungal_score"],
            ["AS-1", "Streptomyces sp. AS-1", 7000000, 100, 50000, 72.1, 50, 30.5, 12, 10, 28, 24.0, "POOR", 3, "NODE_1 (BGC001)", "RiPP; lanthipeptide", 81.0, "NODE_2 (BGC002)", "NRPS; PKS", 42.0],
            ["AS-2", "Actinomycete sp. AS-2", 8000000, 200, 20000, 69.1, 60, 20.0, 3, 12, 45, 5.0, "VERY_POOR", 5, "NODE_3 (BGC003)", "nucleoside; other", 90.0, "NODE_4 (BGC004)", "nucleoside; other", 72.0],
        ],
        "Special_Buckets": [
            ["strain_id", "nucleoside_priority_rows", "polyene_ptm_flag_rows", "other_token_rows", "rggmci_high_pairs", "note"],
            ["AS-1", 2, 1, 10, 3, "demo"],
            ["AS-2", 5, 0, 8, 5, "demo"],
        ],
        "Top_Antibacterial": [
            ["strain_id", "rank", "assembly_locator", "bgc_id", "products", "antibacterial_score", "kcb_top_context"],
            ["AS-1", 1, "NODE_1 (BGC001)", "BGC001", "RiPP", 81.0, "BGC0000001 | demo | knownclusterblast #1"],
            ["AS-2", 1, "NODE_3 (BGC003)", "BGC003", "nucleoside", 90.0, "BGC0000002 | demo2 | knownclusterblast #1"],
        ],
        "Top_Antifungal": [
            ["strain_id", "rank", "assembly_locator", "bgc_id", "products", "antifungal_score", "kcb_top_context"],
            ["AS-1", 1, "NODE_2 (BGC002)", "BGC002", "NRPS; PKS", 42.0, "BGC0000003 | demo3 | knownclusterblast #1"],
            ["AS-2", 1, "NODE_4 (BGC004)", "BGC004", "nucleoside", 72.0, "BGC0000004 | demo4 | knownclusterblast #1"],
        ],
    }
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "")
        z.writestr("xl/workbook.xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>
<sheet name="Strain_Summary" sheetId="1" r:id="rId1"/><sheet name="Special_Buckets" sheetId="2" r:id="rId2"/><sheet name="Top_Antibacterial" sheetId="3" r:id="rId3"/><sheet name="Top_Antifungal" sheetId="4" r:id="rId4"/>
</sheets></workbook>''')
        z.writestr("xl/_rels/workbook.xml.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet4.xml"/>
</Relationships>''')
        for i, rows in enumerate(sheets.values(), 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows))


def test_wrap_prefers_word_boundaries():
    wrapped = _wrap("alpha beta gamma delta epsilon zeta", width=12, max_lines=2)
    assert "\n" in wrapped
    assert not wrapped.endswith(" ")


def test_short_truncates_with_ellipsis_at_word_boundary():
    s = _short("this is a deliberately very long label for a plot", 20)
    assert s.endswith("…")
    assert len(s) <= 20


def test_read_xlsx_table_stdlib_fixture(tmp_path):
    wb = tmp_path / "fixture.xlsx"
    _make_fixture_xlsx(wb)
    rows = read_xlsx_table(wb, "Strain_Summary")
    assert len(rows) == 2
    assert rows[0]["strain_id"] == "AS-1"
    assert rows[1]["assembly_tier"] == "VERY_POOR"


def test_render_master_figure_atlas_outputs_all_figures(tmp_path):
    wb = tmp_path / "fixture.xlsx"
    _make_fixture_xlsx(wb)
    out = tmp_path / "figures"
    result = render_master_figure_atlas(wb, out, make_zip=False)
    assert result["status"] == "PASS"
    assert result["n_strains"] == 2
    assert len(result["figures"]) == 6
    for fig in result["figures"]:
        assert Path(fig["png"]).exists()
        assert Path(fig["source_csv"]).exists()
        sidecar = list(csv.reader(open(fig["source_csv"])))
        assert sidecar[0][0] == "# provenance"
    assert (out / "FIGURE_REMAKE_GUIDE.md").exists()


def test_figure_id_contract_sidecars_index_and_pdf(tmp_path):
    wb = tmp_path / "fixture.xlsx"
    _make_fixture_xlsx(wb)
    out = tmp_path / "figures"
    result = render_master_figure_atlas(wb, out, make_zip=False)
    assert result["status"] == "PASS"
    index = out / "FIGURE_INDEX.csv"
    assert index.exists()
    rows = list(csv.DictReader(open(index, newline="", encoding="utf-8")))
    assert rows
    visible_ids = {r["visible_id"] for r in rows}
    assert "CSA18-01" in visible_ids
    for fig in result["figures"]:
        assert fig["visible_id"] in Path(fig["png"]).name
        assert Path(fig["svg"]).exists()
        assert Path(fig["pdf"]).exists()
        sidecar = Path(fig["sidecar_md"])
        assert sidecar.exists()
        txt = sidecar.read_text(encoding="utf-8")
        assert fig["long_id"] in txt
        assert "## Claim ceiling" in txt


def test_dual_priority_atlas_uses_node_first_visible_labels(tmp_path):
    wb = tmp_path / "fixture.xlsx"
    _make_fixture_xlsx(wb)
    out = tmp_path / "figures"
    result = render_master_figure_atlas(wb, out, make_zip=False)
    dual = next(fig for fig in result["figures"] if fig["visible_id"] == "CSA18-01")
    csv_text = Path(dual["source_csv"]).read_text(encoding="utf-8")
    assert "visible_label" in csv_text
    assert "AB NODE_1 · AF NODE_2" in csv_text
    assert "BGC001" in csv_text  # traceability remains in locator columns/source data
    # The SVG should expose text labels and not depend on hidden path-rendered text.
    svg_text = Path(dual["svg"]).read_text(encoding="utf-8")
    assert "Card ID: CSA18-01" in svg_text
    assert "AB NODE_1" in svg_text
    assert "(BGC" not in svg_text


def test_even_count_median_uses_average_not_upper_middle(tmp_path):
    wb = tmp_path / "fixture.xlsx"
    _make_fixture_xlsx(wb)
    out = tmp_path / "figures"
    result = render_master_figure_atlas(wb, out, make_zip=False)
    dual = next(fig for fig in result["figures"] if fig["visible_id"] == "CSA18-01")
    svg_text = Path(dual["svg"]).read_text(encoding="utf-8")
    assert "AB median = 85.5" in svg_text
    assert "AF median = 57.0" in svg_text


def test_label_position_overrides_have_distinct_real_keys():
    """Guards the FIXED v9.7.308 state of the dual-priority-atlas label offsets.

    History: _fig_dual_priority_atlas used to hold a 10-entry dict literal whose keys were all
    the placeholder "AS-XXX". Python keeps only the last duplicate key, so 9 of the 10 hand-tuned
    offsets were dead and none ever fired (real strain IDs are never literally "AS-XXX"). That
    dead dict was replaced by the module constant LABEL_POSITION_OVERRIDES (keyed by real strain
    ID, empty by default) plus a preserved reference list of the 10 authored tuples.

    This test now guards the INVARIANT rather than the breakage: the override map must never
    reintroduce duplicate or placeholder keys at the source level, its values must be valid
    (x, y, ha) tuples, and the preserved authored-offset reference must survive. It intentionally
    allows the map to be empty (the current, behavior-preserving state) or to be filled with real
    distinct strain IDs later (a real fix) -- it only fails on a regression toward the old bug.
    """
    import ast
    import mamey.master_figure_atlas as mfa

    # Runtime shape.
    assert isinstance(mfa.LABEL_POSITION_OVERRIDES, dict)
    for sid, val in mfa.LABEL_POSITION_OVERRIDES.items():
        assert isinstance(sid, str) and sid, f"override key not a non-empty str: {sid!r}"
        assert "XXX" not in sid, f"placeholder key leaked into LABEL_POSITION_OVERRIDES: {sid!r}"
        assert (
            isinstance(val, tuple) and len(val) == 3 and val[2] in {"left", "right", "center"}
        ), f"override value for {sid!r} is not an (x, y, ha) tuple: {val!r}"

    # Source-level: catch duplicate/placeholder key literals that dict runtime would silently hide.
    src = ast.parse(open(mfa.__file__).read())
    dict_node = None
    for node in ast.walk(src):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "LABEL_POSITION_OVERRIDES":
            dict_node = node.value
            break
    assert isinstance(dict_node, ast.Dict), "LABEL_POSITION_OVERRIDES literal not found -- source moved?"
    literal_keys = [k.value for k in dict_node.keys if isinstance(k, ast.Constant)]
    assert len(literal_keys) == len(set(literal_keys)), (
        f"duplicate key literals in LABEL_POSITION_OVERRIDES: {literal_keys} -- the old "
        "collapse-to-last bug is back."
    )
    assert not any("XXX" in str(k) for k in literal_keys), (
        f"placeholder key literal in LABEL_POSITION_OVERRIDES: {literal_keys}"
    )

    # The 10 authored offsets must be preserved as reference for the pending editorial mapping.
    assert len(mfa._AUTHORED_LABEL_OFFSETS_PENDING_MAPPING) == 10
