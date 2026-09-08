"""v9.7.349x — smoke test for the five graduated widget/analysis deliverable tools.

Five ad-hoc strain_data generators were graduated into the engine as first-class,
path-agnostic deliverable tools with wired post-seal, non-blocking CLI subcommands:

  * deliverable_tools/overmerge_widget.py      -> `mamey overmerge-widgets`
  * deliverable_tools/rggmci_widget.py         -> `mamey rggmci-widget`
  * deliverable_tools/assembly_line_widget.py  -> `mamey assembly-line-widget`
  * deliverable_tools/af_leadboard_widget.py   -> `mamey af-leadboard`
  * deliverable_tools/split_cards.py           -> `mamey split-overmerge-cards`
  * deliverable_tools/_widget_paths.py         (shared, de-duplicated path helper)

This test asserts, WITHOUT needing any of the (large, un-shipped) workspace inputs:
  1. the six deliverable_tools modules import and expose their reusable render/build APIs;
  2. each of the five subcommands is registered and parses its arguments;
  3. each command is non-blocking / gated on inputs — a missing input returns a clean
     non-zero (no traceback), never raises;
  4. the widget HTML templates are self-contained (no external asset URLs) and carry the
     claim-safety ceiling.

Real renders are exercised only if the documented workspace inputs are present on disk
(skipped otherwise, so the suite stays hermetic).
"""
import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DT = os.path.join(REPO_ROOT, "deliverable_tools")

TOOL_MODULES = [
    "_widget_paths",
    "overmerge_widget",
    "rggmci_widget",
    "assembly_line_widget",
    "af_leadboard_widget",
    "split_cards",
]


def _load(name):
    if DT not in sys.path:
        sys.path.insert(0, DT)
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)  # so overmerge_widget can import mamey.scoring
    path = os.path.join(DT, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_deliverable_tools_modules_present():
    for name in TOOL_MODULES:
        assert os.path.exists(os.path.join(DT, name + ".py")), \
            f"missing deliverable_tools/{name}.py"


def test_shared_path_helper_imports():
    p = _load("_widget_paths")
    assert isinstance(p.ROOT_DEFAULT, str) and p.ROOT_DEFAULT
    for fn in ("master_dir", "runs_root", "blastp_repo", "module_dir"):
        assert callable(getattr(p, fn)), f"_widget_paths.{fn} missing"


def test_overmerge_widget_api():
    m = _load("overmerge_widget")
    assert callable(m.render_overmerge)
    assert callable(m.build_widget)
    assert callable(m.score)  # uses mamey.scoring auto-floor keyword scorers
    assert "src=" not in m.TEMPLATE and "cdn" not in m.TEMPLATE.lower()
    assert "judgment deferred" in m.TEMPLATE.lower()


def test_overmerge_index_blank_bgc_shows_placeholder(tmp_path):
    """v9.7.413 BC2 — the canonical OVERMERGE_REGISTER_GBK.tsv has real rows with an empty `bgc`
    field: regions flagged OVER_MERGED that carry no corrected-BGC alias (45 of 180 on a real
    render). `write_index` rendered `esc(b['bgc'])` with no fallback — a bare empty <td></td> that
    reads as a broken render rather than as 'unresolved'. The sibling `kinds` column one line below
    already falls back to '—'; BGC was the one column not following the file's own convention.
    The region stays fully identified by strain+node+region either way; this is legibility only."""
    m = _load("overmerge_widget")
    built = [{
        "strain": "AS-000", "bgc": "", "n_pc": 3, "products": ["T1PKS", "NRPS-like"],
        "kinds": ["neighbouring", "single"], "union_ab": 40, "deinf_ab": 30,
        "delta": 10.0, "fname": "AS-000_NODE_1_length_1000_region001_overmerge.html",
    }]
    html = open(m.write_index(built, [], str(tmp_path))).read()
    assert "<td></td>" not in html, "blank bgc rendered as a bare empty cell, not a placeholder"
    assert "<td>—</td>" in html, "expected the em-dash placeholder already used for blank kinds"


def test_rggmci_widget_api():
    m = _load("rggmci_widget")
    assert callable(m.render)
    assert callable(m.build)
    assert callable(m.discover)
    assert "src=" not in m.TEMPLATE and "cdn" not in m.TEMPLATE.lower()
    assert "judgment" in m.TEMPLATE.lower()


def test_assembly_line_widget_api():
    m = _load("assembly_line_widget")
    assert callable(m.render)
    assert callable(m.build_payload)
    assert isinstance(m.CATS, list) and m.CATS
    assert "src=" not in m.TEMPLATE and "cdn" not in m.TEMPLATE.lower()
    assert "judgment deferred" in m.TEMPLATE.lower()


def test_assembly_line_gene_kind_label_not_truncated():
    """v9.7.413 BC2 — the gene-lane label (`${g.aa} aa · ${g.kind}`) hard-slices antiSMASH's own
    gene_kind qualifier to a fixed character cap. That controlled vocabulary
    (mamey/clusterblast_genes.py) includes 'biosynthetic-additional' (23 chars) alongside
    'biosynthetic' / 'transport' / 'regulatory' / 'other'. A cap narrower than 23 renders the
    longest real value as a garbled fragment ('biosynthetic-additio') with no ellipsis to signal
    the cut — confirmed on live AS-747 and AS-760 renders. The label column (LEFT=196px) has ample
    room for the full string, so the cap was never a layout constraint. A fixed cap stays, matching
    this file's defensive-length convention; it just has to clear the real vocabulary."""
    import re
    m = _load("assembly_line_widget")
    match = re.search(r'g\.kind\|\|""\)\.slice\(0,\s*(\d+)\)', m.TEMPLATE)
    assert match, "expected the gene-lane label to slice g.kind by a fixed character cap"
    cap = int(match.group(1))
    longest_known_gene_kind = "biosynthetic-additional"  # antiSMASH controlled vocabulary
    assert cap >= len(longest_known_gene_kind), (
        f"gene_kind label cap ({cap}) truncates the antiSMASH value "
        f"{longest_known_gene_kind!r} ({len(longest_known_gene_kind)} chars) with no ellipsis"
    )


def test_assembly_line_render_html_embeds_full_gene_kind():
    """Control: the server-side payload always carried gene_kind untruncated — only the
    client-side JS label ever had a cap. Pins that, so a future 'fix' that truncates at
    build_payload time instead of at render time is caught."""
    m = _load("assembly_line_widget")
    payload = {
        "strain": "AS-000",
        "bgcs": [{
            "bgc_id": "BGC001", "products": "PKS", "boundary": "interior",
            "n_domains": 0, "n_modules": 0, "n_complete": 0,
            "genes": [{"locus": "ctg1_1", "aa": 100, "product": "",
                       "kind": "biosynthetic-additional", "strand": 1, "gstart": 0,
                       "domains": []}],
            "modules": [],
        }],
    }
    assert "biosynthetic-additional" in m.render_html(payload)


def test_af_leadboard_widget_api():
    m = _load("af_leadboard_widget")
    assert callable(m.build)
    assert callable(m.build_leads)
    assert "src=" not in m.TEMPLATE and "cdn" not in m.TEMPLATE.lower()
    assert "judgment is deferred" in m.TEMPLATE.lower()


def test_split_cards_api():
    m = _load("split_cards")
    assert callable(m.run_fixer)
    assert callable(m.process_card)
    assert m.MARKER_RE is not None  # idempotent QCFIX marker regex


def test_all_subcommands_registered_and_parse():
    from mamey.cli import build_parser
    parser = build_parser()
    cases = {
        "overmerge_widgets_command": [
            "overmerge-widgets", "--register", "/tmp/nope.tsv", "--out", "/tmp/o"],
        "rggmci_widget_command": [
            "rggmci-widget", "--strain", "AS-320", "--out", "/tmp/o"],
        "assembly_line_widget_command": [
            "assembly-line-widget", "--demo", "--out", "/tmp/o"],
        "af_leadboard_command": [
            "af-leadboard", "--master-csv", "/tmp/m.csv", "--out", "/tmp/o"],
        "split_overmerge_cards_command": [
            "split-overmerge-cards", "--manifest", "/tmp/x.tsv", "--dry-run", "--limit", "3"],
    }
    for expected_func, argv in cases.items():
        ns = parser.parse_args(argv)
        assert ns.func.__name__ == expected_func, f"{argv[0]} -> {ns.func.__name__}"


def test_commands_are_non_blocking_when_inputs_absent(tmp_path, capsys):
    """Every command returns non-zero cleanly (no traceback) when its inputs are absent."""
    from mamey.cli import build_parser
    parser = build_parser()
    absent = str(tmp_path)
    cases = [
        ["overmerge-widgets", "--register", absent + "/absent.tsv", "--out", absent + "/o"],
        ["rggmci-widget", "--strain", "AS-999", "--runs-root", absent, "--out", absent + "/o"],
        ["assembly-line-widget", "--strain", "AS-999", "--runs-root", absent, "--out", absent + "/o"],
        ["af-leadboard", "--master-csv", absent + "/absent.csv", "--out", absent + "/o"],
        ["split-overmerge-cards", "--manifest", absent + "/absent.tsv"],
    ]
    for argv in cases:
        ns = parser.parse_args(argv)
        rc = ns.func(ns)  # must not raise
        assert rc == 1, f"{argv[0]} should return 1 when inputs absent (got {rc})"


def test_missing_required_selector_is_non_blocking(capsys):
    """rggmci-widget / assembly-line-widget with no strain and no --all/--demo return 1."""
    from mamey.cli import build_parser
    parser = build_parser()
    for argv in (["rggmci-widget"], ["assembly-line-widget"]):
        ns = parser.parse_args(argv)
        rc = ns.func(ns)
        assert rc == 1


# --- optional real renders (skipped unless the documented inputs exist) -------
def test_rggmci_real_render_if_present(tmp_path):
    m = _load("rggmci_widget")
    found = m.discover()
    if not found:
        pytest.skip("no *_4A_RGGMCI_ranked_pairs.csv present")
    strain = sorted(found)[0]
    res = m.render(strain=strain, outdir=str(tmp_path))
    assert res["n"] >= 1
    for _s, _n, _e, outp in res["built"]:
        assert os.path.exists(outp)


def test_overmerge_real_render_if_present(tmp_path):
    m = _load("overmerge_widget")
    if not os.path.exists(m.DEFAULT_REGISTER):
        pytest.skip(f"over-merge register not present ({m.DEFAULT_REGISTER})")
    res = m.render_overmerge(register=m.DEFAULT_REGISTER, outdir=str(tmp_path))
    assert os.path.exists(res["index"])
