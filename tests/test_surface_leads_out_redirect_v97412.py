"""v9.7.412 (BC2) — `surface-leads` must be able to write somewhere other than the canonical
dated deliverable folder.

`deliverable_tools/surface_flagged_leads.py` hardcoded BOTH its input and its output under
`MAMEY_DATA_ROOT`, and `mamey surface-leads` accepted no arguments at all
(`usage: mamey surface-leads [-h]`). Because the workspace's `strain_data` is a symlink to the
canonical home (`AS Strain Master`), running the command once — to see what it does, to check it
still works, to reproduce a number — rewrote the real dated deliverable in place, with no
`--out`, no `--dry-run` and no warning. Observed on 2026-09-07 against the real workspace: a run
rewrote `flagged_lead_surfacing_2026-08-05/FLAGGED_LEAD_SURFACING.md` and
`flagged_lead_surfacing.csv` at the canonical path.

The sibling tool in the same dispatcher family (`majority-read` ->
`whole_bgc_majority_read.py`) already takes `--out` and the dispatcher already forwards it;
`surface-leads` was the one that did not. These tests pin both halves: the tool honours `--out`,
and the CLI accepts and forwards it.

Scope: output-location only. No scan, scorer, tier, gate, or emitted scientific value is touched;
the default path is unchanged, so existing invocations behave exactly as before.
"""
import csv
import importlib.util
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(REPO_ROOT, "deliverable_tools", "surface_flagged_leads.py")

COHORT_COLS = ["strain", "bgc_id", "products", "boundary", "hit_genes", "total_genes",
               "query_gene_share", "median_pct_identity", "anchor_compound",
               "class_concordance", "anchor_gene_types", "flags"]


def _write_cohort(path):
    """Minimal cohort CSV with one Group-A and one Group-B row."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = [
        {"strain": "AS-000", "bgc_id": "BGC001", "products": "T1PKS", "boundary": "Edge",
         "hit_genes": "3", "total_genes": "10", "query_gene_share": "0.30",
         "median_pct_identity": "72", "anchor_compound": "examplemycin",
         "class_concordance": "match", "anchor_gene_types": "KS,AT", "flags": "PROMISCUOUS_ONLY"},
        {"strain": "AS-000", "bgc_id": "BGC002", "products": "NRPS", "boundary": "Interior",
         "hit_genes": "2", "total_genes": "8", "query_gene_share": "0.25",
         "median_pct_identity": "48", "anchor_compound": "examplopeptin",
         "class_concordance": "match", "anchor_gene_types": "C,A", "flags": "LOW_ID"},
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COHORT_COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _load_tool(data_root):
    """Load the tool with MAMEY_DATA_ROOT already set (its paths are module-level constants)."""
    spec = importlib.util.spec_from_file_location("surface_flagged_leads_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_surface_leads_out_does_not_touch_the_canonical_folder(tmp_path, monkeypatch):
    """--out redirects BOTH artefacts and leaves the canonical dated folder untouched."""
    data_root = tmp_path / "workspace"
    _write_cohort(str(data_root / "strain_data" / "whole_bgc_majority_read_2026-08-05"
                      / "whole_bgc_majority_read_cohort.csv"))
    canonical = data_root / "strain_data" / "flagged_lead_surfacing_2026-08-05"
    alt = tmp_path / "redirected"

    monkeypatch.setenv("MAMEY_DATA_ROOT", str(data_root))
    mod = _load_tool(data_root)
    monkeypatch.setattr(sys, "argv", ["surface_flagged_leads", "--out", str(alt)])
    rc = mod.main()

    assert rc == 0
    assert (alt / "flagged_lead_surfacing.csv").is_file(), "--out did not redirect the CSV"
    assert (alt / "FLAGGED_LEAD_SURFACING.md").is_file(), "--out did not redirect the markdown"
    # the point of the flag: an exploratory run must not rewrite the canonical deliverable
    assert not (canonical / "flagged_lead_surfacing.csv").exists(), \
        "--out given, yet the canonical dated deliverable was written anyway"
    assert not (canonical / "FLAGGED_LEAD_SURFACING.md").exists(), \
        "--out given, yet the canonical dated deliverable was written anyway"


def test_surface_leads_default_output_location_is_unchanged(tmp_path, monkeypatch):
    """Control: with no --out, the canonical dated folder is still where it writes."""
    data_root = tmp_path / "workspace"
    _write_cohort(str(data_root / "strain_data" / "whole_bgc_majority_read_2026-08-05"
                      / "whole_bgc_majority_read_cohort.csv"))
    canonical = data_root / "strain_data" / "flagged_lead_surfacing_2026-08-05"

    monkeypatch.setenv("MAMEY_DATA_ROOT", str(data_root))
    mod = _load_tool(data_root)
    monkeypatch.setattr(sys, "argv", ["surface_flagged_leads"])
    rc = mod.main()

    assert rc == 0
    assert (canonical / "flagged_lead_surfacing.csv").is_file()
    assert (canonical / "FLAGGED_LEAD_SURFACING.md").is_file()


def test_cli_surface_leads_accepts_and_forwards_out():
    """`mamey surface-leads --out DIR` parses, and the dispatcher forwards it to the tool."""
    from mamey import cli
    parser = cli.build_parser()
    ns = parser.parse_args(["surface-leads", "--out", "/tmp/somewhere"])
    assert getattr(ns, "out", None) == "/tmp/somewhere", \
        "surface-leads does not accept --out"
    assert ns.func.__name__ == "_flagged_lead_command"

    # the dispatcher must actually pass it through to the tool's argv, not silently drop it
    import inspect
    src = inspect.getsource(cli._flagged_lead_command)
    assert 'surface-leads' in src and '"--out"' in src, \
        "dispatcher does not forward --out for surface-leads"
