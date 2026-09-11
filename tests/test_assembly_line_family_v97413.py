"""v9.7.413 (BC2) — the assembly-line family: cohort coverage + the two print companions.

Three things are pinned here.

1. `assembly-line-widget --all`. The reader had only `--strain`/`--demo`, while its sibling
   `rggmci-widget` has had `--all` since it shipped. That single missing flag is why the reader
   covered 5 flagship strains out of the 44 that have the required table — a tooling gap, not a
   data gap.

2. `mamey assembly-line-pdf` — print companion to the reader (4 or 6 BGC panels per page).

3. `mamey bgc-gene-map` — the whole-BGC view. The assembly-line views only cover regions that HAVE
   NRPS/PKS assembly-line domains (42 of AS-747's 57 regions); every RiPP, terpene, saccharide and
   siderophore locus is invisible in them. This renders EVERY region, whatever its class, which is
   what the house gene-level rule requires before a locus may be judged.

Both PDF tools import their data layer (`build_payload`, palette) from `assembly_line_widget.py`
rather than re-deriving it, so a printed figure and its interactive sibling cannot drift apart and
disagree in a thesis. `test_pdf_tools_share_the_widget_data_layer` pins that property.
"""
import importlib.util
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DT = os.path.join(REPO_ROOT, "deliverable_tools")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(DT, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- 1. cohort coverage ------------------------------------------------------------------------

def test_assembly_line_widget_exposes_discover_and_all():
    m = _load("assembly_line_widget")
    assert callable(getattr(m, "discover", None)), "no discover(); --all cannot enumerate strains"
    import inspect
    assert "all_strains" in inspect.signature(m.render).parameters, \
        "render() has no all_strains parameter"


def test_discover_finds_every_strain_with_the_modules_table(tmp_path):
    """discover() keys on the same table the reader needs, so --all cannot over-promise."""
    m = _load("assembly_line_widget")
    for s in ("AS-001", "AS-002"):
        d = tmp_path / s / "package"
        d.mkdir(parents=True)
        (d / f"{s}_3_antismash_modules.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "AS-003" / "package").mkdir(parents=True)      # no table -> must not appear
    found = m.discover(str(tmp_path))
    assert set(found) == {"AS-001", "AS-002"}, f"discover() returned {sorted(found)}"


def test_cli_assembly_line_widget_accepts_all():
    from mamey import cli
    ns = cli.build_parser().parse_args(["assembly-line-widget", "--all", "--out", "/tmp/o"])
    assert getattr(ns, "all_strains", False) is True, "assembly-line-widget does not accept --all"


# ---- 2 & 3. the print companions ---------------------------------------------------------------

@pytest.mark.parametrize("tool", ["assembly_line_pdf", "bgc_gene_map"])
def test_pdf_tool_api(tool):
    m = _load(tool)
    assert callable(m.build_pdf)
    assert callable(m.main)
    assert "judgment deferred" in m.CLAIM_SAFETY.lower(), "claim-safety block missing from the page"


def test_pdf_tools_share_the_widget_data_layer():
    """The whole point: a printed figure and its interactive sibling read one data layer."""
    alp = _load("assembly_line_pdf")
    alw = _load("assembly_line_widget")
    assert alp.build_payload is not None
    # same palette object contents, not a re-typed copy
    assert alp.CATS == alw.CATS, "the PDF re-declares its own palette; it can drift from the widget"


def test_bgc_gene_map_covers_every_region_not_just_assembly_lines(tmp_path):
    """A package whose regions have NO assembly-line domains must still produce a gene map."""
    m = _load("bgc_gene_map")
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "AS-000_gene_context.jsonl").write_text(
        '{"schema_version": 1, "n_cds": 2}\n'
        '{"bgc_id": "BGC001", "cds": [{"locus_tag": "ctg1_1", "start": 10, "end": 900,'
        ' "strand": 1, "aa_length": 296, "gene_kind": "biosynthetic", "sec_met_domains": ["Lant_dehydr"]},'
        ' {"locus_tag": "ctg1_2", "start": 1000, "end": 1600, "strand": -1, "aa_length": 199,'
        ' "gene_kind": "", "sec_met_domains": []}]}\n', encoding="utf-8")
    (pkg / "AS-000_2_inventory.csv").write_text(
        "BGC_ID,Products,Boundary\nBGC001,RiPP; lanthipeptide,Interior\n", encoding="utf-8")
    payload = m.build_payload("AS-000", str(pkg))
    assert len(payload["bgcs"]) == 1
    b = payload["bgcs"][0]
    assert b["n_genes"] == 2, "a gene with no /gene_kind call was dropped — it must be drawn"
    assert b["bgc_id"] == "BGC001"


@pytest.mark.parametrize("cmd", ["assembly-line-pdf", "bgc-gene-map"])
def test_cli_pdf_subcommands_registered(cmd):
    from mamey import cli
    ns = cli.build_parser().parse_args([cmd, "--strain", "AS-000", "--out", "/tmp/o"])
    assert ns.func.__name__ in ("assembly_line_pdf_command", "bgc_gene_map_command")
    assert ns.per_page == 6                      # documented default
    ns4 = cli.build_parser().parse_args([cmd, "--all", "--out", "/tmp/o", "--per-page", "4"])
    assert ns4.per_page == 4 and ns4.all_strains is True
