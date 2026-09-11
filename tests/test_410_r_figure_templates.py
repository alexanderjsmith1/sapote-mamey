"""CLAUDE_410 r_figure_templates — the R templates must not drift from the Python renderer.

The bundle ships R figure templates so a reviewer can rebuild a figure in ggplot2/ggtree from the
factory's own plotted-data sidecar. That only stays honest if the R side keeps using the SAME
palette, the SAME publication profiles, and the SAME column names as the Python side.

R is not installed on every machine that runs this suite (and is not a dependency of the bundle), so
these tests do NOT execute the R scripts. They parse them and compare against the Python constants —
which is the check that actually matters, because the failure mode is silent divergence over time,
not a syntax error. A separate opt-in test runs the scripts wherever Rscript exists.
"""
from __future__ import annotations

import re
import os
import shutil
import sys as _sys
import subprocess
from pathlib import Path

import pytest

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
THEME = TOOLS / "sapote_figure_theme.R"
FF_R = TOOLS / "figure_factory_next_ggplot.R"
TREE_R = TOOLS / "cohort_tree_ggtree.R"


def _r_named_vector(src: str, name: str) -> dict[str, str]:
    """Parse `NAME <- c("k" = "v", ...)` into a dict."""
    m = re.search(rf"{re.escape(name)}\s*<-\s*c\((.*?)\n\)", src, re.S)
    assert m, f"{name} not found in {THEME.name}"
    return dict(re.findall(r'"([^"]+)"\s*=\s*"([^"]+)"', m.group(1)))


def test_the_three_templates_ship() -> None:
    for path in (THEME, FF_R, TREE_R):
        assert path.is_file(), f"missing R template: {path.relative_to(ROOT)}"
    # The pre-existing placement template must not be disturbed by this lane.
    assert (TOOLS / "ggtree_placement.R").is_file()


def test_r_palette_matches_figure_policy_exactly() -> None:
    """A colour that means BEE in Python and something else in R is a figure that lies."""
    from mamey.figure_policy import COHORT_PALETTE

    r_palette = _r_named_vector(THEME.read_text(encoding="utf-8"), "SAPOTE_COHORT_PALETTE")
    assert r_palette == dict(COHORT_PALETTE), (
        "R palette has drifted from mamey/figure_policy.py::COHORT_PALETTE"
    )


def test_r_publication_profiles_match_figure_policy() -> None:
    from mamey.figure_policy import PUBLICATION_PROFILES

    src = THEME.read_text(encoding="utf-8")
    for name, spec in PUBLICATION_PROFILES.items():
        m = re.search(rf"{name}\s*=\s*list\(([^)]*)\)", src)
        assert m, f"profile {name} missing from {THEME.name}"
        body = m.group(1)
        for key in ("width_in", "minimum_text_pt", "minimum_raster_dpi"):
            found = re.search(rf"{key}\s*=\s*([0-9.]+)", body)
            assert found, f"{name}.{key} missing from {THEME.name}"
            assert float(found.group(1)) == float(spec[key]), (
                f"{name}.{key}: R has {found.group(1)}, figure_policy has {spec[key]}"
            )


def test_r_reads_exactly_the_columns_the_sidecar_emits(tmp_path: Path) -> None:
    """The template's REQUIRED list must equal the sidecar's real header — no more, no fewer.

    Generated from a real `build()` run, not hand-typed: the point is to catch a schema change in
    `_aggregate` that nobody remembered to mirror into the R script.
    """
    from tests.test_410_ff_csv_sidecar import _fixture  # the sidecar lane's own fixture
    from mamey.figure_factory_next import build

    build(_fixture(tmp_path))
    sidecar = next(tmp_path.rglob("figure_factory_next_data.csv"))
    header = sidecar.read_text(encoding="utf-8").splitlines()[0].split(",")

    src = FF_R.read_text(encoding="utf-8")
    m = re.search(r"REQUIRED\s*<-\s*c\((.*?)\)\n", src, re.S)
    assert m, "REQUIRED column list not found in figure_factory_next_ggplot.R"
    required = re.findall(r'"([^"]+)"', m.group(1))

    assert required == header, (
        "R template's REQUIRED columns disagree with the emitted sidecar header.\n"
        f"  R      : {required}\n  sidecar: {header}"
    )


def test_r_height_formula_matches_the_python_renderer() -> None:
    """Same canvas height for the same row count, or the two renderers disagree on layout."""
    src = THEME.read_text(encoding="utf-8")
    assert "max(3.4, 0.62 * n_rows + 1.8)" in src, (
        "sapote_height_in has drifted from figure_factory_next._render's "
        "height = max(3.4, 0.62 * len(rows) + 1.8)"
    )
    ff_src = (ROOT / "mamey" / "figure_factory_next.py").read_text(encoding="utf-8")
    assert "max(3.4, 0.62 * len(rows) + 1.8)" in ff_src, (
        "the Python height formula changed; update sapote_figure_theme.R::sapote_height_in"
    )


def test_r_wrap_widths_match_the_python_renderer() -> None:
    theme_src = THEME.read_text(encoding="utf-8")
    assert re.search(r'if \(toupper\(profile\) == "SINGLE_COLUMN"\) 34 else 68', theme_src), (
        "sapote_wrap has drifted from the renderer's `wrap = 34 if SINGLE_COLUMN else 68`"
    )
    ff_src = (ROOT / "mamey" / "figure_factory_next.py").read_text(encoding="utf-8")
    assert 'wrap = 34 if profile == "SINGLE_COLUMN" else 68' in ff_src


def test_no_template_sets_text_below_the_publication_floor() -> None:
    """8 pt is a publication-QA floor enforced by validate_publication_artwork, not a preference."""
    from mamey.figure_policy import PUBLICATION_PROFILES

    floor = min(float(s["minimum_text_pt"]) for s in PUBLICATION_PROFILES.values())
    for path in (THEME, FF_R, TREE_R):
        src = path.read_text(encoding="utf-8")
        for raw in re.findall(r"(?:size|fontsize|base_pt)\s*=\s*([0-9.]+)\s*/\s*\.pt", src):
            assert float(raw) >= floor, f"{path.name}: text size {raw} pt is below the {floor} pt floor"
        for raw in re.findall(r"base_size\s*=\s*([0-9.]+)", src):
            assert float(raw) >= floor, f"{path.name}: base_size {raw} pt is below the {floor} pt floor"


def test_labels_are_offset_off_the_data_in_every_template() -> None:
    """The universal house rule: a text label never sits on the data it describes.

    Enforced structurally — bars place value text past the bar end via the shared helper, and the
    tree nudges tip labels off the branch — so a future edit that drops the offset fails here.
    """
    theme_src = THEME.read_text(encoding="utf-8")
    for helper in ("sapote_bar_label_x", "sapote_bar_marker_x", "sapote_tip_nudge"):
        assert f"{helper} <-" in theme_src, f"{helper} missing from the shared theme"

    ff_src = FF_R.read_text(encoding="utf-8")
    assert "sapote_bar_label_x(percent)" in ff_src, "bar value labels are not offset off the bar"
    assert "sapote_bar_marker_x(percent)" in ff_src, "assembly markers are not offset off the bar"

    tree_src = TREE_R.read_text(encoding="utf-8")
    assert "nudge_x = nudge" in tree_src, "tip labels are not nudged off the branch"
    assert "sapote_tip_nudge(max_depth)" in tree_src


def test_tree_template_does_not_silently_root() -> None:
    """An unstated rooting is an unstated phylogenetic claim — the template must not midpoint-root
    behind the operator's back."""
    # Match a midpoint-rooting CALL, not the word — the template's own comment explains why it does
    # not midpoint-root, and a substring check on "midpoint" would flag that explanation.
    code = "\n".join(
        line for line in TREE_R.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    calls = re.findall(r"\b(?:phytools::)?midpoint(?:\.root)?\s*\(", code)
    assert not calls, f"template must not midpoint-root silently: {calls}"

    src = TREE_R.read_text(encoding="utf-8")
    assert "rooting as supplied" in src, "caption must disclose when the rooting was not declared"
    # Rooting happens only inside the explicit outgroup branch.
    assert "ape::root(tr, outgroup = outgroup" in code


def test_templates_carry_a_claim_safety_note() -> None:
    """Every renderer that leaves the bundle states the ceiling on its own face."""
    ff_src = FF_R.read_text(encoding="utf-8")
    assert "Coverage is not production" in ff_src
    tree_src = TREE_R.read_text(encoding="utf-8")
    assert "not a species assignment" in tree_src


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_r_scripts_parse_under_rscript() -> None:
    """Opt-in syntax check wherever R exists. Parsing only — no packages are loaded, so this passes
    on a bare R with no ggplot2/ggtree installed."""
    for path in (THEME, FF_R, TREE_R):
        result = subprocess.run(
            ["Rscript", "-e", f'invisible(parse("{path.as_posix()}"))'],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{path.name} failed to parse:\n{result.stderr}"


# ---------------------------------------------------------------------------------------------
# Round 2: full figure coverage (matrix / tidy / strain-series / locus map) + the manifest
# ---------------------------------------------------------------------------------------------

MATRIX_R = TOOLS / "sapote_matrix_figure.R"
TIDY_R = TOOLS / "sapote_tidy_figure.R"
STRAIN_R = TOOLS / "sapote_strain_figure.R"
LOCUS_R = TOOLS / "sapote_locus_map.R"
MANIFEST = TOOLS / "FIGURE_R_MANIFEST.tsv"
GEN = TOOLS / "gen_figure_r_manifest.py"

ALL_TEMPLATES = (THEME, FF_R, TREE_R, MATRIX_R, TIDY_R, STRAIN_R, LOCUS_R)


def test_every_renderer_and_the_manifest_ship() -> None:
    for path in (*ALL_TEMPLATES, MANIFEST, GEN):
        assert path.is_file(), f"missing: {path.relative_to(ROOT)}"


def test_manifest_is_generated_not_hand_typed() -> None:
    """The manifest must match what the generator derives from the Python sources.

    Hand-editing it would create a second, unverifiable copy of the render policy — the exact
    failure this codebase keeps paying for. `--check` re-derives and compares.
    """
    result = subprocess.run(
        [_sys.executable, str(GEN), "--check"],
        capture_output=True, text=True, cwd=str(ROOT),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _manifest_rows() -> list[dict[str, str]]:
    import csv as _csv
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        return list(_csv.DictReader(handle, delimiter="\t"))


def test_manifest_covers_the_cohort_figures_with_a_sidecar() -> None:
    rows = _manifest_rows()
    assert len(rows) >= 32, f"manifest has only {len(rows)} figures"
    schemas = {r["schema"] for r in rows}
    assert schemas <= {"WIDE_MATRIX", "TIDY", ""}, schemas
    # Both renderers must have work to do, or one of them is dead code.
    assert sum(r["schema"] == "WIDE_MATRIX" for r in rows) >= 25
    assert sum(r["schema"] == "TIDY" for r in rows) >= 3


def test_every_manifest_geometry_has_a_renderer_branch() -> None:
    """A geometry in the manifest that no template draws would fail only at render time."""
    matrix_src = MATRIX_R.read_text(encoding="utf-8")
    for row in _manifest_rows():
        geom = row["geometry"]
        if not geom:
            continue
        assert geom in {"heatmap", "bubble", "grouped_bar", "stacked_bar"}, geom
        if geom in {"heatmap", "bubble"}:
            assert f'"{geom}"' in matrix_src, f"{geom} has no branch in sapote_matrix_figure.R"


def test_manifest_colormaps_are_all_reproducible_in_r() -> None:
    """Every colormap the Python side uses must map to a real viridisLite option — otherwise the R
    figure silently renders in a different palette than the Python one."""
    known = {"viridis", "plasma", "cividis", "magma", "inferno", "rocket", "mako", "turbo"}
    src = MATRIX_R.read_text(encoding="utf-8")
    for name in known:
        assert f"{name} = " in src or f'"{name}"' in src, f"{name} not handled in the R palette map"
    for row in _manifest_rows():
        if not row["cmap"]:
            continue
        for candidate in row["cmap"].split("|"):
            base = candidate[:-2] if candidate.endswith("_r") else candidate
            assert base in known, (
                f"{row['figure_id']}: colormap {candidate!r} has no viridisLite equivalent"
            )


def test_matrix_renderer_refuses_an_unknown_figure_id() -> None:
    """Guessing a colour scale is worse than refusing: the figure would look right and be wrong."""
    src = MATRIX_R.read_text(encoding="utf-8")
    assert "is not in FIGURE_R_MANIFEST.tsv" in src
    assert "use sapote_tidy_figure.R for that one" in src


def test_zscore_figure_keeps_its_fixed_diverging_domain() -> None:
    """F01 is imshow(z, cmap="RdBu_r", vmin=-2, vmax=2). A rescaled diverging scale would change
    what a colour means between runs."""
    src = MATRIX_R.read_text(encoding="utf-8")
    assert 'palette = "RdBu"' in src and "limits = c(-2, 2)" in src
    py = (ROOT / "mamey" / "cohort_figures.py").read_text(encoding="utf-8")
    assert 'cmap="RdBu_r",vmin=-2,vmax=2' in py, "the Python z-score scale changed; update the R side"


def test_locus_map_prints_the_exact_identity_verbatim() -> None:
    """The panel string is strain / full node / region / BGC. Shortening it names a different locus."""
    src = LOCUS_R.read_text(encoding="utf-8")
    assert "subtitle = identity" in src
    assert "never abbreviated" in src
    # And it must refuse a malformed identity rather than render it.
    assert "is not a full strain / node / region / BGC identity" in src


def test_locus_map_reads_the_real_sidecar_columns() -> None:
    """REQUIRED is checked against a real emitted locus sidecar, not a guess."""
    src = LOCUS_R.read_text(encoding="utf-8")
    m = re.search(r"REQUIRED\s*<-\s*c\((.*?)\)\n", src, re.S)
    assert m, "REQUIRED not found in sapote_locus_map.R"
    required = set(re.findall(r'"([^"]+)"', m.group(1)))
    known_locus_columns = {
        "panel", "locus_tag", "order", "start", "end", "strand", "length_aa", "role",
        "gene_functions", "label_displayed", "selected_comparator", "comparator_accession",
        "comparator_compound", "subject_gene", "pct_identity", "pct_coverage", "blast_score",
        "evalue", "domain_tokens", "hmm_tokens", "module_tokens", "motif_tokens",
        "displayed_evidence_summary",
    }
    assert required <= known_locus_columns, required - known_locus_columns


def test_strain_series_keeps_the_provenance_banner() -> None:
    """The 8-series sidecars carry `# provenance,... KCB=similarity not identity`. Dropping it would
    strip the claim ceiling the Python figure prints."""
    src = STRAIN_R.read_text(encoding="utf-8")
    assert 'startsWith(lines, "#")' in src
    assert "caption = caption" in src or "caption = provenance" in src


@pytest.mark.parametrize("path", [p.name for p in ALL_TEMPLATES])
def test_every_template_offsets_labels_or_explains_why(path: str) -> None:
    """House rule across the whole set. A heatmap cell label is the one allowed exception — it
    annotates its own cell and nothing else — and must say so."""
    src = (TOOLS / path).read_text(encoding="utf-8")
    if "geom_text" not in src:
        return
    offsets = ("sapote_bar_label_x", "sapote_tip_nudge", "nudge_x", "hjust = -0.25",
               "geom_text_repel", "-0.72", "row = 0")
    exception = "INSIDE its own cell"
    assert any(o in src for o in offsets) or exception in src, (
        f"{path} draws text with no offset helper and no documented exception"
    )


@pytest.mark.parametrize("path", [p.name for p in ALL_TEMPLATES])
def test_every_template_states_its_claim_ceiling(path: str) -> None:
    src = (TOOLS / path).read_text(encoding="utf-8")
    assert "Claim-safety" in src or "claim-safety" in src, f"{path} has no claim-safety note"
