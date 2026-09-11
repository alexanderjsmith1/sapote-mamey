#!/usr/bin/env python3
"""Sapote-Mamey gold gene/domain figure generator v3 (data-only PNG + sidecar CSV).
Adds: figure numbering (F01..) + croppable corner stamp, soft PUBLIC|PRIVATE divider,
genus-from-manifest labels, and chemistry-class heatmaps (product class, tailoring
enzymes, transporters, regulators/TFs).
Usage: python3 make_figures2.py --runs-dir runs_gold --out out/figuresN [--strains ...] [--public-only]
"""
try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json, glob, os, csv, ast, collections, re, argparse, hashlib, warnings
import json as _j
import contextlib
import math
from pathlib import Path
PUBLICATION_RASTER_DPI = 300
from .manifest_schema import read_manifest_field
from .cross_strain_figures import build_cross_strain_figures
from . import figure_policy as _figure_policy
from .figure_save import save_figure
import numpy as np
try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mp
    from matplotlib.colors import LogNorm
    _HAVE_MPL = True
except ImportError as _e:  # figure deps are optional; fail with a clear message, not a traceback
    _HAVE_MPL = False
    _MPL_ERR = str(_e)

    def _require_mpl():
        raise RuntimeError(
            "Figure generation needs matplotlib. Install the figures extra: "
            "`pip install -e '.[figures]'` (or `.[all]`). "
            f"(import error: {_MPL_ERR})")
try:
    from scipy.cluster.hierarchy import linkage, leaves_list
    _HAS_SCIPY = True
except Exception:                       # scipy is optional; clustermap falls back to count-ordering
    _HAS_SCIPY = False

def _loadj(p):   # B1: context-managed json load — no leaked handle (was _loadj(p) in a per-strain loop)
    with open(p, encoding="utf-8") as _f:
        return json.load(_f)

if _HAVE_MPL:   # B4: this ran unconditionally at import -> NameError('plt') when matplotlib absent,
    # making the whole 1580-line module unimportable and defeating the _HAVE_MPL guard above.
    plt.rcParams.update({"font.size":9,"axes.titlesize":12,"axes.titleweight":"bold",
                         "figure.dpi":PUBLICATION_RASTER_DPI,"savefig.dpi":PUBLICATION_RASTER_DPI,"axes.edgecolor":"#444",
                         "savefig.bbox":"tight","savefig.pad_inches":0.35,"font.family":"DejaVu Sans"})
TCOLOR={"GOOD":"#1b7837","MODERATE":"#7b3294","POOR":"#e08214","VERY_POOR":"#b2182b"}
GENUS={}; FIGNUM=[0]


def _save_pair(fig, path, *, renderer="cohort_figures", provenance="normalized_cohort_tables"):
    # BC2-408: 15 of this file's figures use `constrained_layout=True`, whose own layout engine
    # actively repositions the axes/tick-labels on every draw -- including the draw triggered by
    # `save_figure()`'s later `savefig(..., bbox_inches="tight")` call, which happens AFTER
    # `add_claim_safety_footer()` has already placed the mandatory footer text at a FIXED
    # figure-fraction position. Since the footer text is added via plain `fig.text()` calls (not
    # tracked by the constrained-layout engine), the engine has no way to know it must leave room
    # for it -- `fig.subplots_adjust()` is also silently a no-op once constrained_layout is active
    # (matplotlib's own UserWarning: "not calling subplots_adjust"), so the domain_strip fix's
    # one-line pattern (fix earlier this cycle, mamey/domain_figures.py) does not apply here.
    # Verified live against a real 2-strain cohort-figures run (AS-XXX + AS-XXX): F03's x-axis
    # tick labels ("Streptomyces sp. / strain AS-XXX", "strain AS-XXX") rendered directly through
    # the claim-safety sentence. Reserve the bottom margin through the layout engine's own `rect`
    # API instead -- confirmed via a standalone check this correctly keeps the axes/tick-labels
    # clear of the reserved band even under `bbox_inches="tight"`. A figure NOT using
    # constrained_layout (10 of this file's other figures) has no layout engine to reserve space
    # on, so this is a no-op there -- unaffected, matching what was actually verified broken.
    _engine = fig.get_layout_engine()
    if _engine is not None:
        try:
            _engine.set(rect=(0, 0.13, 1, 1))
        except Exception as exc:
            # The margin reservation is compatibility-best-effort, but failure must remain
            # observable because it can reintroduce a label/footer collision. Continue to save
            # so one Matplotlib API change does not suppress the entire figure suite.
            warnings.warn(
                "LAYOUT_ENGINE_RECT_UNAVAILABLE: constrained-layout margin reservation "
                f"failed ({type(exc).__name__}); figure save will continue",
                RuntimeWarning,
                stacklevel=2,
            )
    target = Path(path)
    save_figure(
        fig, figure_id=target.stem, out_stem=target.with_suffix(""),
        renderer=renderer, package_dir=target.parent, provenance=provenance,
    )

# v9.7.229: AS- is PUBLIC as of the 2026 Hymenoptera paper (PI decision 2026-07-06, same basis as the
# .219 AS_SCRUB retirement + .222 divider removal). So AS- no longer draws (PRIV)/diamond markers on the
# PCA/tier scatters. Machinery retained for genuinely-unpublished series (AJS-/PENDING-).
def is_private(sid): return sid.startswith(("AJS-","PENDING-"))
def genus(sid):
    g=(GENUS.get(sid) or "Unknown genus").split()
    return " ".join(g[:2]) if len(g)>=2 else GENUS.get(sid,"Unknown genus")
def lab(sid): return f"{genus(sid)}\nstrain {sid}"

def _load_manifest_short(pkg, sid):
    """Load manifest_short.json, or reconstruct the fields the figure suite needs
    (raw_bgcs, assembly_tier, taxonomy) from the full manifest.json / intake when
    it's absent.

    manifest_short.json is written late in the run (after the auto-emit gold-figure
    call in cli.py), so a single-strain gold run reaches this loader before the file
    exists. An unguarded open() here raised FileNotFoundError, which the caller
    swallowed into a blanket "Gold figures: SKIPPED" — silently killing the entire
    suite over one missing compact-summary file whose data lives in manifest.json
    anyway. Fall back rather than fail. (v9.7.155 pipeline fix.)
    """
    ms_path = f"{pkg}/manifest_short.json"
    if os.path.exists(ms_path):
        try:
            ms = _loadj(ms_path)
        except (json.JSONDecodeError, OSError) as exc:
            warnings.warn(
                "MANIFEST_SHORT_UNREADABLE_FALLBACK: compact manifest could not be read "
                f"({type(exc).__name__}); reconstructing from manifest.json",
                RuntimeWarning,
                stacklevel=2,
            )
        else:
            return _require_manifest_figure_fields(ms)
    # Reconstruct the needed fields from the full manifest (written earlier).
    ms = {}
    man_path = f"{pkg}/manifest.json"
    if os.path.exists(man_path):
        # The full manifest is the final reconstruction authority. Corrupt or unreadable
        # content must surface; it cannot become a scientifically meaningful zero/UNKNOWN row.
        man = _loadj(man_path)
        ms["taxonomy"] = man.get("taxonomy")
        # v9.7.160 claimed assembly_tier lives in man["assembly"]["tier"], but the real
        # writer puts it under bgc_counts. The schema accessor owns that mapping.
        ms["assembly_tier"] = read_manifest_field("assembly_tier", manifest=man)
        # raw_bgcs: accessor checks bgc_counts["raw"]; keep the len(bgcs) fallback.
        ms["raw_bgcs"] = read_manifest_field("raw_bgcs", manifest=man)
        if ms["raw_bgcs"] is None and isinstance(man.get("bgcs"), list):
            ms["raw_bgcs"] = len(man["bgcs"])
        # corrected_bgcs is required because a zero fallback changes figure content.
        ms["corrected_bgcs"] = read_manifest_field("corrected_bgcs", manifest=man)
        return _require_manifest_figure_fields(ms)
    raise FileNotFoundError(
        "MANIFEST_METADATA_UNAVAILABLE: neither a readable manifest_short.json nor "
        "manifest.json is available for figure metadata"
    )


def _require_manifest_figure_fields(ms):
    """Refuse absent required figure metadata instead of inventing numeric zero."""
    if not isinstance(ms, dict):
        raise ValueError("MANIFEST_FIGURE_METADATA_NOT_OBJECT")
    required = ("raw_bgcs", "corrected_bgcs", "assembly_tier")
    missing = [field for field in required if ms.get(field) in (None, "")]
    if missing:
        raise ValueError("MANIFEST_FIGURE_FIELDS_MISSING: " + ",".join(missing))
    return ms


def load(runs_dir, only=None, public_only=False):
    S={}
    for dd in sorted(glob.glob(f"{runs_dir}/*/package/deep_data.json")):
        pkg=os.path.dirname(dd); sid=os.path.basename(os.path.dirname(pkg))
        if only and sid not in only: continue
        if public_only and is_private(sid): continue
        ms=_load_manifest_short(pkg, sid)
        # COHORT-FIG-P01: strain-prefixed package files use the --strain id, which is NOT always
        # the deliverable folder name (sid) — e.g. Type-strain folders are display names with
        # spaces. Glob for the actual intake file instead of building the path from sid.
        _intake = next(iter(sorted(glob.glob(f"{pkg}/*_1_intake.json"))), f"{pkg}/{sid}_1_intake.json")
        GENUS[sid]=ms.get("taxonomy") or _loadj(_intake).get("taxonomy","Unknown genus")
        S[sid]={"deep":_loadj(dd),"gene":_loadj(f"{pkg}/gene_data.json"),"ms":ms,"pkg":pkg}
    return S


# F13 publication-source artwork contract.  This renderer does not make a
# biological call: it binds the existing antiSMASH-derived per-BGC counts to a
# declared cohort before it writes a vector source-artwork candidate.
F13_SCHEMA_VERSION = "sapote-mamey.f13-domain-pca.v1"
F13_DENOMINATOR_REGISTRY_SCHEMA = "sapote-mamey.cohort-denominator-registry.v1"
F13_VOCAB = (
    "PKS_KS", "PKS_AT", "PKS_KR", "PKS_DH", "PKS_ER", "PKS_ACP", "NRPS_C",
    "NRPS_A", "NRPS_T_PCP", "TE_release",
)
F13_CLAIM_CEILING = (
    "Descriptive source-derived domain-count ordination only; it does not establish "
    "product, sequence, activity, evolutionary, or phylogenetic claims."
)


def _f13_digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _f13_write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _f13_hold(out, code, detail, *, cohort_manifest=None, denominator_registry=None):
    """Write a machine-readable refusal without creating new F13 artwork."""
    target = Path(out)
    target.mkdir(parents=True, exist_ok=True)
    existing_artwork = sorted(
        candidate.name for candidate in target.glob("F13_bgc_domain_pca_2d.*")
        if candidate.suffix.lower() in {".svg", ".png", ".pdf"}
    )
    receipt = {
        "schema_version": F13_SCHEMA_VERSION,
        "status": "HOLD",
        "code": str(code),
        "detail": str(detail),
        "cohort_manifest_filename": Path(cohort_manifest).name if cohort_manifest else None,
        "denominator_registry_filename": (
            Path(denominator_registry).name if denominator_registry else None
        ),
        "new_source_artwork_created": False,
        "preexisting_f13_artwork_detected": existing_artwork,
        "claim_ceiling": F13_CLAIM_CEILING,
    }
    _f13_write_json(target / "F13_bgc_domain_pca_2d_HOLD.json", receipt)
    return {"status": "HOLD", "hold_path": str(target / "F13_bgc_domain_pca_2d_HOLD.json"),
            "code": str(code)}


def _f13_load_cohort(cohort_manifest, expected_digest, order):
    if not cohort_manifest or not expected_digest:
        raise _figure_policy.FigurePolicyError(
            "F13_COHORT_BINDING_REQUIRED",
            "a cohort manifest path and its exact SHA-256 digest are required",
        )
    path = Path(cohort_manifest)
    if not path.is_file():
        raise _figure_policy.FigurePolicyError("F13_COHORT_MANIFEST_MISSING", path.name)
    expected = str(expected_digest).strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise _figure_policy.FigurePolicyError("F13_COHORT_DIGEST_INVALID", "expected a SHA-256 hex digest")
    observed = _f13_digest(path)
    if observed != expected:
        raise _figure_policy.FigurePolicyError(
            "F13_COHORT_DIGEST_MISMATCH", f"expected {expected}; observed {observed}"
        )
    payload = _loadj(path)
    if payload.get("schema_version") != _figure_policy.COHORT_MANIFEST_SCHEMA:
        raise _figure_policy.FigurePolicyError(
            "F13_COHORT_SCHEMA_INVALID", _figure_policy.COHORT_MANIFEST_SCHEMA
        )
    rows, policy_receipt = _figure_policy.validate_cohort_manifest(payload.get("rows") or [])
    by_identity = {row["identity"]: row for row in rows}
    missing = sorted(set(order) - set(by_identity))
    if missing:
        raise _figure_policy.FigurePolicyError(
            "F13_COHORT_ROSTER_INCOMPLETE", ", ".join(missing)
        )
    eligible = {
        row["identity"]: row for row in rows
        if row["identity"] in order and row["study_denominator_member"]
    }
    if not eligible:
        raise _figure_policy.FigurePolicyError("F13_COHORT_NO_DEFAULT_STUDY", "no default-on STUDY rows")
    excluded = [
        {
            "identity": row["identity"],
            "role": row["role"],
            "include_by_default": row["include_by_default"],
            "assembly_state": row["assembly_state"],
            "reason": row["assembly_reason"],
        }
        for row in rows if row["identity"] in order and row["identity"] not in eligible
    ]
    return {
        "path": path,
        "digest": observed,
        "policy_rows": rows,
        "policy_receipt": policy_receipt,
        "eligible": eligible,
        "excluded": excluded,
        "denominator_scope": str(payload.get("denominator_scope") or "").strip().upper(),
    }


def _f13_load_denominator_registry(path, expected_digest):
    """Load an independently hash-bound registry of permitted cohort denominators."""
    if not path or not expected_digest:
        raise _figure_policy.FigurePolicyError(
            "DENOMINATOR_UNGOVERNED",
            "an independent denominator-registry path and exact SHA-256 digest are required",
        )
    registry_path = Path(path)
    if not registry_path.is_file():
        raise _figure_policy.FigurePolicyError(
            "DENOMINATOR_UNGOVERNED", f"denominator registry missing: {registry_path.name}"
        )
    expected = str(expected_digest).strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise _figure_policy.FigurePolicyError(
            "DENOMINATOR_UNGOVERNED", "denominator registry digest must be SHA-256 hex"
        )
    observed = _f13_digest(registry_path)
    if observed != expected:
        raise _figure_policy.FigurePolicyError(
            "DENOMINATOR_UNGOVERNED",
            f"denominator registry digest mismatch: expected {expected}; observed {observed}",
        )
    payload = _loadj(registry_path)
    if payload.get("schema_version") != F13_DENOMINATOR_REGISTRY_SCHEMA:
        raise _figure_policy.FigurePolicyError(
            "DENOMINATOR_UNGOVERNED",
            f"denominator registry schema must be {F13_DENOMINATOR_REGISTRY_SCHEMA}",
        )
    scopes = {}
    for position, row in enumerate(payload.get("scopes") or [], 1):
        if not isinstance(row, dict):
            raise _figure_policy.FigurePolicyError(
                "DENOMINATOR_UNGOVERNED", f"denominator registry row {position} is not an object"
            )
        scope = str(row.get("scope") or "").strip().upper()
        strains = row.get("strains")
        regions = row.get("regions")
        if (
            not scope
            or isinstance(strains, bool) or not isinstance(strains, int) or strains < 1
            or isinstance(regions, bool) or not isinstance(regions, int) or regions < 1
        ):
            raise _figure_policy.FigurePolicyError(
                "DENOMINATOR_UNGOVERNED",
                f"denominator registry row {position} needs scope and positive integer strains/regions",
            )
        if scope in scopes:
            raise _figure_policy.FigurePolicyError(
                "DENOMINATOR_UNGOVERNED", f"duplicate denominator scope: {scope}"
            )
        scopes[scope] = {"scope": scope, "strains": strains, "regions": regions}
    if not scopes:
        raise _figure_policy.FigurePolicyError(
            "DENOMINATOR_UNGOVERNED", "denominator registry contains no governed scopes"
        )
    return {
        "path": registry_path,
        "digest": observed,
        "scopes": scopes,
    }


def _f13_validate_denominator(cohort, source_region_count, registry):
    scope = cohort["denominator_scope"]
    allowed = registry["scopes"].get(scope)
    observed = {
        "scope": scope,
        "strains": len(cohort["eligible"]),
        "regions": source_region_count,
    }
    if allowed is None or observed != allowed:
        raise _figure_policy.FigurePolicyError(
            "DENOMINATOR_UNGOVERNED",
            f"observed {observed}; permitted entry for scope is {allowed}",
        )
    return {
        "status": "PASS",
        "scope": scope,
        "strains": observed["strains"],
        "regions": observed["regions"],
        "registry_filename": registry["path"].name,
        "registry_sha256": registry["digest"],
    }


def _f13_package_context(sid, source):
    """Load only a package's bound F13 inputs and refuse incomplete locus rows."""
    package = Path(source["pkg"])
    manifest_path = package / "manifest.json"
    gene_path = package / "gene_data.json"
    intakes = sorted(package.glob("*_1_intake.json"))
    if not manifest_path.is_file() or not gene_path.is_file() or len(intakes) != 1:
        raise _figure_policy.FigurePolicyError(
            "F13_PACKAGE_BINDING_INCOMPLETE",
            f"{sid} requires manifest.json, gene_data.json, and exactly one *_1_intake.json",
        )
    manifest = _loadj(manifest_path)
    gene = _loadj(gene_path)
    intake = _loadj(intakes[0])
    if str(manifest.get("strain_id") or "").strip() != sid:
        raise _figure_policy.FigurePolicyError("F13_PACKAGE_STRAIN_MISMATCH", sid)
    mamey_version = str(manifest.get("workflow_version") or manifest.get("mamey_version") or "").strip()
    antismash_version = str(intake.get("antismash_version") or "").strip()
    if not mamey_version or not antismash_version:
        raise _figure_policy.FigurePolicyError(
            "F13_SOURCE_VERSION_UNBOUND", f"{sid} lacks workflow_version or antismash_version"
        )
    bgcs = {}
    for position, row in enumerate(manifest.get("bgcs") or [], 1):
        alias = str(row.get("bgc_id") or "").strip()
        node = str(row.get("node_id") or row.get("contig") or "").strip()
        region = str(row.get("antismash_region") or row.get("region_number") or "").strip()
        if not alias or not node or not region:
            raise _figure_policy.FigurePolicyError(
                "F13_EXACT_LOCUS_IDENTITY_INCOMPLETE", f"{sid} manifest BGC row {position}"
            )
        if alias in bgcs:
            raise _figure_policy.FigurePolicyError("F13_BGC_ALIAS_DUPLICATE", f"{sid}: {alias}")
        bgcs[alias] = {
            "strain": sid,
            "node_or_contig": node,
            "region": region,
            "bgc_alias": alias,
            "complete_identity": f"{sid} / {node} / {region} / {alias}",
        }
    if not bgcs:
        raise _figure_policy.FigurePolicyError("F13_PACKAGE_BGC_MANIFEST_EMPTY", sid)
    return {
        "gene": gene,
        "bgcs": bgcs,
        "mamey_version": mamey_version,
        "antismash_version": antismash_version,
        "source_bindings": [
            {"filename": "manifest.json", "sha256": _f13_digest(manifest_path)},
            {"filename": "gene_data.json", "sha256": _f13_digest(gene_path)},
            {"filename": intakes[0].name, "sha256": _f13_digest(intakes[0])},
        ],
    }


def _f13_count(value, *, field, identity):
    try:
        number = float(value or 0)
    except (TypeError, ValueError) as exc:
        raise _figure_policy.FigurePolicyError(
            "F13_DOMAIN_COUNT_NON_NUMERIC", f"{identity}: {field}"
        ) from exc
    if not math.isfinite(number) or number < 0:
        raise _figure_policy.FigurePolicyError(
            "F13_DOMAIN_COUNT_INVALID", f"{identity}: {field}"
        )
    return number


def _f13_rows(S, eligible):
    rows = []
    source_bindings = []
    versions = {"mamey": set(), "antismash": set()}
    source_region_count = 0
    for sid in sorted(eligible):
        if sid not in S or not S[sid].get("pkg"):
            raise _figure_policy.FigurePolicyError("F13_PACKAGE_NOT_LOADED", sid)
        policy = eligible[sid]
        context = _f13_package_context(sid, S[sid])
        source_region_count += len(context["bgcs"])
        source_bindings.extend(
            {"strain": sid, **binding} for binding in context["source_bindings"]
        )
        versions["mamey"].add(context["mamey_version"])
        versions["antismash"].add(context["antismash_version"])
        seen = set()
        for record in context["gene"].get("domain_arch") or []:
            alias = str(record.get("bgc_id") or "").strip()
            if alias not in context["bgcs"]:
                raise _figure_policy.FigurePolicyError(
                    "F13_DOMAIN_ARCH_BGC_UNBOUND", f"{sid}: {alias or 'missing alias'}"
                )
            if alias in seen:
                raise _figure_policy.FigurePolicyError("F13_DOMAIN_ARCH_BGC_DUPLICATE", f"{sid}: {alias}")
            seen.add(alias)
            architecture = record.get("architecture")
            try:
                parsed = architecture if isinstance(architecture, dict) else ast.literal_eval(str(architecture))
            except (ValueError, SyntaxError) as exc:
                raise _figure_policy.FigurePolicyError(
                    "F13_DOMAIN_ARCH_INVALID", f"{context['bgcs'][alias]['complete_identity']}"
                ) from exc
            counts = parsed.get("domain_counts") if isinstance(parsed, dict) else None
            if not isinstance(counts, dict):
                raise _figure_policy.FigurePolicyError(
                    "F13_DOMAIN_COUNTS_MISSING", f"{context['bgcs'][alias]['complete_identity']}"
                )
            identity = context["bgcs"][alias]
            raw = [_f13_count(counts.get(feature, 0), field=feature,
                              identity=identity["complete_identity"]) for feature in F13_VOCAB]
            rows.append({
                **identity,
                "genus": policy["genus"],
                "cohort": policy["cohort"],
                "assembly_state": policy["assembly_state"],
                "raw_counts": raw,
            })
    if len(rows) < 2:
        raise _figure_policy.FigurePolicyError(
            "F13_PCA_ROWS_INSUFFICIENT", f"requires at least 2 eligible BGC rows; observed {len(rows)}"
        )
    return rows, source_bindings, versions, source_region_count


def _f13_file_receipt(path):
    target = Path(path)
    return {"filename": target.name, "sha256": _f13_digest(target), "bytes": target.stat().st_size}


def _render_f13_domain_pca(S, order, out, *, cohort_manifest=None,
                           cohort_manifest_sha256=None, denominator_registry=None,
                           denominator_registry_sha256=None, profile="SINGLE_COLUMN"):
    """Render F13 only after binding cohort, package, version, and full-locus provenance."""
    try:
        cohort = _f13_load_cohort(cohort_manifest, cohort_manifest_sha256, order)
        rows, source_bindings, versions, source_region_count = _f13_rows(S, cohort["eligible"])
        registry = _f13_load_denominator_registry(
            denominator_registry, denominator_registry_sha256
        )
        denominator_receipt = _f13_validate_denominator(cohort, source_region_count, registry)
        matrix = np.array([row["raw_counts"] for row in rows], dtype=float)
        transformed = np.log1p(matrix)
        centered = transformed - transformed.mean(axis=0)
        if np.allclose(centered, 0.0):
            raise _figure_policy.FigurePolicyError(
                "F13_PCA_DEGENERATE", "all eligible rows are identical after log1p and mean-centering"
            )
        _u, singular_values, vt = np.linalg.svd(centered, full_matrices=False)
        pcs = centered @ vt[:2].T
        variance_total = float(np.sum(singular_values ** 2))
        explained = ((singular_values[:2] ** 2) / variance_total).tolist()
        profile_receipt = _figure_policy.validate_publication_profile(
            profile, plot_minimum_text_pt=8.2, caption_text_pt=9.0
        )
        palette_receipt = _figure_policy.validate_cohort_palette()
        genera = sorted({row["genus"] for row in rows})
        if profile_receipt["profile"] == "SINGLE_COLUMN" and len(genera) > 1:
            raise _figure_policy.FigurePolicyError(
                "F13_PROFILE_TOO_NARROW_FOR_GENUS_FACETS",
                "SINGLE_COLUMN permits one genus facet; use DOUBLE_COLUMN for multiple genera",
            )
        genus_receipt = _figure_policy.validate_genus_comparison(
            "WITHIN_GENUS" if len(genera) == 1 else "CROSS_GENUS",
            None if len(genera) == 1 else "COMPOSITION_SHOWN",
        )
    except _figure_policy.FigurePolicyError as exc:
        return _f13_hold(
            out, exc.code, exc.detail, cohort_manifest=cohort_manifest,
            denominator_registry=denominator_registry,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return _f13_hold(out, "F13_SOURCE_INPUT_INVALID", f"{type(exc).__name__}: {exc}",
                         cohort_manifest=cohort_manifest,
                         denominator_registry=denominator_registry)

    target = Path(out)
    target.mkdir(parents=True, exist_ok=True)
    svg_path = target / "F13_bgc_domain_pca_2d.svg"
    ncols = 1 if len(genera) == 1 else 2
    nrows = int(math.ceil(len(genera) / ncols))
    width = profile_receipt["width_in"]
    fig, axes = plt.subplots(nrows, ncols, figsize=(width, max(3.5, 3.05 * nrows)), squeeze=False)
    legend_handles = {}
    for axis, genus_name in zip(axes.ravel(), genera):
        indices = [index for index, row in enumerate(rows) if row["genus"] == genus_name]
        for cohort_name in sorted({rows[index]["cohort"] for index in indices}):
            selected = [index for index in indices if rows[index]["cohort"] == cohort_name]
            flags = [index for index in selected if rows[index]["assembly_state"] == "FLAG"]
            passes = [index for index in selected if rows[index]["assembly_state"] != "FLAG"]
            if passes:
                handle = axis.scatter(pcs[passes, 0], pcs[passes, 1], s=30,
                                      color=_figure_policy.COHORT_PALETTE[cohort_name], marker="o",
                                      edgecolor="#222222", linewidth=0.35, alpha=0.9, label=cohort_name)
                legend_handles.setdefault(cohort_name, handle)
            if flags:
                handle = axis.scatter(pcs[flags, 0], pcs[flags, 1], s=42,
                                      color=_figure_policy.COHORT_PALETTE[cohort_name], marker="^",
                                      edgecolor="#222222", linewidth=0.35, alpha=0.9,
                                      label=f"{cohort_name} assembly flag")
                legend_handles.setdefault(f"{cohort_name} assembly flag", handle)
        axis.axhline(0, color="#B8B8B8", lw=0.55, zorder=0)
        axis.axvline(0, color="#B8B8B8", lw=0.55, zorder=0)
        axis.set_title(genus_name, fontsize=8.5, fontweight="bold")
        axis.set_xlabel(f"PC1 ({explained[0] * 100:.1f}% variance)", fontsize=8.2)
        axis.set_ylabel(f"PC2 ({explained[1] * 100:.1f}% variance)", fontsize=8.2)
        axis.tick_params(labelsize=8.2)
    for axis in axes.ravel()[len(genera):]:
        axis.remove()
    fig.suptitle("F13. BGC domain-count PCA by declared genus cohort", fontsize=9.0, fontweight="bold")
    if legend_handles:
        fig.legend(list(legend_handles.values()), list(legend_handles), loc="lower center",
                   ncol=max(1, min(3, len(legend_handles))), fontsize=8.2, frameon=False)
    fig.tight_layout(rect=(0, 0.08 if legend_handles else 0, 1, 0.94))
    source_binding_text = "; ".join(
        [f"cohort_manifest sha256={cohort['digest']}"] +
        [f"{binding['strain']}:{binding['filename']} sha256={binding['sha256']}"
         for binding in source_bindings]
    )
    try:
        with matplotlib.rc_context({"svg.fonttype": "none"}):
            _save_pair(
                fig, svg_path,
                renderer="cohort_figures.f13_bgc_domain_pca_2d",
                provenance=source_binding_text,
            )
        artwork_receipt = _figure_policy.validate_publication_artwork(
            svg_path, profile=profile_receipt["profile"], plot_minimum_text_pt=8.2,
            caption_text_pt=9.0, source_kind="SOURCE_ARTWORK",
        )
    except Exception:
        if svg_path.exists():
            svg_path.unlink()
        raise
    finally:
        plt.close(fig)

    csv_path = target / "F13_bgc_domain_pca_2d_plotdata.csv"
    header = ["strain", "node_or_contig", "region", "bgc_alias", "complete_identity", "genus",
              "cohort", "assembly_state", "PC1", "PC2"]
    header += [f"raw_{feature}" for feature in F13_VOCAB]
    header += [f"log1p_{feature}" for feature in F13_VOCAB]
    csv_rows = []
    for index, row in enumerate(rows):
        csv_rows.append([
            row["strain"], row["node_or_contig"], row["region"], row["bgc_alias"],
            row["complete_identity"], row["genus"], row["cohort"], row["assembly_state"],
            f"{pcs[index, 0]:.8f}", f"{pcs[index, 1]:.8f}",
            *[f"{value:.8g}" for value in row["raw_counts"]],
            *[f"{value:.8g}" for value in transformed[index]],
        ])
    sidecar(csv_path, header, csv_rows)
    genus_counts = collections.Counter(row["genus"] for row in rows)
    cohort_counts = collections.Counter(row["cohort"] for row in rows)
    caption = {
        "caption_schema_version": _figure_policy.CAPTION_METHOD_SCHEMA,
        "figure_question": "How do declared-cohort BGCs distribute in a ten-feature source-derived domain-count PCA?",
        "source": "Hash-bound gene_data.json per-BGC antiSMASH-derived domain_arch domain_counts.",
        "source_bindings": source_binding_text,
        "source_release": "antiSMASH versions: " + ", ".join(sorted(versions["antismash"])),
        "software_versions": "Mamey workflow versions: " + ", ".join(sorted(versions["mamey"])) + "; NumPy SVD.",
        "unit_of_analysis": "One antiSMASH-defined BGC with a complete strain / node-or-contig / region / BGC alias identity.",
        "inclusion_exclusion_roles": "Included default-on STUDY rows only; default-off assembly holds and external benchmarks are not plotted.",
        "denominator": (
            f"{len(rows)} plotted BGC rows from governed scope {denominator_receipt['scope']}: "
            f"{denominator_receipt['strains']} strains / {denominator_receipt['regions']} regions."
        ),
        "group_denominators": "; ".join(f"{name}: rows={genus_counts[name]}" for name in sorted(genus_counts)),
        "typed_missingness": f"plotted_rows={len(rows)}; no_typed_state_column_in_plotted_rows; "
                             f"default_off_strains={len(cohort['excluded'])}",
        "benchmark_sensitivity": "External benchmark rows are default_off=true and excluded from study n and percentages; none are included in this default view.",
        "transformation": "Ten fixed raw domain counts were transformed with log1p, mean-centered, not variance-scaled, then decomposed by NumPy SVD.",
        "visual_grammar": "Each point is one BGC; panels are declared genera; color is declared cohort; triangles mark assembly FLAG rows; axes are PC scores.",
        "statistics_uncertainty": "Descriptive ordination only; no hypothesis tests, confidence intervals, product calls, or biological-effect estimates are supplied.",
        "comparison_group": "Declared default-on STUDY cohort, with default-off roles excluded from displayed denominators.",
        "genus_control": "Within-genus facets are shown" if len(genera) == 1 else "Genus facets show composition; no cross-genus statistical inference is made.",
        "contradictions": "Missing source binding, incomplete locus identity, duplicate BGC source row, or invalid count produces a HOLD rather than artwork.",
        "interpretation_boundary": F13_CLAIM_CEILING,
    }
    caption_receipt = _figure_policy.validate_caption_methods(caption, nonstandard_visual=True)
    caption_path = target / "F13_bgc_domain_pca_2d_caption_methods.json"
    _f13_write_json(caption_path, {**caption, "validation": caption_receipt})
    notes_path = target / "F13_bgc_domain_pca_2d_owner_notes.json"
    _f13_write_json(notes_path, {
        "schema_version": F13_SCHEMA_VERSION,
        "status": "EMPTY_OWNER_NOTES",
        "notes": [],
        "separate_from_caption_methods": True,
    })
    provenance_path = target / "F13_bgc_domain_pca_2d_provenance.json"
    _f13_write_json(provenance_path, {
        "schema_version": F13_SCHEMA_VERSION,
        "status": "SOURCE_ARTWORK_CANDIDATE_NOT_SCIENTIFIC_ACCEPTANCE",
        "cohort_manifest": {"filename": cohort["path"].name, "sha256": cohort["digest"]},
        "cohort_policy": cohort["policy_receipt"],
        "denominator_policy": denominator_receipt,
        "eligible_default_study_identities": sorted(cohort["eligible"]),
        "excluded_default_off_or_nonstudy_identities": cohort["excluded"],
        "source_bindings": source_bindings,
        "feature_order": list(F13_VOCAB),
        "transformation": "log1p then mean-center; no variance scaling",
        "pca": {
            "algorithm": "numpy.linalg.svd",
            "explained_variance_fraction": [float(value) for value in explained],
            "loadings": {
                "PC1": {feature: float(vt[0, index]) for index, feature in enumerate(F13_VOCAB)},
                "PC2": {feature: float(vt[1, index]) for index, feature in enumerate(F13_VOCAB)},
            },
        },
        "genus_policy": genus_receipt,
        "cohort_palette": palette_receipt,
        "artwork_validation": artwork_receipt,
        "claim_ceiling": F13_CLAIM_CEILING,
        "pdf_delivery": "PENDING_SHARED_POST_EMBED_PDF_GATE",
    })
    artifacts = [_f13_file_receipt(path) for path in (
        svg_path.with_suffix(".png"), svg_path, csv_path, caption_path, notes_path, provenance_path
    )]
    receipt_path = target / "F13_bgc_domain_pca_2d_receipt.json"
    _f13_write_json(receipt_path, {
        "schema_version": F13_SCHEMA_VERSION,
        "status": "PASS_SOURCE_ARTWORK_ONLY",
        "artifacts": artifacts,
        "plotted_bgc_rows": len(rows),
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "genus_counts": dict(sorted(genus_counts.items())),
        "pdf_delivery": "PENDING_SHARED_POST_EMBED_PDF_GATE",
        "claim_ceiling": F13_CLAIM_CEILING,
    })
    return {"status": "PASS_SOURCE_ARTWORK_ONLY", "svg": str(svg_path),
            "receipt": str(receipt_path), "plotted_bgc_rows": len(rows)}

def _strain_num(sid):
    import re
    m=re.search(r"(\d+)", sid or "")
    return int(m.group(1)) if m else 10**9

def order_strains(S, explicit=None):
    # explicit wins — this is the hook for a data-clustering order (e.g. dendrogram leaf
    # order from the domain matrix); pass it in and it is used verbatim.
    if explicit: return [s for s in explicit if s in S]
    # Default: ascending strain number, so panels line up by ID across figures and the axis
    # is reproducible/scannable. (v9.7.222: was raw_bgcs + public/private split; the AS cohort
    # is public at publication, so the split is retired and the axis is a single ID-ordered run.)
    return sorted(S, key=lambda s:(_strain_num(s), s))

def sidecar(path, header, rows):
    with open(path,"w",newline="", encoding="utf-8") as fh:
        w=_SafeWriter(fh); w.writerow(header); w.writerows(rows)

def stamp(fig, fid):
    FIGNUM[0]+=1
    tag=f"F{FIGNUM[0]:02d} · {fid}"
    # v9.7.162: place tag in its own reserved band BELOW the x-tick labels via supxlabel
    # (constrained_layout-aware). fig.text at y=0.004 sat at the same height as the rotated
    # BGC tick labels and overlapped regardless of ha; supxlabel is placed under them.
    fig.supxlabel(tag, fontsize=6, color="#9a9a9a")
    return f"F{FIGNUM[0]:02d}_{fid}"

def soft_divider(ax, ndiv, npriv, y=-0.55):
    # v9.7.222: PUBLIC/PRIVATE divider + labels removed — the AS cohort is public at publication
    # (PI decision 2026-07-06). Kept as a no-op so the ~9 call sites need no change.
    return

def domain_counts(S, order):
    dc=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for h in S[s]["deep"].get("domain_hits",[]):
            p=h.get("pfam") or h.get("domain")
            if p: dc[p][s]+=1
    return dc

def heatmap(mat, rowlabs, order, S, title, fid, OUT, cbar="count", lognorm=True,
            annot=True, cmap="magma_r", row_raw=None, divider=True):
    mat=np.array(mat,float)
    if mat.size == 0:
        # v9.7.375 (audit lane: cohort_figures_f_series_empty_matrix_crash): heatmap() is the
        # F-series third copy of the shared rendering logic; its two siblings hmap() (G) and
        # bubble_matrix() (D) got this early-return placeholder in v9.7.267, but heatmap() was left
        # exposed — an empty row list (a cohort where no strain carries any CCTT trigger, or an
        # unpopulated resistance-axis scan) reached ax.imshow() with a zero-size array and raised
        # "Invalid shape (0,) for image data", aborting figs_multi() and every remaining F-series
        # figure for the whole batch. Render a labelled empty-state panel instead so the run
        # completes and the gap stays visible.
        fig,ax=plt.subplots(figsize=(6.0,2.2),constrained_layout=True)
        ax.text(0.5,0.5,f"{title}\n(no data for this view)",ha="center",va="center",fontsize=10,color="#666")
        ax.axis("off")
        fname=stamp(fig,fid); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
        return
    npriv=sum(1 for s in order if is_private(s)); ndiv=len(order)-npriv
    fig_w=max(8.0, 1.55*len(order)+3.4); fig_h=max(3.4, 0.36*len(rowlabs)+2.6)
    fig,ax=plt.subplots(figsize=(fig_w,fig_h),constrained_layout=True)
    if lognorm:
        disp=np.where(mat<=0,np.nan,mat)
        # B-empty (v9.7.212 audit follow-on): the line-450 guard fixed ONE nanmax site but left this
        # shared heatmap() helper exposed to the same crash — an empty cohort or an all-zero/all-negative
        # strain row makes disp empty/all-NaN, and np.nanmin/np.nanmax then raise (ValueError zero-size /
        # all-NaN RuntimeWarning). Guard both bounds; fall back to a benign 1..2 range so the (empty) grid
        # still renders instead of crashing the whole figure run.
        _ok = disp.size and not np.all(np.isnan(disp))
        _vmin = max(1,np.nanmin(disp)) if _ok else 1
        _vmax = max(_vmin+1, np.nanmax(disp)) if _ok else 2
        im=ax.imshow(disp,aspect="auto",cmap=cmap,norm=LogNorm(vmin=_vmin,vmax=_vmax))
    else:
        im=ax.imshow(mat,aspect="auto",cmap=cmap)
    ax.set_xticks(range(len(order))); ax.set_xticklabels([lab(s) for s in order],fontsize=8)
    ax.set_yticks(range(len(rowlabs))); ax.set_yticklabels(rowlabs,fontsize=8.5); ax.tick_params(length=0)
    if annot:
        mx=(np.nanmax(mat) if mat.size and not np.all(np.isnan(mat)) else 0) or 1   # empty/all-NaN-safe (audit follow-on)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v=mat[i,j]
                if v==0: ax.text(j,i,"0",ha="center",va="center",fontsize=6.5,color="#ccc"); continue
                txt=f"{v:.0f}" if abs(v-round(v))<1e-6 else f"{v:.1f}"
                dark=(lognorm and v>mx*0.10) or (not lognorm and v>mx*0.55)
                ax.text(j,i,txt,ha="center",va="center",fontsize=7,color="white" if dark else "#111")
    if divider: soft_divider(ax,ndiv,npriv)
    ax.set_title(title,pad=24)
    cb=fig.colorbar(im,ax=ax,fraction=0.024,pad=0.012); cb.set_label(cbar,fontsize=9)
    fname=stamp(fig,fid); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["row"]+list(order),
            [[(row_raw or rowlabs)[i]]+list(mat[i]) for i in range(len(rowlabs))])

def products_per_strain(S, order):
    pc=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        invf=glob.glob(f"{S[s]['pkg']}/*_2_inventory.csv")
        if not invf: continue
        for row in csv.DictReader(open(invf[0], encoding="utf-8")):
            for t in (row.get("Products") or "").replace(";",",").split(","):
                t=t.strip()
                if t: pc[t][s]+=1
    return pc

_RIPP_PRODUCT_RE = re.compile(r"ripp|lanthipeptide|lassopeptide|thiopeptide|\bLAP\b|sactipeptide|"
                              r"bottromycin|linaridin|lipolanthine|microviridin|lanthidin|crocagin", re.I)

def _ripp_product_count(pkg):
    """RiPP-1: count BGCs with a RiPP-family antiSMASH PRODUCT CLASS (always present in the inventory),
    not the mode-gated gene.ripp scan (empty when json_mode:off). Reads the inventory/triage Products col."""
    inv = next(iter(glob.glob(f"{pkg}/*_2_inventory.csv") or glob.glob(f"{pkg}/*_4_triage_board.csv")), None)
    if not inv:
        raise FileNotFoundError(f"RiPP product count requires an inventory or triage table under {pkg}")
    with open(inv, encoding="utf-8") as handle:
        return sum(1 for row in csv.DictReader(handle)
                   if _RIPP_PRODUCT_RE.search(str(row.get("Products") or "")))


def _domain_counts_from_architecture(record):
    """Parse one required domain-architecture mapping without masking corruption."""
    try:
        parsed = ast.literal_eval(record["architecture"])
    except (KeyError, TypeError, ValueError, SyntaxError) as exc:
        raise ValueError(f"invalid domain architecture: {exc}") from exc
    counts = parsed.get("domain_counts") if isinstance(parsed, dict) else None
    if not isinstance(counts, dict):
        raise ValueError("invalid domain architecture: domain_counts mapping required")
    return counts


def figs_multi(S, order, OUT, *, f13_cohort_manifest=None,
               f13_cohort_manifest_sha256=None, f13_denominator_registry=None,
               f13_denominator_registry_sha256=None, f13_profile="SINGLE_COLUMN"):
    dc=domain_counts(S,order); tier={s:S[s]["ms"]["assembly_tier"] for s in order}
    npriv=sum(1 for s in order if is_private(s)); ndiv=len(order)-npriv

    # F01 census z-score (NO heavy black bar; soft divider only)
    metrics=[("total_domain_hits","domain hits"),("distinct_pfam","distinct Pfam"),
             ("tier1_core_domains","core domains"),("active_site_confirmations","active-site calls"),
             ("ripp_calls","RiPP calls")]
    def census_val(s, key):
        deep=S[s]["deep"]; dh=deep.get("domain_hits",[])
        if key=="total_domain_hits": return len(dh)
        if key=="distinct_pfam": return len(set((h.get("pfam") or h.get("domain")) for h in dh))
        if key=="tier1_core_domains": return sum(1 for h in dh if h.get("tier1"))
        if key=="active_site_confirmations": return len(deep.get("active_sites",[]))
        if key=="ripp_calls":
            return _ripp_product_count(S[s]["pkg"])   # RiPP-1: product classes, not gene.ripp
        return 0
    raw=np.array([[float(census_val(s,m)) for s in order] for m,_ in metrics])
    # ActiveSite-1 / false-absence guard: drop any metric whose row is all-zero across every strain — a
    # z-score of an all-zero row is a meaningless flat band that reads as measured absence (e.g. active-site
    # calls when json_mode:off leaves active_sites empty). Don't render an unpopulated scan as data.
    keep=[i for i in range(raw.shape[0]) if raw[i].any()]
    census_dropped=[metrics[i][1] for i in range(len(metrics)) if i not in keep]
    if keep and len(keep)<len(metrics):
        metrics=[metrics[i] for i in keep]; raw=raw[keep]
    z=(raw-raw.mean(1,keepdims=True))/(raw.std(1,keepdims=True)+1e-9)
    fig,ax=plt.subplots(figsize=(max(8.5,1.55*len(order)+3.4),5.0),constrained_layout=True)
    im=ax.imshow(z,aspect="auto",cmap="RdBu_r",vmin=-2,vmax=2)
    ax.set_xticks(range(len(order))); ax.set_xticklabels([lab(s) for s in order],fontsize=8)
    ax.set_yticks(range(len(metrics))); ax.set_yticklabels([l for _,l in metrics],fontsize=9); ax.tick_params(length=0)
    for i in range(raw.shape[0]):
        for j in range(raw.shape[1]):
            ax.text(j,i,f"{raw[i,j]:.0f}",ha="center",va="center",fontsize=8,color="white" if abs(z[i,j])>1.3 else "#111")
    for j,s in enumerate(order):
        ax.add_patch(plt.Rectangle((j-0.5,-1.2),1,0.45,color=TCOLOR.get(tier[s],"#999"),clip_on=False))
    if npriv: ax.axvline(ndiv-0.5,color="#9a9a9a",lw=1.1,ls=(0,(4,3)))
    ax.set_ylim(len(metrics)-0.5,-1.35)
    ax.set_title("Per-strain gene/domain census  (cells = raw counts; colour = z-score per metric;\n"
                 "top strip = assembly tier)",pad=30,fontsize=11)
    cb=fig.colorbar(im,ax=ax,fraction=0.024,pad=0.012); cb.set_label("z-score (within metric)",fontsize=9)
    fname=stamp(fig,"census_zscore_heatmap"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["metric"]+order,[[metrics[i][1]]+list(raw[i]) for i in range(len(metrics))])

    # F02 megasynthase core
    core=[("PKS_KS","ketosynthase"),("PKS_AT","acyltransferase"),("PKS_KR","ketoreductase"),
          ("PKS_DH","dehydratase"),("PKS_ER","enoylreductase"),("ACP","ACP"),("PP-binding","PCP/ACP"),
          ("Condensation","NRPS C"),("AMP-binding","NRPS A"),("Epimerization","NRPS E"),
          ("Thioesterase","TE release"),("LANC_like","lanthipeptide cyclase"),("YcaO","YcaO RiPP")]
    heatmap([[dc[d].get(s,0) for s in order] for d,_ in core],[f"{d}  ({l})" for d,l in core],order,S,
            "Megasynthase / NRPS-PKS catalytic core (domain counts, all BGCs)",
            "megasynthase_heatmap",OUT,cbar="domain count",row_raw=[d for d,_ in core])

    # F03 product-class heatmap (+ computed macrolide-type proxy row)
    pc=products_per_strain(S,order)
    keep=["saccharide","PKS","T1PKS","T2PKS","T3PKS","transAT-PKS","NRPS","NRPS-like","NRP-metallophore",
          "NI-siderophore","RiPP","RiPP-like","RRE-containing","lanthipeptide-class-ii","lanthipeptide-class-iii",
          "terpene","halogenated","butyrolactone","ectoine","indole","fatty_acid","nucleoside","NAPAA","other"]
    # BC2_399 fix (CORRECTED v2 — see PATCH_CARD.md "correction" section): `pc` is keyed by
    # the raw antiSMASH Products token as written to _2_inventory.csv, with no case
    # normalization applied by products_per_strain() above. This is HARDENING against a mixed-
    # case cohort (a board from an older/differently-configured antiSMASH run, or any future
    # casing drift), not a fix for a demonstrated defect on current-engine data — verified
    # against a real engine-1.9.142 strict-profile cohort board that real Products tokens are
    # already canon-cased and match `keep`'s own casing exactly. `keep`'s casing is kept as
    # the row LABEL (readability); only the lookup into `pc` is done case-insensitively.
    #
    # CORRECTION (independent peer review): the original v1 fix here,
    # `pc_ci = {k.lower(): v for k, v in pc.items()}`, REPLACES on a case collision instead of
    # merging — if `pc` ever legitimately holds both "NRPS" and "nrps" as separate keys (the
    # exact mixed-case scenario this hardening exists for), the dict comprehension silently
    # drops one spelling's entire per-strain count dict, the same class of data loss this patch
    # was written to prevent. Fixed to merge (sum) per-strain counts across any case-variant
    # keys, matching the B2 sibling fix's `+=` shape.
    pc_ci = collections.defaultdict(lambda: collections.defaultdict(int))
    for _k, _sub in pc.items():
        for _s, _n in _sub.items():
            pc_ci[_k.lower()][_s] += _n
    rows=[k for k in keep if k.lower() in pc_ci]
    # macrolide-type proxy: BGCs with reductive PKS loop (KR & DH present)
    macro=collections.defaultdict(int)
    for s in order:
        for da in S[s]["gene"].get("domain_arch",[]):
            a=_domain_counts_from_architecture(da)
            if a.get("PKS_KR",0)>0 and a.get("PKS_DH",0)>0: macro[s]+=1
    mat=[[pc_ci[k.lower()].get(s,0) for s in order] for k in rows]+[[macro.get(s,0) for s in order]]
    rl=rows+["macrolide-type (reduced-PKS proxy*)"]
    heatmap(mat,rl,order,S,"BGC product classes per strain (antiSMASH; * = computed proxy, not a class)",
            "product_class_heatmap",OUT,cbar="BGC count",row_raw=rl)

    # F04 tailoring / accessory enzyme heatmap (domain counts)
    tail=[("Trp_halogenase","halogenase (Trp_halogenase)"),("Glyco_hydro_18","chitinase (GH18)"),
          ("IucA_IucC","siderophore synthetase (IucA/IucC)"),("FhuF","siderophore reductase (FhuF)"),
          ("Metallophos","metallophosphatase"),("Ni_hydr_CYTB","Ni-hydrogenase cytb"),
          ("Aminotransferase","aminotransferase"),("Methyltransf_2","O/N-methyltransferase"),
          ("p450","cytochrome P450"),("Glycos_transf_1","glycosyltransferase")]
    trows=[(d,l) for d,l in tail if dc.get(d)]
    if trows:
        heatmap([[dc[d].get(s,0) for s in order] for d,_ in trows],[l for _,l in trows],order,S,
                "Tailoring / accessory enzymes per strain (domain counts)",
                "tailoring_enzyme_heatmap",OUT,cbar="domain count",cmap="rocket_r" if "rocket_r" in plt.colormaps() else "magma_r",row_raw=[d for d,_ in trows])

    # F05 CCTT triggers
    cct=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for b in S[s]["deep"]["bgc_profile"]:
            for t in (b.get("cctt_triggers") or "").split(","):
                t=t.strip()
                if t: cct[t][s]+=1
    ck=sorted(cct,key=lambda k:-sum(cct[k].values()))
    heatmap([[cct[k].get(s,0) for s in order] for k in ck],[k.replace("T43-","") for k in ck],order,S,
            "CCTT diagnostic-chemistry triggers per strain (BGC counts)","cctt_trigger_heatmap",OUT,
            cbar="BGCs w/ trigger",row_raw=ck)

    # F06 resistance tiers
    rt=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for b in S[s]["deep"]["bgc_profile"]:
            v=b.get("resistance_tier")
            if v: rt[v][s]+=1
    rk=["T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED","T2_RESISTANCE_LIKE_SOURCE_DERIVED","T3_TRANSPORTER_ONLY_ROUTING","NULL_NO_SOURCE_DERIVED_RESISTANCE"]
    rk=[k for k in rk if k in rt]+[k for k in rt if k not in rk]
    heatmap([[rt[k].get(s,0) for s in order] for k in rk],
            [k.replace("_SOURCE_DERIVED","").replace("_NO_SOURCE_DERIVED_RESISTANCE","")[:24] for k in rk],
            order,S,"Resistance-axis tier distribution per strain (BGC counts)","resistance_tier_heatmap",OUT,cbar="BGCs",row_raw=rk)

    # F07/F08 substrate + AT
    def subhm(filt,fid,title,cbar,cmap):
        d=collections.defaultdict(lambda: collections.defaultdict(int))
        for s in order:
            for sub in S[s]["gene"].get("substrates",[]):
                if filt not in sub.get("domain_id",""): continue
                v=(sub.get("substrate") or "").strip()
                if v and v.lower() not in ("nan","none",""): d[v][s]+=1
        ks=sorted(d,key=lambda k:-sum(d[k].values()))[:15]
        if ks: heatmap([[d[k].get(s,0) for s in order] for k in ks],ks,order,S,title,fid,OUT,cbar=cbar,cmap=cmap,row_raw=ks)
    subhm("AMP-binding","adomain_substrate_heatmap","NRPS A-domain substrate consensus (inferred)","A-domains","viridis")
    subhm("PKS_AT","AT_extender_heatmap","PKS AT extender-unit consensus (inferred)","AT domains","cividis")

    # F09 transporter families
    tfam=["ABC_tran","MFS_1","MFS_3","AA_permease","AA_permease_2","GntP_permease","Xan_ur_permease","NMN_transporter","MatE"]
    tfam=[d for d in tfam if dc.get(d)]
    heatmap([[dc[d].get(s,0) for s in order] for d in tfam],tfam,order,S,
            "Transporter families per strain (domain counts)","transporter_family_heatmap",OUT,cbar="domain count",cmap="mako_r" if "mako_r" in plt.colormaps() else "viridis",row_raw=tfam)

    # F10 selected raw antiSMASH domain tokens. These are annotation-token
    # occurrences, not independently called regulator genes or validated functions.
    rfam=["TetR_N","GntR","LysR_substrate","HTH_1","Sigma70_r2","Sigma70_r4_2","HTH_31","HTH_18","MarR_2","HTH_30","AraC_binding"]
    rfam=[d for d in rfam if dc.get(d)]
    heatmap([[dc[d].get(s,0) for s in order] for d in rfam],rfam,order,S,
            "Selected upstream antiSMASH domain tokens per strain (retained occurrence counts)",
            "regulator_TF_heatmap",OUT,cbar="retained occurrences",cmap="magma_r",row_raw=rfam)

    # F11 REDESIGN hold: legacy deep_data.domain_hits flattens all retained
    # dinfo.domains and does not carry the feature-type/accession provenance
    # required to distinguish PFAM_domain rows from aSDomain, motif, TIGRFAM,
    # and tool-like labels. Do not emit a misleading "Pfam-only" figure.
    # The future domain adapter must provide explicit source class, accession,
    # feature identity, and per-BGC overlap provenance before this view returns.
    with open(f"{OUT}/F11_domain_clustermap_top40_HOLD.json", "w", encoding="utf-8") as fh:
        _j.dump({
            "schema_version": "sapote.figure-factory.figure-hold.v1",
            "figure_id": "F11_domain_clustermap_top40",
            "status": "REDESIGN_NOT_PUBLICATION_READY",
            "reason_code": "F11_MIXED_TOKEN_SOURCE_CLASS_UNBOUND",
            "required_fields": [
                "feature_type", "accession", "annotation_source",
                "source_feature_identity", "bgc_overlap_assignment",
            ],
            "release_condition": (
                "Source-class-filter domain observations before ranking and bind exact feature "
                "type, accession, provenance, deduplication, and overlap semantics."
            ),
        }, fh, indent=2, sort_keys=True)
        fh.write("\n")

    # F12 active-site completeness bars
    comp={}; ng={}
    for s in order:
        by=collections.defaultdict(lambda:[0,0])
        for a in S[s]["deep"].get("active_sites",[]):
            b=re.findall(r":\s*(True|False)",a.get("active_site_calls",""))
            m=re.search(r"(ctg\d+_\d+)",a.get("domain_id","")+a.get("locus",""))
            g=m.group(1) if m else "g?"; by[g][0]+=sum(1 for x in b if x=="True"); by[g][1]+=len(b)
        tf=sum(v[0] for v in by.values()); tt=sum(v[1] for v in by.values())
        comp[s]=100*tf/tt if tt else 0; ng[s]=len(by)
    as_scanned=any(ng[s] for s in order)   # ActiveSite-1: was active-site scan populated at all?
    fig,ax=plt.subplots(figsize=(max(8.5,1.45*len(order)+3),4.6),constrained_layout=True)
    ax.bar(range(len(order)),[comp[s] for s in order],color=[TCOLOR.get(tier[s],"#999") for s in order],edgecolor="#222")
    for i,s in enumerate(order):
        ax.text(i,comp[s]+1.0,(f"{comp[s]:.0f}%" if as_scanned else "n/a"),ha="center",fontsize=8,fontweight="bold")
    if not as_scanned:
        # active_sites empty for every strain (json_mode:off / SOURCE_DERIVED_BEST_EFFORT) — do NOT present
        # 0% as a measured completeness. Say so on the figure.
        ax.text(0.5,0.5,"active-site scan not populated in these packages\n(json_mode:off) — not a measured 0%",
                transform=ax.transAxes,ha="center",va="center",fontsize=11,color="#b00",
                bbox=dict(boxstyle="round",fc="#fff4f4",ec="#b00",alpha=0.95))
        ax.text(i,4,f"{ng[s]}",ha="center",fontsize=7,color="white")
    ax.set_xticks(range(len(order))); ax.set_xticklabels([lab(s) for s in order],fontsize=8)
    ax.set_ylabel("active-site completeness (%)"); ax.set_ylim(0,108); ax.tick_params(length=0)
    ax.set_title("Active-site completeness per strain (catalytic genes; n above bar)",pad=12)
    if npriv: ax.axvline(ndiv-0.5,color="#9a9a9a",lw=1.1,ls=(0,(4,3)))
    ax.legend(handles=[mp.Patch(color=TCOLOR[t],label=t) for t in ["GOOD","MODERATE","POOR","VERY_POOR"]],
              fontsize=7.5,bbox_to_anchor=(1.02,1.0),loc="upper left",borderaxespad=0)
    fname=stamp(fig,"active_site_completeness"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["strain","tier","catalytic_genes","completeness_pct"],
            [[s,tier[s],ng[s],round(comp[s],1)] for s in order])

    # F13/F14/F15 ordinations
    # P12-residual: Oxidoreductase/Aminotransferase/Transporter/Regulator are separate genes, never
    # aSDomain architecture tokens, so those dims were always-zero (dead features padding every vector).
    # Restrict the vocab to tokens domain_arch can actually carry.
    vocab=["PKS_KS","PKS_AT","PKS_KR","PKS_DH","PKS_ER","PKS_ACP","NRPS_C","NRPS_A","NRPS_T_PCP",
           "TE_release"]
    vecs=[]; meta=[]
    for s in order:
        for da in S[s]["gene"].get("domain_arch",[]):
            a=_domain_counts_from_architecture(da)
            v=np.array([a.get(k,0) for k in vocab],float)
            if v.sum()==0: continue
            vecs.append(v); meta.append((s,da["bgc_id"]))
    X=np.log1p(np.array(vecs)); Xc=X-X.mean(0); U,Sg,Vt=np.linalg.svd(Xc,full_matrices=False)
    PC=Xc@Vt[:2].T; _ss=np.sum(Sg**2); ev=(Sg**2)/_ss if _ss>0 else np.zeros_like(Sg)
    # F13 is source artwork only when cohort and package provenance are bound.  In
    # every other case _render_f13_domain_pca writes a HOLD receipt and leaves no
    # new F13 PNG/SVG behind.  F14/F15 retain the historic matrix below.
    _render_f13_domain_pca(
        S, order, OUT, cohort_manifest=f13_cohort_manifest,
        cohort_manifest_sha256=f13_cohort_manifest_sha256,
        denominator_registry=f13_denominator_registry,
        denominator_registry_sha256=f13_denominator_registry_sha256,
        profile=f13_profile,
    )

    Xn=X/(np.linalg.norm(X,axis=1,keepdims=True)+1e-9); sim=Xn@Xn.T
    n=len(meta); asg=[-1]*n; c=0
    for i in range(n):
        if asg[i]!=-1: continue
        asg[i]=c
        for j in range(i+1,n):
            if asg[j]==-1 and sim[i,j]>=0.85: asg[j]=c
        c+=1
    sizes=collections.Counter(asg); big=[k for k,_ in sizes.most_common(8)]
    fig,ax=plt.subplots(figsize=(9.4,6.4)); pal2=plt.cm.tab10(np.linspace(0,1,len(big)))
    for i in range(n):
        cl=asg[i]
        if cl in big: ax.scatter(PC[i,0],PC[i,1],s=26,color=pal2[big.index(cl)],alpha=0.85,edgecolor="#222",linewidth=0.3)
        else: ax.scatter(PC[i,0],PC[i,1],s=12,color="#cccccc",alpha=0.5)
    for gi,cl in enumerate(big): ax.scatter([],[],color=pal2[gi],label=f"cluster {cl} (n={sizes[cl]})")
    ax.scatter([],[],color="#cccccc",label="other")
    ax.set_xlabel(f"PC1 ({ev[0]*100:.0f}% var)"); ax.set_ylabel(f"PC2 ({ev[1]*100:.0f}% var)")
    ax.set_title("BGC domain space coloured by architecture cluster (top 8)",pad=12); ax.grid(alpha=0.2)
    ax.legend(fontsize=8,bbox_to_anchor=(1.02,1.0),loc="upper left",borderaxespad=0)
    fname=stamp(fig,"bgc_pca_by_cluster"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["strain","bgc_id","PC1","PC2","cluster"],[[meta[i][0],meta[i][1],round(PC[i,0],4),round(PC[i,1],4),asg[i]] for i in range(n)])

    prof=[]
    for s in order:
        idx=[i for i,m in enumerate(meta) if m[0]==s]; prof.append(X[idx].mean(0))
    P=np.array(prof); Pc=P-P.mean(0); Us,Ss,Vts=np.linalg.svd(Pc,full_matrices=False)
    SP=Pc@Vts[:2].T; _sss=np.sum(Ss**2); evs=(Ss**2)/_sss if _sss>0 else np.zeros_like(Ss)
    fig,ax=plt.subplots(figsize=(9.0,6.2))
    for i,s in enumerate(order):
        priv=is_private(s)
        ax.scatter(SP[i,0],SP[i,1],s=330,marker="D" if priv else "o",color=TCOLOR.get(tier[s],"#999"),edgecolor="#111",linewidth=1.5 if priv else 0.8,zorder=3)
        ax.annotate(f"{s}"+("\n(PRIV)" if priv else ""),(SP[i,0],SP[i,1]),fontsize=8,fontweight="bold",xytext=(8,8),textcoords="offset points")
    ax.set_xlabel(f"PC1 ({evs[0]*100:.0f}% var)"); ax.set_ylabel(f"PC2 ({evs[1]*100:.0f}% var)")
    ax.set_title("Strain ordination by mean BGC domain profile",pad=12); ax.grid(alpha=0.2)
    ax.legend(handles=[mp.Patch(color=TCOLOR[t],label=t) for t in ["GOOD","MODERATE","POOR","VERY_POOR"]]+
                      [plt.Line2D([],[],marker="D",color="w",markerfacecolor="#888",markeredgecolor="#111",label="PRIVATE")],
              fontsize=7.5,bbox_to_anchor=(1.02,1.0),loc="upper left",borderaxespad=0)
    fname=stamp(fig,"strain_ordination_2d"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["strain","tier","PC1","PC2"],[[order[i],tier[order[i]],round(SP[i,0],4),round(SP[i,1],4)] for i in range(len(order))])

def figs_single(S, sid, OUT):
    deep=S[sid]["deep"]
    # v9.7.185 P12: this per-BGC heatmap is fed from aSDomain counts. Transporters/regulators/
    # oxidoreductases are separate genes (never aSDomains), so those rows were always zero — a false
    # "absent" signal. They live in the dedicated gene-level figures (transporter_family_heatmap,
    # bubble_regulators). Show only rows this data source can populate.
    core=["PKS_KS","PKS_AT","PKS_KR","PKS_DH","NRPS_C","NRPS_A","NRPS_T_PCP","TE_release"]
    bgcids=[]; rows=[]
    for b in deep["bgc_profile"]:
        bgcids.append(b["bgc_id"]); rows.append([b.get(k,0) or 0 for k in core])
    M=np.array(rows,float).reshape(-1,len(core)); tot=M.sum(1) if M.size else np.zeros(0); keep=np.argsort(-tot)[:40]; M=M[keep]; bk=[bgcids[i] for i in keep]
    fig,ax=plt.subplots(figsize=(max(9,0.22*len(bk)+4),5.5),constrained_layout=True)
    disp=np.where(M.T<=0,np.nan,M.T)
    _vmax=max(2,np.nanmax(disp)) if disp.size and not np.all(np.isnan(disp)) else 2   # empty/all-zero strain -> no crash (Nocardia patch B)
    im=ax.imshow(disp,aspect="auto",cmap="magma_r",norm=LogNorm(vmin=1,vmax=_vmax))
    ax.set_yticks(range(len(core))); ax.set_yticklabels(core,fontsize=8)
    ax.set_xticks(range(len(bk))); ax.set_xticklabels(bk,rotation=90,fontsize=6); ax.tick_params(length=0)
    ax.set_title(f"{genus(sid)} strain {sid} — per-BGC catalytic domain composition (top {len(bk)} BGCs)",pad=14)
    cb=fig.colorbar(im,ax=ax,fraction=0.02,pad=0.01); cb.set_label("domain count",fontsize=8)
    fname=stamp(fig,f"{sid}_perBGC_domain_heatmap"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["bgc_id"]+core,[[bk[i]]+list(M[i]) for i in range(len(bk))])

    # S2 per-BGC active-site completeness (bars, ordered)
    bygene={}
    for a in deep.get("active_sites",[]):
        b=re.findall(r":\s*(True|False)",a.get("active_site_calls",""))
        m=re.search(r"(ctg\d+_\d+)",a.get("domain_id","")+a.get("locus",""))
        g=m.group(1) if m else "g?"; bygene.setdefault(g,[0,0]); bygene[g][0]+=sum(1 for x in b if x=="True"); bygene[g][1]+=len(b)
    genes=[(g,100*v[0]/v[1]) for g,v in bygene.items() if v[1]]; genes.sort(key=lambda x:-x[1])
    if genes:
        fig,ax=plt.subplots(figsize=(max(9,0.24*len(genes)+3),4.4),constrained_layout=True)
        ax.bar(range(len(genes)),[c for _,c in genes],color="#3a7ca5",edgecolor="#222")
        ax.set_xticks(range(len(genes))); ax.set_xticklabels([g for g,_ in genes],rotation=90,fontsize=6)
        ax.set_ylabel("active-site completeness (%)"); ax.set_ylim(0,105); ax.tick_params(length=0)
        ax.axhline(100,ls=":",color="#888",lw=0.8)
        ax.set_title(f"{genus(sid)} strain {sid} — per-catalytic-gene active-site completeness",pad=12)
        fname=stamp(fig,f"{sid}_perGene_active_site_completeness"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
        sidecar(f"{OUT}/{fname}_data.csv",["catalytic_gene","completeness_pct"],[[g,round(c,1)] for g,c in genes])

    # S3 per-BGC CCTT trigger presence + resistance tier strip
    trig=set()
    for b in deep["bgc_profile"]:
        for t in (b.get("cctt_triggers") or "").split(","):
            t=t.strip()
            if t: trig.add(t)
    trig=sorted(trig)
    bgcs=[b for b in deep["bgc_profile"] if (b.get("cctt_triggers") or "").strip()]
    if trig and bgcs:
        Mt=np.array([[1 if t in (b.get("cctt_triggers") or "") else 0 for b in bgcs] for t in trig],float)
        rtmap={"T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED":"#b2182b","T2_RESISTANCE_LIKE_SOURCE_DERIVED":"#ef8a62",
               "T3_TRANSPORTER_ONLY_ROUTING":"#67a9cf","NULL_NO_SOURCE_DERIVED_RESISTANCE":"#f7f7f7"}
        fig,ax=plt.subplots(figsize=(max(9,0.30*len(bgcs)+3),0.4*len(trig)+3),constrained_layout=True)
        ax.imshow(Mt,aspect="auto",cmap="Greens",vmin=0,vmax=1)
        ax.set_yticks(range(len(trig))); ax.set_yticklabels([t.replace("T43-","") for t in trig],fontsize=8)
        ax.set_xticks(range(len(bgcs))); ax.set_xticklabels([b["bgc_id"] for b in bgcs],rotation=90,fontsize=6); ax.tick_params(length=0)
        for j,b in enumerate(bgcs):
            ax.add_patch(plt.Rectangle((j-0.5,-1.1),1,0.5,color=rtmap.get(b.get("resistance_tier"),"#ccc"),clip_on=False))
        ax.set_ylim(len(trig)-0.5,-1.25)
        # v9.7.400: define the strip ON the figure — the tier colours were previously undefined
        # anywhere on the rendered image (an unlabeled orange/red/blue band). Claim-safe wording:
        # tiers are source-derived routing strata, not resistance assertions.
        _tier_label={"T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED":"T1 diagnostic self-protection (source-derived)",
                     "T2_RESISTANCE_LIKE_SOURCE_DERIVED":"T2 resistance-like (source-derived)",
                     "T3_TRANSPORTER_ONLY_ROUTING":"T3 transporter-only routing",
                     "NULL_NO_SOURCE_DERIVED_RESISTANCE":"no source-derived resistance signal"}
        _unmapped=sorted({(b.get("resistance_tier") or "") for b in bgcs} - set(rtmap))
        _handles=[mp.Patch(facecolor=rtmap[k],edgecolor="#888",label=_tier_label[k]) for k in rtmap]
        if _unmapped:
            _handles.append(mp.Patch(facecolor="#ccc",edgecolor="#888",label="other/unmapped tier"))
        ax.legend(handles=_handles,title="resistance tier strip (top band)",fontsize=7,title_fontsize=8,
                  loc="upper left",bbox_to_anchor=(1.01,1.0),borderaxespad=0,frameon=False)
        ax.set_title(f"{genus(sid)} strain {sid} — per-BGC CCTT triggers (green) + resistance tier strip",pad=18)
        fname=stamp(fig,f"{sid}_perBGC_cctt_resistance"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
        sidecar(f"{OUT}/{fname}_data.csv",["cctt_trigger"]+[b["bgc_id"] for b in bgcs],
                [[trig[i]]+list(Mt[i]) for i in range(len(trig))])
    emit(f"  single-strain figures for {sid} written")

def generate(runs_dir="runs_gold", out="cohort_figures", strains=None, public_only=False, series="F",
             f13_cohort_manifest=None, f13_cohort_manifest_sha256=None,
             f13_denominator_registry=None, f13_denominator_registry_sha256=None,
             f13_profile="SINGLE_COLUMN"):
    """Emit the gold gene/domain figure suite. strains: optional explicit order/subset.
    series: F = cross-strain heatmaps (default) | G = complementary (rarity / novelty /
    architecture / similarity) | D = dot/bubble plots | all = F+G+D. A single strain with
    series F gets the single-strain panels. Base captions (figure_captions.md) regenerate
    on every run. Returns dict with output dir, figure count, strain order, and series."""
    if not _HAVE_MPL:
        _require_mpl()
    os.makedirs(out, exist_ok=True); FIGNUM[0]=0
    S=load(runs_dir, only=strains, public_only=public_only)
    if not S:
        return {"out": out, "figures": 0, "strains": [], "note": "no gold packages found"}
    order=order_strains(S, explicit=strains)
    sel = "all" if str(series).lower() == "all" else str(series).upper()
    want = ["F", "G", "D"] if sel == "all" else [sel]
    if "F" in want:
        (figs_single(S, order[0], out) if len(order)==1 else figs_multi(
            S, order, out, f13_cohort_manifest=f13_cohort_manifest,
            f13_cohort_manifest_sha256=f13_cohort_manifest_sha256,
            f13_denominator_registry=f13_denominator_registry,
            f13_denominator_registry_sha256=f13_denominator_registry_sha256,
            f13_profile=f13_profile,
        ))
    if "G" in want:
        _run_all_g(S, order, out)
    if "D" in want:
        _run_all_d(S, order, out)
    pngs=sorted(glob.glob(f"{out}/*.png"))
    # base captions + glossary, regenerated each run (claim-safe, author-refinable)
    try:
        caption_path = write_captions(out, [os.path.basename(p) for p in pngs])  # defined below (merged from cohort_figure_captions)
        caption_status = "WRITTEN"
        caption_error = None
    except OSError as exc:
        caption_path = None
        caption_status = "ERRORED"
        caption_error = f"{type(exc).__name__}: {exc}"
    return {"out": out, "figures": len(pngs), "strains": order,
            "files": [os.path.basename(p) for p in pngs], "series": sel,
            "caption_status": caption_status, "caption_path": caption_path,
            "caption_error": caption_error}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--runs-dir",default="runs_gold"); ap.add_argument("--out",default="out/figures3")
    ap.add_argument("--strains",default=None); ap.add_argument("--public-only",action="store_true")
    ap.add_argument("--f13-cohort-manifest", default=None,
                    help="Hash-bound F13 cohort-manifest JSON; omit to emit an F13 HOLD receipt")
    ap.add_argument("--f13-cohort-manifest-sha256", default=None,
                    help="Exact SHA-256 for --f13-cohort-manifest")
    ap.add_argument("--f13-denominator-registry", default=None,
                    help="Independent hash-bound registry of permitted F13 denominator scopes")
    ap.add_argument("--f13-denominator-registry-sha256", default=None,
                    help="Exact SHA-256 for --f13-denominator-registry")
    ap.add_argument("--f13-profile", choices=["SINGLE_COLUMN", "DOUBLE_COLUMN"], default="SINGLE_COLUMN",
                    help="Declared physical F13 artwork width profile")
    a=ap.parse_args()
    r=generate(a.runs_dir, a.out, a.strains.split(",") if a.strains else None, a.public_only,
               f13_cohort_manifest=a.f13_cohort_manifest,
               f13_cohort_manifest_sha256=a.f13_cohort_manifest_sha256,
               f13_denominator_registry=a.f13_denominator_registry,
               f13_denominator_registry_sha256=a.f13_denominator_registry_sha256,
               f13_profile=a.f13_profile)
    emit(f"strains ({len(r['strains'])}): {r['strains']}", f"{r['figures']} figures -> {r['out']}", sep="\n")
    for f in r.get("files",[]): emit("  ",f)

if __name__=="__main__": main()


# ===== merged from cohort_figures_d.py (D-series bubble/dot plots) =====
#!/usr/bin/env python3
"""D-series dot / bubble plots — complement to F- and G-series heatmaps.
Bubble matrices (size+colour encode two variables) read sparse chemistry far better than
zero-filled heatmaps; scatters expose the per-BGC architecture landscape.
Usage: python3 make_figures_dots.py --runs-dir runs_gold --out out/figuresD
"""

DNUM=[0]
def stamp_d(fig, fid):
    DNUM[0]+=1; fig.supxlabel(f"D{DNUM[0]:02d} · {fid}",fontsize=6,color="#9a9a9a")  # v9.7.162: below x-tick labels
    return f"D{DNUM[0]:02d}_{fid}"

def place_labels(ax, pts):
    """pts: list of (x,y,text). Singletons get a small offset; clustered points are
    fanned around a circle with thin leader lines so labels never mask each other."""
    xr=ax.get_xlim(); yr=ax.get_ylim()
    tx=abs(xr[1]-xr[0])*0.06; ty=abs(yr[1]-yr[0])*0.06
    used=[False]*len(pts)
    for i in range(len(pts)):
        if used[i]: continue
        grp=[i]; used[i]=True
        for j in range(i+1,len(pts)):
            if not used[j] and abs(pts[i][0]-pts[j][0])<tx and abs(pts[i][1]-pts[j][1])<ty:
                grp.append(j); used[j]=True
        if len(grp)==1:
            x,y,t=pts[i]; ax.annotate(t,(x,y),fontsize=8,fontweight="bold",xytext=(6,5),textcoords="offset points")
        else:
            n=len(grp)
            for k,gi in enumerate(grp):
                x,y,t=pts[gi]; ang=2*math.pi*k/n + math.pi/4
                ax.annotate(t,(x,y),fontsize=8,fontweight="bold",
                            xytext=(26*math.cos(ang),26*math.sin(ang)),textcoords="offset points",
                            ha="center",arrowprops=dict(arrowstyle="-",color="#999",lw=0.6))

def soft_div_x(ax, order, y):
    npriv=sum(1 for s in order if is_private(s)); ndiv=len(order)-npriv
    # v9.7.222: PUBLIC/PRIVATE divider removed — AS cohort public at publication.

def _load_inv_d(S, order):
    inv={}
    for s in order:
        f=glob.glob(f"{S[s]['pkg']}/*_2_inventory.csv"); inv[s]=list(csv.DictReader(open(f[0], encoding="utf-8"))) if f else []
    return inv

def bubble_matrix(rows, order, count_fn, color_fn, title, fid, OUT, clab, slab, cmap="viridis", color_is_count=False):
    """rows: list of row keys; count_fn(row,s)->size count; color_fn(row,s)->color value or None."""
    nx,ny=len(order),len(rows)
    if nx==0 or ny==0:
        # Degenerate input (no strains or no populated rows — e.g., a single-BGC strain): counts.max()
        # on the empty array raised "zero-size array to reduction operation maximum" and skipped the
        # whole gold suite. Render a labelled empty-state panel instead of crashing. (v9.7.267 Path-3 guard.)
        fig,ax=plt.subplots(figsize=(6.0,2.2),constrained_layout=True)
        ax.text(0.5,0.5,f"{title}\n(no data for this view)",ha="center",va="center",fontsize=10,color="#666")
        ax.axis("off")
        # v9.7.268: bubble_matrix is a D-series figure; the empty-state placeholder must be stamped
        # D, not G. The original copied hmap's stamp_g here, mis-filing the placeholder into the
        # G (heatmap) family. stamp_d keeps the placeholder in the same series as the real figure.
        fname=stamp_d(fig,fid); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
        return
    fig,ax=plt.subplots(figsize=(max(8,1.5*nx+3),max(3.5,0.5*ny+2.5)),constrained_layout=True)
    counts=np.array([[count_fn(r,s) for s in order] for r in rows],float)
    cmax=(counts.max() if counts.size else 0) or 1; smax=900.0
    xs,ys,ss,cs=[],[],[],[]
    for i,r in enumerate(rows):
        for j,s in enumerate(order):
            c=counts[i,j]
            if c<=0: continue
            xs.append(j); ys.append(i); ss.append(40+ (c/cmax)*smax)
            cs.append(c if color_is_count else (color_fn(r,s) if color_fn(r,s) is not None else np.nan))
    sc=ax.scatter(xs,ys,s=ss,c=cs,cmap=cmap,edgecolor="#333",linewidth=0.5,alpha=0.9)
    ax.set_xticks(range(nx)); ax.set_xticklabels([lab(s) for s in order],fontsize=8)
    ax.set_yticks(range(ny)); ax.set_yticklabels(rows,fontsize=8.5); ax.tick_params(length=0)
    ax.set_xlim(-0.6,nx-0.4); ax.set_ylim(ny-0.4,-0.8); ax.grid(alpha=0.15)
    soft_div_x(ax,order,-0.65)
    cb=fig.colorbar(sc,ax=ax,fraction=0.024,pad=0.012); cb.set_label(clab,fontsize=9)
    # size legend
    for cv in sorted({int(cmax),max(1,int(cmax/2)),1}):
        ax.scatter([],[],s=40+(cv/cmax)*smax,c="#bbb",edgecolor="#333",label=f"{cv}")
    ax.legend(title=slab,fontsize=7,title_fontsize=7.5,bbox_to_anchor=(1.16,1.0),loc="upper left",borderaxespad=0,labelspacing=1.4,frameon=False)
    ax.set_title(title,pad=22)
    fname=stamp_d(fig,fid); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["row"]+list(order),[[rows[i]]+list(counts[i]) for i in range(ny)])

def build(S, order, OUT):
    inv=_load_inv_d(S,order)
    # per-BGC product class + length + kcb + node, keyed (s,bgc)
    L={}; KCB={}; PRODS={}
    for s in order:
        for r in inv[s]:
            bid=r.get("BGC_ID")
            L[(s,bid)]=_num(r.get("Length_kb"))
            v=r.get("KCB_score"); KCB[(s,bid)]=float(v) if v not in (None,"","NA","nan") and r.get("KCB_top") else None
            PRODS[(s,bid)]=[t.strip() for t in (r.get("Products") or "").replace(";",",").split(",") if t.strip()]

    # D01 bubble matrix: product class x strain (size=BGC count, colour=mean BGC length kb)
    pc=collections.Counter()
    by=collections.defaultdict(lambda: collections.defaultdict(list))
    for s in order:
        for r in inv[s]:
            for t in PRODS[(s,r.get("BGC_ID"))]:
                by[t][s].append(L[(s,r.get("BGC_ID"))]); pc[t]+=1
    classes=[c for c,_ in pc.most_common(16)]
    bubble_matrix(classes, order,
        lambda r,s: len(by[r].get(s,[])),
        lambda r,s: (np.mean(by[r][s]) if by[r].get(s) else None),
        "Product class \u00d7 strain — dot size = BGC count, colour = mean BGC length (kb)",
        "bubble_productclass_size_length", OUT, "mean length (kb)", "BGC count", cmap="plasma")

    # D02 rare-trigger bubble (sparse-friendly): trigger x strain, size=count, colour=count
    COMMON={"T43-HAL_halogenase","T43-LAN_lanthipeptide"}
    tr=collections.defaultdict(lambda: collections.defaultdict(int)); tot=collections.Counter()
    for s in order:
        for b in S[s]["deep"]["bgc_profile"]:
            for t in (b.get("cctt_triggers") or "").split(","):
                t=t.strip()
                if t and t not in COMMON: tr[t][s]+=1; tot[t]+=1
    trows=sorted(tr,key=lambda k:tot[k])
    bubble_matrix([t.replace("T43-","") for t in trows], order,
        lambda r,s: tr["T43-"+r if "T43-"+r in tr else r].get(s,0) if ("T43-"+r in tr or r in tr) else 0,
        None,
        "Rare diagnostic-chemistry triggers \u00d7 strain (dot size = BGC count) — sparse-friendly view",
        "bubble_rare_triggers", OUT, "BGC count", "BGC count", cmap="rocket_r" if "rocket_r" in plt.colormaps() else "magma_r", color_is_count=True)

    # D03 per-BGC scatter: size (kb) vs domain count, colour by strain, diamonds=private
    fig,ax=plt.subplots(figsize=(9.6,6.6))
    pal=plt.cm.tab20(np.linspace(0,1,max(3,len(order))))
    for gi,s in enumerate(order):
        xs=[]; ys=[]
        prof={b["bgc_id"]:b for b in S[s]["deep"]["bgc_profile"]}
        for r in inv[s]:
            bid=r.get("BGC_ID"); b=prof.get(bid)
            if not b: continue
            xs.append(L[(s,bid)]); ys.append(int(b.get("total_domains") or 0))
        priv=is_private(s)
        ax.scatter(xs,ys,s=70 if priv else 26,marker="D" if priv else "o",color=pal[gi],alpha=0.75,
                   edgecolor="#222",linewidth=0.8 if priv else 0.3,label=f"{genus(s).split()[0]} {s}"+(" (PRIV)" if priv else ""))
    ax.set_xlabel("BGC region length (kb)"); ax.set_ylabel("domains per BGC")
    ax.set_title("Per-BGC architecture landscape — size vs domain richness",pad=12); ax.grid(alpha=0.2)
    ax.legend(fontsize=7,bbox_to_anchor=(1.02,1.0),loc="upper left",borderaxespad=0)
    fn=stamp_d(fig,"scatter_size_vs_domains"); _save_pair(fig,f"{OUT}/{fn}.png"); plt.close(fig)

    # D04 KCB strength vs BGC size, colour by boundary (truncation effect on KCB)
    binv={}
    for s in order:
        for r in inv[s]: binv[(s,r.get("BGC_ID"))]=r.get("Boundary")
    bcol={"Interior":"#1b7837","Edge":"#e08214","Full-contig":"#b2182b"}
    fig,ax=plt.subplots(figsize=(9.2,6.4))
    _pos_kcb=False
    for bnd,col in bcol.items():
        xs=[]; ys=[]
        for s in order:
            for r in inv[s]:
                bid=r.get("BGC_ID")
                if binv.get((s,bid))==bnd and KCB.get((s,bid)):
                    xs.append(L[(s,bid)]); ys.append(KCB[(s,bid)])
        if any(v>0 for v in ys): _pos_kcb=True
        ax.scatter(xs,ys,s=24,color=col,alpha=0.65,edgecolor="#222",linewidth=0.3,label=bnd)
    # a cohort with no KnownClusterBlast hits has no positive y -> log scale would crash; stay linear
    if _pos_kcb:
        ax.set_yscale("log")
    else:
        ax.text(0.5,0.5,"no KCB reference hits in this cohort\n(all BGCs novelty-leaning; linear axis)",
                transform=ax.transAxes,ha="center",va="center",fontsize=10,color="#777")
    ax.set_xlabel("BGC region length (kb)"); ax.set_ylabel("KCB rank-1 cumulative BLAST score\n(log; unnormalised sum, scales with cluster size; similarity, not identity)")
    ax.set_title("KCB reference-similarity vs BGC size, by boundary status\n(truncated Edge/Full-contig BGCs trend to weaker / absent hits)",pad=12); ax.grid(alpha=0.2,which="both")
    ax.legend(fontsize=8,title="boundary",title_fontsize=8)
    fn=stamp_d(fig,"scatter_kcb_vs_size"); _save_pair(fig,f"{OUT}/{fn}.png"); plt.close(fig)

    # D05 strain summary: raw vs corrected BGC count, size=domain hits, colour=tier, labelled
    fig,ax=plt.subplots(figsize=(10.5,7.0))
    pts=[]
    for s in order:
        ms=S[s]["ms"]; raw=int(read_manifest_field("raw_bgcs", manifest_short=ms, default=0)); cor=float(read_manifest_field("corrected_bgcs", manifest_short=ms, default=0)); dh=len(S[s]["deep"].get("domain_hits",[]))
        priv=is_private(s); tier=read_manifest_field("assembly_tier", manifest_short=ms, default="UNKNOWN")
        ax.scatter(raw,cor,s=60+dh/12,marker="D" if priv else "o",color=TCOLOR.get(tier,"#999"),
                   edgecolor="#111",linewidth=1.2 if priv else 0.7,zorder=3)
        pts.append((raw,cor,s))
    lim=max(int(S[s]["ms"]["raw_bgcs"]) for s in order)+12
    ax.plot([0,lim],[0,lim],ls=":",color="#aaa",lw=1,label="raw = corrected")
    ax.set_xlim(0,lim); ax.set_ylim(0,lim*0.85)
    place_labels(ax,pts)
    ax.set_xlabel("raw BGC count"); ax.set_ylabel("corrected BGC count (Interior + \u00bdEdge + \u00bcFC)")
    ax.set_title("Strain summary — raw vs corrected BGC count (dot size = domain hits)",pad=12); ax.grid(alpha=0.2)
    h=[plt.Line2D([],[],marker="o",color="w",markerfacecolor=TCOLOR[t],markeredgecolor="#111",label=t) for t in ["GOOD","MODERATE","POOR","VERY_POOR"]]
    h.append(plt.Line2D([],[],marker="D",color="w",markerfacecolor="#888",markeredgecolor="#111",label="PRIVATE"))
    ax.legend(handles=h,fontsize=7.5,loc="upper left")
    fn=stamp_d(fig,"scatter_raw_vs_corrected"); _save_pair(fig,f"{OUT}/{fn}.png"); plt.close(fig)

    # D06 KCB strip plot: each BGC a dot, x=strain (jittered), y=log KCB bitscore; no-hit count noted
    fig,ax=plt.subplots(figsize=(max(9,1.3*len(order)+3),6.2))
    rng=np.random.default_rng(7)
    _pos_kcb=False
    for j,s in enumerate(order):
        ys=[KCB[(s,r.get("BGC_ID"))] for r in inv[s] if KCB.get((s,r.get("BGC_ID")))]
        if any(v>0 for v in ys): _pos_kcb=True
        nohit=sum(1 for r in inv[s] if not KCB.get((s,r.get("BGC_ID"))))
        xs=j+rng.uniform(-0.18,0.18,size=len(ys))
        ax.scatter(xs,ys,s=20,marker="D" if is_private(s) else "o",
                   color=TCOLOR.get(S[s]["ms"]["assembly_tier"],"#999"),alpha=0.6,edgecolor="#222",linewidth=0.2)
        ax.text(j,1.5,f"{nohit} no-hit",ha="center",fontsize=6.5,color="#777",rotation=90)
    # no positive KCB score anywhere -> log scale would raise; stay linear and note it
    if _pos_kcb:
        ax.set_yscale("log")
    else:
        ax.text(0.5,0.5,"no KCB reference hits in this cohort\n(all BGCs novelty-leaning; linear axis)",
                transform=ax.transAxes,ha="center",va="center",fontsize=10,color="#777")
    ax.set_xticks(range(len(order))); ax.set_xticklabels([lab(s) for s in order],fontsize=8)
    ax.set_ylabel("KCB rank-1 cumulative BLAST score\n(log; unnormalised sum, scales with cluster size; similarity, not identity)"); ax.tick_params(length=0)
    soft_div_x(ax,order,ax.get_ylim()[1])
    ax.set_title("KCB reference-similarity distribution per strain (one dot = one BGC with a hit;\n'no-hit' count noted = novelty-leaning, incl. truncated BGCs)",pad=12); ax.grid(alpha=0.2,axis="y",which="both")
    fn=stamp_d(fig,"strip_kcb_per_strain"); _save_pair(fig,f"{OUT}/{fn}.png"); plt.close(fig)

    # D07 rare-chemistry richness vs total BGC content (per strain)
    COMMON={"T43-HAL_halogenase","T43-LAN_lanthipeptide"}
    fig,ax=plt.subplots(figsize=(9.4,6.6)); pts=[]
    for s in order:
        rare_tr=set()
        for b in S[s]["deep"]["bgc_profile"]:
            for t in (b.get("cctt_triggers") or "").split(","):
                t=t.strip()
                if t and t not in COMMON: rare_tr.add(t)
        raw=int(S[s]["ms"]["raw_bgcs"]); priv=is_private(s)
        ax.scatter(raw,len(rare_tr),s=90,marker="D" if priv else "o",color=TCOLOR.get(S[s]["ms"]["assembly_tier"],"#999"),
                   edgecolor="#111",linewidth=1.1 if priv else 0.7,zorder=3)
        pts.append((raw,len(rare_tr),s))
    place_labels(ax,pts)
    ax.set_xlabel("raw BGC count"); ax.set_ylabel("# distinct rare chemistry triggers")
    ax.set_title("Rare-chemistry richness vs genome BGC content\n(strains above the trend punch above their weight in rare chemistry)",pad=12); ax.grid(alpha=0.2)
    fn=stamp_d(fig,"scatter_rarechem_vs_bgcs"); _save_pair(fig,f"{OUT}/{fn}.png"); plt.close(fig)

    # D08 tailoring-enzyme bubble matrix (size=count)
    dc=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for h in S[s]["deep"].get("domain_hits",[]):
            p=h.get("pfam") or h.get("domain")
            if p: dc[p][s]+=1
    tail=[("Trp_halogenase","halogenase"),("Glyco_hydro_18","chitinase GH18"),("p450","cytochrome P450"),
          ("Glycos_transf_1","glycosyltransferase"),("Methyltransf_2","methyltransferase"),
          ("Radical_SAM","radical SAM"),("IucA_IucC","siderophore synthetase"),("polyprenyl_synt","prenyltransferase")]
    tail=[(d,l) for d,l in tail if dc.get(d)]
    bubble_matrix([l for _,l in tail], order, lambda r,s: dc[dict((l,d) for d,l in tail)[r]].get(s,0), None,
        "Tailoring enzymes \u00d7 strain (dot size = domain count)","bubble_tailoring",OUT,
        "domain count","domain count",cmap="rocket_r" if "rocket_r" in plt.colormaps() else "magma_r",color_is_count=True)

    # D09 regulator / TF bubble matrix (size=count) — with family descriptions in subtitle
    reg=[("TetR_N","TetR (efflux/antibiotic-responsive repressors)"),("GntR","GntR (metabolic repressors)"),
         ("LysR_substrate","LysR (dual activator/repressor)"),("MarR_2","MarR (multidrug-resistance regulators)"),
         ("Sigma70_r2","sigma-70 (alternative sigma factors)"),("HTH_1","HTH (helix-turn-helix DNA-binding)")]
    reg=[(d,l) for d,l in reg if dc.get(d)]
    bubble_matrix([l for _,l in reg], order, lambda r,s: dc[dict((l,d) for d,l in reg)[r]].get(s,0), None,
        "Transcription-factor / regulator families \u00d7 strain (dot size = domain count)","bubble_regulators",OUT,
        "domain count","domain count",cmap="mako_r" if "mako_r" in plt.colormaps() else "viridis",color_is_count=True)

    # D10 per-BGC scatter coloured by dominant product class
    DOMCLASS=["NRPS","T1PKS","PKS","RiPP","terpene","saccharide","NI-siderophore","other"]
    cpal={c:plt.cm.tab10(i/10) for i,c in enumerate(DOMCLASS)}
    fig,ax=plt.subplots(figsize=(9.8,6.6))
    for c in DOMCLASS:
        xs=[]; ys=[]
        for s in order:
            prof={b["bgc_id"]:b for b in S[s]["deep"]["bgc_profile"]}
            for r in inv[s]:
                bid=r.get("BGC_ID"); pl=PRODS.get((s,bid),[])
                dom=next((d for d in DOMCLASS if d in pl),"other") if pl else "other"
                if dom==c and prof.get(bid):
                    xs.append(L[(s,bid)]); ys.append(int(prof[bid].get("total_domains") or 0))
        ax.scatter(xs,ys,s=22,color=cpal[c],alpha=0.6,edgecolor="#333",linewidth=0.2,label=c)
    ax.set_xlabel("BGC region length (kb)"); ax.set_ylabel("domains per BGC")
    ax.set_title("Per-BGC architecture coloured by dominant product class",pad=12); ax.grid(alpha=0.2)
    ax.legend(fontsize=7.5,bbox_to_anchor=(1.02,1.0),loc="upper left",borderaxespad=0,title="product class")
    fn=stamp_d(fig,"scatter_bgc_by_class"); _save_pair(fig,f"{OUT}/{fn}.png"); plt.close(fig)

    # D11 TTA load vs modularity (per BGC), coloured by strain
    fig,ax=plt.subplots(figsize=(9.6,6.4)); pal=plt.cm.tab20(np.linspace(0,1,max(3,len(order))))
    rng=np.random.default_rng(3)
    for gi,s in enumerate(order):
        xs=[]; ys=[]
        for b in S[s]["deep"]["bgc_profile"]:
            mod=int(b.get("PKS_KS") or 0)+int(b.get("NRPS_C") or 0); tta=int(b.get("tta_codons") or 0)
            xs.append(mod+rng.uniform(-0.2,0.2)); ys.append(tta+rng.uniform(-0.2,0.2))
        priv=is_private(s)
        ax.scatter(xs,ys,s=55 if priv else 20,marker="D" if priv else "o",color=pal[gi],alpha=0.7,
                   edgecolor="#222",linewidth=0.6 if priv else 0.2,label=f"{s}"+(" (PRIV)" if priv else ""))
    ax.set_xlabel("megasynthase modules per BGC (PKS-KS + NRPS-C)"); ax.set_ylabel("TTA codons per BGC (bldA-dependency)")
    ax.set_title("bldA-dependency vs megasynthase modularity, per BGC",pad=12); ax.grid(alpha=0.2)
    ax.legend(fontsize=7,bbox_to_anchor=(1.02,1.0),loc="upper left",borderaxespad=0)
    fn=stamp_d(fig,"scatter_tta_vs_modularity"); _save_pair(fig,f"{OUT}/{fn}.png"); plt.close(fig)


def _run_all_d(S, order, out):
    """Emit all D-series dot/bubble plots into <out>. Returns list of PNG basenames."""
    DNUM[0]=0
    build(S, order, out)
    return sorted(os.path.basename(p) for p in glob.glob(f"{out}/D*.png"))

# ===== merged from cohort_figures_g.py (G-series rarity/novelty) =====
#!/usr/bin/env python3
"""Complementary G-series figures (rarity, novelty, architecture, similarity) — batch-driven.
Reuses data loaders + styling from make_figures2; G-numbered stamp; data-only PNG + sidecar CSV.
Usage: python3 -m mamey.cohort_figures_g --runs-dir runs_gold --out out/figuresG --batch 1
(v9.7.151 bunny-hop 60-file fix: docstring said `make_figures_complement.py` from a pre-bundle
era; the actual file is `mamey/cohort_figures_g.py`.)
"""

GNUM=[0]
def stamp_g(fig, fid):
    GNUM[0]+=1; tag=f"G{GNUM[0]:02d} · {fid}"
    fig.supxlabel(tag,fontsize=6,color="#9a9a9a")  # v9.7.162: below x-tick labels
    return f"G{GNUM[0]:02d}_{fid}"

def soft_div(ax, order):
    npriv=sum(1 for s in order if is_private(s)); ndiv=len(order)-npriv
    # v9.7.222: PUBLIC/PRIVATE divider removed — AS cohort public at publication.

def hmap(mat, rowlabs, order, title, fid, OUT, cbar="count", cmap="magma_r", lognorm=True, annot=True, row_raw=None):
    mat=np.array(mat,float)
    if mat.size == 0:
        # Degenerate input (e.g., a single-BGC strain, or a view with no populated rows/cols):
        # matplotlib's imshow rejects a zero-size array ("Invalid shape (0,)"), which previously
        # propagated out of the entire gold suite and skipped every figure. Render a labelled
        # empty-state panel instead so the suite completes and the gap is visible. (v9.7.267 Path-3 guard.)
        fig,ax=plt.subplots(figsize=(6.0,2.2),constrained_layout=True)
        ax.text(0.5,0.5,f"{title}\n(no data for this view)",ha="center",va="center",fontsize=10,color="#666")
        ax.axis("off")
        fname=stamp_g(fig,fid); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
        return
    fig_w=max(8.0,1.55*len(order)+3.4); fig_h=max(3.2,0.36*len(rowlabs)+2.6)
    fig,ax=plt.subplots(figsize=(fig_w,fig_h),constrained_layout=True)
    if lognorm:
        disp=np.where(mat<=0,np.nan,mat)
        # B-empty (v9.7.212 audit follow-on): same empty/all-NaN guard as heatmap() above.
        _ok = disp.size and not np.all(np.isnan(disp))
        _vmin = max(1,np.nanmin(disp)) if _ok else 1
        _vmax = max(_vmin+1, np.nanmax(disp)) if _ok else 2
        im=ax.imshow(disp,aspect="auto",cmap=cmap,norm=LogNorm(vmin=_vmin,vmax=_vmax))
    else:
        im=ax.imshow(mat,aspect="auto",cmap=cmap)
    ax.set_xticks(range(len(order))); ax.set_xticklabels([lab(s) for s in order],fontsize=8)
    ax.set_yticks(range(len(rowlabs))); ax.set_yticklabels(rowlabs,fontsize=8.5); ax.tick_params(length=0)
    if annot:
        mx=(np.nanmax(mat) if mat.size and not np.all(np.isnan(mat)) else 0) or 1   # empty/all-NaN-safe (audit follow-on)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v=mat[i,j]
                if v==0: ax.text(j,i,"0",ha="center",va="center",fontsize=6.5,color="#ccc"); continue
                t=f"{v:.0f}" if abs(v-round(v))<1e-6 else f"{v:.1f}"
                dark=(lognorm and v>mx*0.10) or (not lognorm and v>mx*0.55)
                ax.text(j,i,t,ha="center",va="center",fontsize=7,color="white" if dark else "#111")
    soft_div(ax,order); ax.set_title(title,pad=24)
    cb=fig.colorbar(im,ax=ax,fraction=0.024,pad=0.012); cb.set_label(cbar,fontsize=9)
    fname=stamp_g(fig,fid); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["row"]+list(order),[[(row_raw or rowlabs)[i]]+list(mat[i]) for i in range(len(rowlabs))])

def _load_inv_g(S, order):
    """per-strain list of inventory rows (Boundary, Length_kb, KCB_top, KCB_score, Products, Node_ID)."""
    inv={}
    for s in order:
        f=glob.glob(f"{S[s]['pkg']}/*_2_inventory.csv")
        if f:
            with open(f[0], encoding='utf-8') as fh:
                inv[s]=list(csv.DictReader(fh))
        else:
            inv[s]=[]
    return inv

# ---------------- BATCH 1: rarity & novelty ----------------
def batch1(S, order, OUT):
    inv=_load_inv_g(S,order)
    # G01 rare-chemistry CCTT triggers (drop the two ubiquitous: HAL, LAN)
    COMMON={"T43-HAL_halogenase","T43-LAN_lanthipeptide"}
    cct=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for b in S[s]["deep"]["bgc_profile"]:
            for t in (b.get("cctt_triggers") or "").split(","):
                t=t.strip()
                if t and t not in COMMON: cct[t][s]+=1
    rk=sorted(cct,key=lambda k:sum(cct[k].values()))  # rarest at top
    hmap([[cct[k].get(s,0) for s in order] for k in rk],[k.replace("T43-","") for k in rk],order,
         "Rare diagnostic-chemistry triggers per strain (DKP, indolocarbazole, lasso, nucleoside…;\nubiquitous halogenase/lanthipeptide removed to spotlight rarity)",
         "rare_chemistry_triggers",OUT,cbar="BGCs w/ trigger",cmap="rocket_r" if "rocket_r" in plt.colormaps() else "magma_r",row_raw=rk)

    # G02 rare product classes (present in <= 4 strains)
    pc=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for row in inv[s]:
            for t in (row.get("Products") or "").replace(";",",").split(","):
                t=t.strip()
                if t: pc[t][s]+=1
    present={k:sum(1 for s in order if pc[k].get(s,0)>0) for k in pc}
    rare=[k for k in pc if present[k]<=4 and present[k]>=1]
    rare=sorted(rare,key=lambda k:(present[k],-sum(pc[k].values())))
    hmap([[pc[k].get(s,0) for s in order] for k in rare],[f"{k}  (in {present[k]})" for k in rare],order,
         "Rare product classes (present in \u22644 of %d strains) — BGC counts" % len(order),
         "rare_product_classes",OUT,cbar="BGC count",cmap="viridis",row_raw=rare)

    # G03 KCB reference-similarity strength (similarity, not identity)
    scores=[]
    for s in order:
        for row in inv[s]:
            v=row.get("KCB_score")
            if v not in (None,"","NA","nan"):
                scores.append(_num(v))
    # v9.7.404 (B1 ruling): these cut points are COHORT TERTILES computed from this cohort's own
    # available scores (33rd/66th percentile of `scores` above) -- they are NOT similarity
    # thresholds, and they carry no biological meaning. Re-run the same figure on a different
    # cohort and the same BGC can move bin without any change to its evidence. The bin labels say
    # so on the figure itself, because a reader who sees "high" next to a number will otherwise
    # read it as a threshold. See docs/KCB_SCORE_PROVENANCE.md for what the number actually is.
    q1,q2=(np.percentile(scores,[33,66]) if scores else (0,0))
    bins=["no KCB hit (novel-leaning)",
          f"lower cohort third (<{q1:.0f})",
          f"middle cohort third ({q1:.0f}\u2013{q2:.0f})",
          f"upper cohort third (\u2265{q2:.0f})"]
    kc=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for row in inv[s]:
            v=row.get("KCB_score"); top=row.get("KCB_top")
            if not top or v in (None,"","NA","nan"):
                kc[bins[0]][s]+=1; continue
            f=float(v); kc[bins[1] if f<q1 else bins[2] if f<q2 else bins[3]][s]+=1
    hmap([[kc[b].get(s,0) for s in order] for b in bins],bins,order,
         "KCB cumulative-BLAST-score band per strain (BGC counts; KCB = similarity, not identity)\n"
         "Bands are COHORT TERTILES of this cohort's own scores, not similarity thresholds. The score is\n"
         "antiSMASH's unnormalised 'Cumulative BLAST score', which grows with cluster size and protein count,\n"
         "so it is not comparable between BGCs of different size. 'No hit' is novelty-leaning, not proof of novelty.",
         "kcb_similarity_strength",OUT,cbar="BGC count",cmap="cividis",row_raw=bins)

    # G04 BGC boundary status (corrected-count components)
    bnd=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for row in inv[s]: bnd[row.get("Boundary") or "?"][s]+=1
    bk=["Interior","Edge","Full-contig"]; bk=[b for b in bk if b in bnd]+[b for b in bnd if b not in bk]
    hmap([[bnd[b].get(s,0) for s in order] for b in bk],bk,order,
         "BGC boundary status per strain (corrected count = Interior + \u00bd\u00b7Edge + \u00bc\u00b7Full-contig)",
         "bgc_boundary_status",OUT,cbar="BGC count",cmap="magma_r",row_raw=bk)

BATCHES={1:batch1}

# ---------------- BATCH 2: architecture & regulation ----------------
def batch2(S, order, OUT):
    inv=_load_inv_g(S,order)
    def bin_heat(per_strain_vals, edges, labels, title, fid, cbar, cmap="magma_r"):
        # per_strain_vals: dict s-> list of numeric values (one per BGC)
        rows=[[0]*len(order) for _ in labels]
        for j,s in enumerate(order):
            for v in per_strain_vals[s]:
                bi=len(edges)
                for i,e in enumerate(edges):
                    if v<e: bi=i; break
                rows[bi][j]+=1
        hmap(rows,labels,order,title,fid,OUT,cbar=cbar,cmap=cmap,row_raw=labels)

    # G05 BGC size distribution (Length_kb)
    sz={s:[float(r["Length_kb"]) for r in inv[s] if r.get("Length_kb")] for s in order}
    bin_heat(sz,[5,15,30,50],["< 5 kb","5\u201315 kb","15\u201330 kb","30\u201350 kb","\u2265 50 kb"],
             "BGC size distribution per strain (region length, kb)","bgc_size_distribution","BGC count",cmap="viridis")

    # G06 domain richness (total_domains per BGC)
    dr={s:[int(b.get("total_domains") or 0) for b in S[s]["deep"]["bgc_profile"]] for s in order}
    bin_heat(dr,[6,16,31,51],["0\u20135","6\u201315","16\u201330","31\u201350","\u2265 51"],
             "Per-BGC domain richness per strain (total domains/BGC)","domain_richness","BGC count",cmap="mako_r" if "mako_r" in plt.colormaps() else "viridis")

    # G07 TTA / bldA-dependency (tta_codons per BGC)
    tt={s:[int(b.get("tta_codons") or 0) for b in S[s]["deep"]["bgc_profile"]] for s in order}
    bin_heat(tt,[1,2,4,8],["0 (TTA-free)","1","2\u20133","4\u20137","\u2265 8"],
             "TTA-codon load per BGC per strain (bldA-dependent regulation signal)","tta_bldA_dependency","BGC count",cmap="rocket_r" if "rocket_r" in plt.colormaps() else "magma_r")

    # G08 megasynthase modularity (modules ~ PKS_KS + NRPS_C per BGC)
    md={s:[int(b.get("PKS_KS") or 0)+int(b.get("NRPS_C") or 0) for b in S[s]["deep"]["bgc_profile"]] for s in order}
    bin_heat(md,[1,3,6,11],["0 (non-modular)","1\u20132","3\u20135","6\u201310","\u2265 11"],
             "Megasynthase modularity per strain (PKS-KS + NRPS-C modules per BGC)","megasynthase_modularity","BGC count",cmap="cividis")

BATCHES={1:batch1,2:batch2}

# ---------------- BATCH 3: similarity & co-occurrence ----------------
def _strain_profiles(S, order):
    # P12-residual (G09): Oxidoreductase/Aminotransferase/Transporter/Regulator are separate genes,
    # never aSDomain architecture tokens -> always-zero dims. Same fix as figs_multi (.202); this second
    # copy in _strain_profiles was missed then. Restrict to tokens domain_arch can carry.
    vocab=["PKS_KS","PKS_AT","PKS_KR","PKS_DH","PKS_ER","PKS_ACP","NRPS_C","NRPS_A","NRPS_T_PCP",
           "TE_release"]
    prof={}
    for s in order:
        acc=np.zeros(len(vocab))
        for da in S[s]["gene"].get("domain_arch",[]):
            a=_domain_counts_from_architecture(da)
            acc+=np.array([a.get(k,0) for k in vocab],float)
        prof[s]=np.log1p(acc)
    return prof

def batch3(S, order, OUT):
    inv=_load_inv_g(S,order)
    # G09 strain x strain similarity matrix (correlation on z-scored relative domain composition;
    # raw-cosine saturates because housekeeping domains dominate, so we use relative composition)
    dc=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for h in S[s]["deep"].get("domain_hits",[]):
            p=h.get("pfam") or h.get("domain")
            if p: dc[p][s]+=1
    tot_d={p:sum(dc[p].values()) for p in dc}
    top=[p for p in sorted(tot_d,key=lambda p:-tot_d[p])][:40]
    Mc=np.array([[dc[p].get(s,0) for p in top] for s in order],float)
    Mc=Mc/(Mc.sum(1,keepdims=True)+1e-9)          # relative composition per strain
    with np.errstate(invalid="ignore", divide="ignore"):
        sim=np.corrcoef(Mc)                        # Pearson across strains -> discriminative
    sim=np.nan_to_num(sim, nan=0.0)               # zero-variance rows -> 0 correlation, not NaN
    npriv=sum(1 for s in order if is_private(s)); ndiv=len(order)-npriv
    fig,ax=plt.subplots(figsize=(max(8,1.0*len(order)+4),max(6,0.8*len(order)+3)),constrained_layout=True)
    off=sim[~np.eye(len(order),dtype=bool)]
    im=ax.imshow(sim,aspect="auto",cmap="YlGnBu",vmin=off.min(),vmax=1)
    ax.set_xticks(range(len(order))); ax.set_xticklabels([s for s in order],rotation=90,fontsize=8)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([lab(s).replace("\n"," ") for s in order],fontsize=7.5); ax.tick_params(length=0)
    for i in range(len(order)):
        for j in range(len(order)):
            ax.text(j,i,f"{sim[i,j]:.2f}",ha="center",va="center",fontsize=6.5,color="white" if sim[i,j]>(off.min()+1)/2 else "#111")
    if npriv:
        ax.axvline(ndiv-0.5,color="#9a9a9a",lw=1.1,ls=(0,(4,3))); ax.axhline(ndiv-0.5,color="#9a9a9a",lw=1.1,ls=(0,(4,3)))
    ax.set_title("Strain \u00d7 strain similarity (Pearson on relative top-40 domain composition)",pad=14)
    cb=fig.colorbar(im,ax=ax,fraction=0.04,pad=0.02); cb.set_label("correlation",fontsize=9)
    fname=stamp_g(fig,"strain_similarity_matrix"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["strain"]+order,[[order[i]]+[round(x,4) for x in sim[i]] for i in range(len(order))])

    # G10 product-class co-occurrence across strains (class x class; # strains sharing both)
    pcs={}
    for s in order:
        cs=set()
        for r in inv[s]:
            for t in (r.get("Products") or "").replace(";",",").split(","):
                t=t.strip()
                if t: cs.add(t)
        pcs[s]=cs
    allc=collections.Counter()
    for s in order:
        for c in pcs[s]: allc[c]+=1
    classes=[c for c,_ in allc.most_common(18)]
    co=np.zeros((len(classes),len(classes)))
    for a_i,ca in enumerate(classes):
        for b_i,cb in enumerate(classes):
            co[a_i,b_i]=sum(1 for s in order if ca in pcs[s] and cb in pcs[s])
    fig,ax=plt.subplots(figsize=(max(9,0.6*len(classes)+3),max(7,0.5*len(classes)+3)),constrained_layout=True)
    im=ax.imshow(co,aspect="auto",cmap="magma_r")
    ax.set_xticks(range(len(classes))); ax.set_xticklabels(classes,rotation=90,fontsize=7.5)
    ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes,fontsize=7.5); ax.tick_params(length=0)
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j,i,f"{int(co[i,j])}",ha="center",va="center",fontsize=6.5,color="white" if co[i,j]>co.max()*0.55 else "#111")
    ax.set_title("Product-class co-occurrence across strains (cell = # strains carrying both)",pad=14)
    cb=fig.colorbar(im,ax=ax,fraction=0.04,pad=0.02); cb.set_label("# strains with both",fontsize=9)
    fname=stamp_g(fig,"product_class_cooccurrence"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["class"]+classes,[[classes[i]]+[int(x) for x in co[i]] for i in range(len(classes))])

    # G11 RiPP subclass detail per strain
    RIPP_KEYS=["RiPP","RiPP-like","RRE-containing","lanthipeptide-class-i","lanthipeptide-class-ii",
               "lanthipeptide-class-iii","lanthipeptide-class-iv","lassopeptide","lanthipeptide",
               "thiopeptide","sactipeptide","LAP","linaridin","lipolanthine","redox-cofactor","ranthipeptide"]
    rp=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for r in inv[s]:
            for t in (r.get("Products") or "").replace(";",",").split(","):
                t=t.strip()
                if t in RIPP_KEYS: rp[t][s]+=1
    rk=[k for k in RIPP_KEYS if k in rp]
    if rk:
        hmap([[rp[k].get(s,0) for s in order] for k in rk],rk,order,
             "RiPP subclass detail per strain (antiSMASH RiPP product classes, BGC counts)",
             "ripp_subclass_detail",OUT,cbar="BGC count",cmap="viridis",row_raw=rk)

    # G12 product-class x resistance-tier (cohort-wide; which chemistries carry self-resistance)
    rtier={}
    for s in order:
        for b in S[s]["deep"]["bgc_profile"]: rtier[(s,b["bgc_id"])]=b.get("resistance_tier")
    tiers=["T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED","T2_RESISTANCE_LIKE_SOURCE_DERIVED",
           "T3_TRANSPORTER_ONLY_ROUTING","NULL_NO_SOURCE_DERIVED_RESISTANCE"]
    cls_set=collections.Counter()
    pcl_rt=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for r in inv[s]:
            rt=rtier.get((s,r.get("BGC_ID")))
            if not rt: continue
            for t in (r.get("Products") or "").replace(";",",").split(","):
                t=t.strip()
                if t: pcl_rt[t][rt]+=1; cls_set[t]+=1
    classes2=[c for c,_ in cls_set.most_common(18)]
    M=np.array([[pcl_rt[c].get(t,0) for t in tiers] for c in classes2],float)
    fig,ax=plt.subplots(figsize=(8.5,max(6,0.45*len(classes2)+2.5)),constrained_layout=True)
    _M_ok = M.size and not np.all(np.isnan(np.where(M<=0,np.nan,M)))
    im=ax.imshow(np.where(M<=0,np.nan,M),aspect="auto",cmap="magma_r",norm=LogNorm(vmin=1,vmax=(max(2,np.nanmax(M)) if _M_ok else 2)))   # empty-class-matrix-safe (audit follow-on)
    ax.set_xticks(range(len(tiers))); ax.set_xticklabels([t.replace("_SOURCE_DERIVED","").replace("_NO_SOURCE_DERIVED_RESISTANCE","")[:22] for t in tiers],rotation=30,ha="right",fontsize=8)
    ax.set_yticks(range(len(classes2))); ax.set_yticklabels(classes2,fontsize=8); ax.tick_params(length=0)
    for i in range(len(classes2)):
        for j in range(len(tiers)):
            if M[i,j]>0: ax.text(j,i,f"{int(M[i,j])}",ha="center",va="center",fontsize=7,color="white" if M[i,j]>np.nanmax(M)*0.12 else "#111")
    ax.set_title("Product class \u00d7 resistance-axis tier (cohort-wide BGC counts)",pad=14)
    cb=fig.colorbar(im,ax=ax,fraction=0.04,pad=0.02); cb.set_label("BGC count",fontsize=9)
    fname=stamp_g(fig,"productclass_x_resistance"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",["product_class"]+tiers,[[classes2[i]]+[int(x) for x in M[i]] for i in range(len(classes2))])

BATCHES={1:batch1,2:batch2,3:batch3}

# ---------------- BATCH 4: specialized chemistry + rare-BGC roster ----------------
def _short_node(s):
    if not s: return "?"
    parts=str(s).split("_")
    return "_".join(parts[:2]) if len(parts)>=2 else str(s)

def batch4(S, order, OUT):
    inv=_load_inv_g(S,order)
    dc=collections.defaultdict(lambda: collections.defaultdict(int))
    for s in order:
        for h in S[s]["deep"].get("domain_hits",[]):
            p=h.get("pfam") or h.get("domain")
            if p: dc[p][s]+=1

    # G13 redox / oxidoreductase tailoring
    redox=[("p450","cytochrome P450"),("FAD_binding_3","FAD-binding oxidoreductase"),
           ("NAD_binding_4","NAD(P)-binding"),("adh_short","short-chain dehydrogenase"),
           ("ADH_zinc_N","Zn-dependent ADH"),("Pyr_redox_2","pyridine-nucleotide redox"),
           ("Flavin_Reduct","flavin reductase"),("Oxidored_molyb","molybdopterin oxidoreductase")]
    rr=[(d,l) for d,l in redox if dc.get(d)]
    hmap([[dc[d].get(s,0) for s in order] for d,_ in rr],[l for _,l in rr],order,
         "Redox / oxidoreductase tailoring enzymes per strain (domain counts)",
         "redox_tailoring",OUT,cbar="domain count",cmap="mako_r" if "mako_r" in plt.colormaps() else "viridis",row_raw=[d for d,_ in rr])

    # G14 rare / distinctive tailoring enzymes
    rare=[("Radical_SAM","radical SAM"),("polyprenyl_synt","prenyltransferase"),
          ("Glycos_transf_1","glycosyltransferase GT1"),("Glycos_transf_2","glycosyltransferase GT2"),
          ("Methyltransf_2","O/N-methyltransferase (MTf2)"),("Methyltransf_11","methyltransferase (MTf11)"),
          ("Aminotran_3","aminotransferase III"),("Aminotran_5","aminotransferase V"),
          ("Acetyltransf_1","acetyltransferase"),("Epimerase","epimerase/dehydratase")]
    rt=[(d,l) for d,l in rare if dc.get(d)]
    hmap([[dc[d].get(s,0) for s in order] for d,_ in rt],[l for _,l in rt],order,
         "Distinctive tailoring enzymes per strain (domain counts)",
         "distinctive_tailoring",OUT,cbar="domain count",cmap="rocket_r" if "rocket_r" in plt.colormaps() else "magma_r",row_raw=[d for d,_ in rt])

    # G15 rare-BGC roster (BGCs carrying a rare CCTT trigger) WITH node/contig
    COMMON={"T43-HAL_halogenase","T43-LAN_lanthipeptide"}
    prod={}; node={}
    for s in order:
        for r in inv[s]:
            prod[(s,r.get("BGC_ID"))]=(r.get("Products") or "").strip()
            node[(s,r.get("BGC_ID"))]=_short_node(r.get("Node_ID") or r.get("Contig"))
    rows=[]
    for s in order:
        for b in S[s]["deep"]["bgc_profile"]:
            rare_tr=[t.strip().replace("T43-","") for t in (b.get("cctt_triggers") or "").split(",")
                     if t.strip() and t.strip() not in COMMON]
            if rare_tr:
                rows.append([s, b["bgc_id"], node.get((s,b["bgc_id"]),"?"),
                             ", ".join(rare_tr)[:46], (prod.get((s,b["bgc_id"]),"") or "")[:34]])
    rows.sort(key=lambda r:(is_private(r[0]), order.index(r[0]) if r[0] in order else 99, r[1]))
    n=len(rows); fig_h=max(4, 0.30*n+1.6)
    fig,ax=plt.subplots(figsize=(13,fig_h),constrained_layout=True); ax.axis("off")
    cols=["strain","BGC","node/contig","rare trigger(s)","product class"]
    tab=ax.table(cellText=rows,colLabels=cols,cellLoc="left",loc="center",
                 colWidths=[0.11,0.07,0.13,0.40,0.29])
    tab.auto_set_font_size(False); tab.set_fontsize(7.5); tab.scale(1,1.25)
    for (ri,ci),cell in tab.get_celld().items():
        cell.set_edgecolor("#ddd")
        if ri==0:
            cell.set_facecolor("#2a3d66")
            cell.set_text_props(color="white",fontweight="bold")
        elif rows and ri-1<len(rows) and is_private(rows[ri-1][0]):
            cell.set_facecolor("#fdeaea")
    ax.set_title(f"Rare-BGC roster — {n} BGCs carrying a rare diagnostic trigger (node/contig listed; "
                 f"PRIVATE rows shaded)",pad=12,fontsize=12,fontweight="bold")
    fname=stamp_g(fig,"rare_bgc_roster"); _save_pair(fig,f"{OUT}/{fname}.png"); plt.close(fig)
    sidecar(f"{OUT}/{fname}_data.csv",cols,rows)

BATCHES={1:batch1,2:batch2,3:batch3,4:batch4}


def _run_all_g(S, order, out):
    """Emit all G-series figures (batches 1-4) into <out>. Returns list of PNG basenames.

    v9.7.252 (P8): batches 3-4 (strain similarity matrix, product-class co-occurrence) index a
    correlation matrix with `~np.eye(...)`, which fails when the matrix is a scalar (1x1). They need
    >=2 strains and are skipped for single-strain runs. Batches 1-2 are per-strain and always run."""
    GNUM[0]=0
    for b in (1,2): BATCHES[b](S, order, out)
    if len(order) >= 2:
        for b in (3,4): BATCHES[b](S, order, out)
    return sorted(os.path.basename(p) for p in glob.glob(f"{out}/G*.png"))

# ===== merged from cohort_figure_captions.py (captions) =====


CAPTIONS = {
    # ---- F-series (cross-strain heatmaps) ----
    "census_zscore_heatmap": "Per-strain gene/domain census. Cells are raw counts; colour is the z-score of each metric across strains. The top strip encodes assembly tier.",
    "megasynthase_heatmap": "Counts of core PKS/NRPS catalytic domains across all BGCs per strain (ketosynthase, acyltransferase, ketoreductase, condensation, adenylation, thioesterase, etc.) — the assembly-line machinery underlying polyketide and non-ribosomal peptide capacity.",
    "product_class_heatmap": "antiSMASH region product classes per strain (BGC counts). The bottom row is a computed reduced-PKS (macrolide-type) proxy — BGCs carrying the reductive PKS loop — and is not an antiSMASH class (marked *).",
    "tailoring_enzyme_heatmap": "Tailoring / accessory enzyme domain counts per strain: halogenases (introduce Cl/Br), chitinase (GH18), siderophore synthetase/reductase (iron acquisition), P450s and methyl-/glycosyltransferases (oxidation and decoration of scaffolds).",
    "cctt_trigger_heatmap": "CCTT diagnostic-chemistry triggers per strain (BGC counts). Each trigger flags biosynthetic capacity consistent with a chemistry (halogenation, lanthipeptide, thioamide, phosphonate, tetronate, nucleoside, etc.).",
    "resistance_tier_heatmap": "Source-derived resistance-axis tier distribution per strain (BGC counts). Tiers run from T1 (diagnostic self-protection) to NULL (none detected); a self-resistance signal, not a phenotype.",
    "adomain_substrate_heatmap": "NRPS adenylation-domain substrate consensus per strain (antiSMASH-inferred amino-acid specificity). Inferred predictions, similarity-level evidence.",
    "AT_extender_heatmap": "PKS acyltransferase extender-unit consensus per strain (antiSMASH-inferred: malonyl, methylmalonyl, etc.), reflecting polyketide building-block selection.",
    "transporter_family_heatmap": "Transporter family domain counts per strain: ABC transporters (ATP-driven export, often product self-resistance), MFS (proton-motive efflux) and permeases.",
    "regulator_TF_heatmap": (
        "Counts of selected raw domain tokens from upstream antiSMASH GBK aSDomain/PFAM_domain "
        "annotations, not experimentally defined regulator genes or validated functions. Displayed raw "
        "tokens are TetR_N, GntR, LysR_substrate, HTH_1, Sigma70_r2, Sigma70_r4_2, HTH_31, "
        "HTH_18, MarR_2, HTH_30, and AraC_binding. The observation unit is one retained "
        "deep_data.domain_hits occurrence assigned to a BGC overlap; each matching occurrence "
        "increments one strain cell. Upstream extract_domain_features prefers whole-record GBKs, "
        "excludes region-file copies when whole-record GBKs exist, and deduplicates identical feature "
        "keys (contig, coordinates, strand, feature type, token, locus). Repeated occurrences at "
        "different loci are retained, and one source feature can be represented more than once when "
        "it overlaps multiple BGC intervals. Sapote-Mamey selects the displayed token list and any "
        "human-readable glossary labels but does not independently call or validate regulator identity "
        "or regulatory role. In particular, LysR_substrate denotes a substrate-binding-domain token; "
        "by itself it does not establish a complete LysR regulator or regulatory function."
    ),
    "domain_clustermap_top40": "REDESIGN / NOT PUBLICATION-READY. Legacy deep_data.domain_hits mixes retained annotation-token source classes and lacks the feature-type/accession provenance needed for a truthful Pfam-only view; no figure is emitted until the source-class-filter contract is satisfied.",
    "active_site_completeness": "Fraction of catalytic active-site residues confirmed present per strain (catalytic megasynthase genes; n per strain above each bar). A proxy for how intact the catalytic machinery is.",
    "bgc_domain_pca_2d": "PCA of every BGC in domain-composition space; each point is one BGC, coloured by strain (PRIVATE strains drawn as diamonds). Proximity = similar domain architecture.",
    "bgc_pca_by_cluster": "The same BGC PCA recoloured by architecture cluster (greedy cosine >= 0.85; top clusters), highlighting recurrent assembly-line architectures shared across strains.",
    "strain_ordination_2d": "Strains ordinated by their mean BGC domain profile; colour = assembly tier, diamonds = PRIVATE. Separation reflects overall biosynthetic-repertoire differences.",
    # F single-strain panels
    "perBGC_domain_heatmap": "Single strain: per-BGC catalytic-domain composition (top BGCs by domain content), giving the within-genome biosynthetic landscape.",
    "perGene_active_site_completeness": "Single strain: active-site residue completeness for each catalytic megasynthase gene, ranked.",
    "perBGC_cctt_resistance": "Single strain: per-BGC CCTT diagnostic-chemistry triggers (green presence) with a resistance-tier colour strip, locating rare chemistry on specific BGCs.",

    # ---- G-series (complementary) ----
    "rare_chemistry_triggers": "Rare diagnostic-chemistry triggers per strain with the two ubiquitous triggers (halogenase, lanthipeptide) removed, so uncommon capacity (diketopiperazine/CDPS, indolocarbazole, lassopeptide, nucleoside, n-n-bond) stands out.",
    "rare_product_classes": "Product classes present in at most four strains (BGC counts) — isolates the unusual chemistry (metallophores, nucleosides, NAPAA, RRE-containing/lanthipeptide RiPP subtypes, indole) from the common backbone classes.",
    "kcb_similarity_strength": "Per-strain distribution of BGCs by KnownClusterBlast reference-similarity strength, including a 'no-hit' (novelty-leaning) bin. KCB is similarity, not identity; the no-hit bin partly conflates true novelty with truncation of fragmented BGCs.",
    "bgc_boundary_status": "BGC boundary status per strain (Interior / Edge / Full-contig) — the components of the corrected BGC count (Interior + 1/2*Edge + 1/4*Full-contig), making assembly fragmentation explicit.",
    "bgc_size_distribution": "Per-strain BGC counts binned by region length (kb). Larger regions tend to host modular megasynthases; many small regions indicate fragmentation.",
    "domain_richness": "Per-strain BGC counts binned by total domains per BGC, separating domain-poor fragments from domain-rich modular clusters.",
    "tta_bldA_dependency": "Per-strain BGC counts binned by TTA-codon load. TTA codons require the bldA-encoded tRNA for translation, so TTA-rich BGCs are candidate bldA-dependent (developmentally regulated) clusters in actinomycetes.",
    "megasynthase_modularity": "Per-strain BGC counts binned by module number (PKS-KS + NRPS-C domains per BGC), a proxy for assembly-line length and product complexity.",
    "strain_similarity_matrix": "Strain x strain similarity (Pearson correlation on relative top-40 domain composition). Relative composition is used because raw cosine saturates on shared housekeeping domains.",
    "product_class_cooccurrence": "Product-class co-occurrence across strains (cell = number of strains carrying both classes), showing which chemistries tend to travel together in the cohort.",
    "ripp_subclass_detail": "RiPP subclass detail per strain (antiSMASH RiPP product classes: lanthipeptide classes, lassopeptide, RRE-containing, thiopeptide, sactipeptide, etc.).",
    "productclass_x_resistance": "Product class x resistance-axis tier across the cohort (BGC counts), indicating which chemistries more often carry a source-derived self-resistance signal.",
    "redox_tailoring": "Redox / oxidoreductase tailoring enzyme domain counts per strain (P450s, FAD/NAD(P)-binding oxidoreductases, dehydrogenases, flavin reductases) that install oxidations on scaffolds.",
    "distinctive_tailoring": "Distinctive tailoring enzyme domain counts per strain: radical SAM (diverse radical chemistry), prenyltransferase, glycosyl-/methyltransferases, aminotransferases and epimerases that diversify scaffolds.",
    "rare_bgc_roster": "Roster of every BGC carrying a rare diagnostic trigger, with its node/contig, trigger(s) and product class. PRIVATE-strain rows are shaded. Node/contig is listed per the project's BGC-localisation convention.",

    # ---- D-series (dot / bubble) ----
    "bubble_productclass_size_length": "Product class x strain bubble matrix: dot area = BGC count, colour = mean BGC length (kb). Small dark dots flag many short (often truncated) BGCs; large warm dots flag intact multi-class capacity.",
    "bubble_rare_triggers": "Rare diagnostic-chemistry triggers x strain as a bubble plot (dot area = BGC count) — a sparse-friendly view where single-occurrence rare chemistry reads clearly instead of vanishing in a zero-filled grid.",
    "scatter_size_vs_domains": "Per-BGC architecture landscape: region length (kb) vs domains per BGC, one dot per BGC, coloured by strain (PRIVATE = diamonds). The upper-right tail are large, domain-rich modular clusters.",
    "scatter_kcb_vs_size": "KCB reference-similarity (top bitscore, log) vs BGC length, coloured by boundary status. Truncated Edge/Full-contig BGCs trend toward weaker or absent hits — the caveat behind the KCB novelty bin.",
    "scatter_raw_vs_corrected": "Strain summary: raw vs corrected BGC count (dot area = domain hits, colour = tier). Distance below the raw=corrected line shows how much fragmentation discounts the count.",
    "strip_kcb_per_strain": "Per-strain KCB strength distribution (one dot = one BGC with a hit; the 'no-hit' count is annotated). Shows the spread of dereplication strength, not just a summary.",
    "scatter_rarechem_vs_bgcs": "Rare-chemistry richness (distinct rare triggers) vs total BGC content per strain. Strains above the trend punch above their weight in rare chemistry relative to genome size.",
    "bubble_tailoring": "Tailoring enzyme x strain bubble matrix (dot area = domain count): halogenases, chitinase, P450, glycosyl-/methyltransferases, radical SAM, siderophore synthetase, prenyltransferase.",
    "bubble_regulators": "Regulator family x strain bubble matrix (dot area = domain count). TetR: efflux/antibiotic-responsive repressors; GntR: metabolic repressors; LysR: dual activator/repressors; MarR: multidrug-resistance regulators; sigma-70: alternative sigma factors; HTH: generic DNA-binding regulators.",
    "scatter_bgc_by_class": "Per-BGC length vs domain count, coloured by dominant product class — the chemical-architecture landscape, showing how class relates to size/complexity.",
    "scatter_tta_vs_modularity": "Per-BGC bldA-dependency (TTA codons) vs megasynthase modularity (PKS-KS + NRPS-C), coloured by strain. Tests whether large modular clusters are preferentially bldA-regulated.",
}

GLOSSARY = {
    "Regulators / promoters": [
        "TetR-family: tetracycline-repressor-like; typically repress efflux pumps and antibiotic-biosynthesis operons, de-repressed by pathway intermediates.",
        "GntR-family: repressors coupling primary metabolism to regulation.",
        "LysR-family (LTTRs): dual activators/repressors, often divergently transcribed from targets.",
        "MarR-family: multidrug/antibiotic-resistance and oxidative-stress regulators.",
        "Sigma factors (sigma-70 region domains): dissociable RNA-polymerase subunits that select promoters; alternative sigmas switch on stress/developmental and secondary-metabolite promoters.",
        "HTH (helix-turn-helix): the generic DNA-binding fold shared by many of the above.",
        "AraC-family: typically activators of catabolic and stress regulons.",
    ],
    "Assembly-line genes / domains": [
        "PKS_KS (ketosynthase): condenses extender units to elongate polyketides.",
        "PKS_AT (acyltransferase): selects the extender unit (malonyl / methylmalonyl).",
        "PKS_KR/DH/ER: reductive loop (ketoreductase, dehydratase, enoylreductase) setting oxidation state — the macrolide-type signature.",
        "ACP / PP-binding (PCP): carrier proteins tethering growing chains.",
        "NRPS C (condensation), A (adenylation; selects the amino acid), T/PCP, E (epimerization): the NRPS module.",
        "TE (thioesterase): releases/cyclises the finished product.",
        "Halogenase (Trp_halogenase): installs Cl/Br, often key to bioactivity.",
        "Glycosyltransferase / methyltransferase / P450: decorate and oxidise scaffolds.",
        "Radical SAM: versatile radical chemistry, prominent in RiPP maturation.",
        "LANC_like / YcaO: lanthipeptide and other RiPP maturation enzymes.",
    ],
    "Key terms": [
        "KCB (KnownClusterBlast): similarity to characterised reference clusters — similarity, NOT identity or proof of product.",
        "CCTT triggers: diagnostic chemistry signatures flagging biosynthetic capacity consistent with a chemotype.",
        "TTA / bldA: TTA codons depend on the bldA tRNA; TTA-rich BGCs are candidate developmentally regulated clusters in actinomycetes.",
        "Boundary (Interior/Edge/Full-contig) and corrected count = Interior + 1/2*Edge + 1/4*Full-contig: discounts BGCs truncated by assembly fragmentation.",
        "Assembly tiers: GOOD >=70% / MODERATE >=45% / POOR >=20% / VERY_POOR <20% interior BGCs.",
        "PUBLIC (SID/WW) vs PRIVATE (AJS-/PENDING-): release guard; any figure set containing a private strain is PRIVATE.",
    ],
}


def write_captions(out, png_names):
    """Write figure_captions.md into <out>, covering the PNGs present (by stem lookup)."""
    lines = ["# Figure captions (base / regenerable)", "",
             "_Auto-generated base captions. Claim-safe: capacity & inferred predictions, not product identity. "
             "KCB = similarity, not identity. Refine for the manuscript as needed._", ""]
    series = {"F": [], "G": [], "D": []}
    for n in sorted(png_names):
        m = re.match(r"([FGD])(\d+)_(.+)\.png$", n)
        if not m:
            continue
        s, num, stem = m.group(1), m.group(2), m.group(3)
        cap = CAPTIONS.get(stem) or CAPTIONS.get(re.sub(r"^[A-Za-z0-9\-]+_", "", stem), "")
        series[s].append((f"{s}{num}", stem, cap))
    titles = {"F": "F-series — cross-strain heatmaps", "G": "G-series — complementary (rarity, novelty, architecture, similarity)",
              "D": "D-series — dot / bubble plots"}
    for s in ("F", "G", "D"):
        if not series[s]:
            continue
        lines += [f"## {titles[s]}", ""]
        for fid, stem, cap in series[s]:
            lines.append(f"**{fid}** ({stem}). {cap or '(caption pending)'}")
            lines.append("")
    lines += ["## Glossary — regulators, genes, and terms", ""]
    for sec, items in GLOSSARY.items():
        lines += [f"### {sec}", ""]
        for it in items:
            lines.append(f"- {it}")
        lines.append("")
    path = os.path.join(out, "figure_captions.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path

# ===== merged from cohort_figures_bridge.py (bridge) =====


from pathlib import Path


def _read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _num(x, d=0.0):
    if x is None or str(x).strip().lower() in {"", "na", "n/a", "nan", "none", "unbound"}:
        return d
    return float(x)


def _find_one(pkg_dir, suffix):
    hits = sorted(glob.glob(os.path.join(pkg_dir, f"*{suffix}")))
    return hits[0] if hits else None


def _boundary_counts(pkg_dir):
    """Interior/Edge/Full-contig counts from the package's bgc_data.json (W6)."""
    p = os.path.join(pkg_dir, "bgc_data.json")
    interior = edge = fc = 0
    try:
        d = _loadj(p)
        for b in d.get("bgcs", []):
            es = (b.get("edge_status") or "").lower()
            if es.startswith("interior"):
                interior += 1
            elif es.startswith("edge"):
                edge += 1
            else:
                fc += 1
    except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
        # Boundary composition is evidence-derived.  An unreadable source must
        # remain uncomputed rather than being rendered as a measured zero row.
        return "", "", "", f"UNCOMPUTED: {type(exc).__name__}: {exc}"
    return interior, edge, fc, "COMPUTED"


def _strain_summary_row(strain_id, pkg_dir, result):
    """One priority_summary row from a strain's package + its run-result dict."""
    ranked_path = _find_one(pkg_dir, "_RGGMCI_ranked_pairs.csv")
    ranked = _read_csv(ranked_path) if ranked_path else []
    evidence_path = _find_one(pkg_dir, "_RGGMCI_evidence.csv")
    evidence = _read_csv(evidence_path) if evidence_path else []

    def conf(r):
        return (r.get("rggmci_confidence") or "").upper()

    # v9.7.88 9.7.88-H: the ranked file stores full tier labels (HIGH_RG_GMCI_RESCUE,
    # MODERATE_RG_GMCI_CANDIDATE); `== "HIGH"` never matched, so every native cohort high-pair
    # figure read flat-zero while the master B4 layer counted them correctly. Prefix-match instead.
    high = sum(1 for r in ranked if conf(r).startswith("HIGH"))
    moderate = sum(1 for r in ranked if conf(r).startswith("MODERATE"))
    good_geom = sum(1 for r in ranked if _num(r.get("good_geometry_references")) > 0)
    best = max((_num(r.get("rggmci_score")) for r in ranked), default=0.0)
    best_refs = max((_num(r.get("supporting_references")) for r in ranked), default=0.0)
    best_geom = max((_num(r.get("good_geometry_references")) for r in ranked), default=0.0)
    interior, edge, fc, boundary_counts_status = _boundary_counts(pkg_dir)

    # v9.7.88 9.7.88-I: post-hoc cohort figures built from packages (not a live run) get an empty
    # result dict, so raw/corrected/tier/interior silently zeroed. Fall back to manifest_short.json.
    def _rget(key, ms_key):
        v = result.get(key, "")
        if v not in ("", None):
            return v
        # v9.7.408: this is an OPTIONAL fallback -- the caller already has "" as a valid answer.
        # Narrowed from a bare Exception to the three things that can actually go wrong reading an
        # optional sidecar: it is absent, unreadable, or not valid JSON. Anything else is a real bug
        # and must not be swallowed here.
        with contextlib.suppress(OSError, ValueError, TypeError):
            ms_path = _find_one(pkg_dir, "manifest_short.json") if pkg_dir else None
            if ms_path:
                return _j.loads(open(ms_path, encoding="utf-8").read()).get(ms_key, "")
        return ""

    return {
        "strain": strain_id,
        "raw_bgcs": _rget("raw_bgcs", "raw_bgcs"),
        "corrected_bgcs": _rget("corrected_bgcs", "corrected_bgcs"),
        "assembly_tier": _rget("assembly_tier", "assembly_tier"),
        "pairs_total": len(ranked),
        "high_pairs": high,
        "moderate_pairs": moderate,
        "good_geometry_pairs": good_geom,
        "evidence_rows": len(evidence),
        "interior_bgcs": interior,
        "edge_bgcs": edge,
        "full_contig_bgcs": fc,
        "boundary_counts_status": boundary_counts_status,
        "priority_score": best,
        "priority_supporting_references": best_refs,
        "priority_good_geometry_references": best_geom,
    }, ranked


def build_cohort_figures(results, outdir, logger=None):
    """Aggregate batch packages into cohort tables, then emit cross-strain figures.

    results : list of run-summary dicts from run_one_strain (each must carry
              'strain_id' and a 'package_zip' whose parent holds the package dir).
    outdir  : the run output directory (figures go under <outdir>/cohort_figures/).
    Returns the emitter's manifest dict, or a small status dict on no-op/failure.
    """
    log = logger or (lambda m: None)
    try:
        ok = [r for r in results if r.get("strain_id")]
        if len(ok) < 2:
            return {"status": "SKIPPED_SINGLE_STRAIN", "figure_count": 0}

        run_dir = Path(outdir)
        stage = run_dir / "cohort_figs_input"
        stage.mkdir(parents=True, exist_ok=True)

        summary_rows = []
        all_pairs = []
        for r in ok:
            strain_id = r["strain_id"]
            # locate the package dir: <outdir>/<strain_id>/package  (matches run layout)
            pkg_dir = None
            zip_path = r.get("package_zip", "")
            if zip_path:
                cand = Path(zip_path).parent / "package"
                if cand.exists():
                    pkg_dir = str(cand)
            if pkg_dir is None:
                cand = run_dir / strain_id / "package"
                pkg_dir = str(cand) if cand.exists() else None
            if pkg_dir is None:
                log(f"COHORT_FIGS: package dir not found for {strain_id}; skipping its row")
                continue

            row, ranked = _strain_summary_row(strain_id, pkg_dir, r)
            summary_rows.append(row)
            for pr in ranked:
                pr = dict(pr)
                pr["strain"] = strain_id
                all_pairs.append(pr)

        if len(summary_rows) < 2:
            return {"status": "SKIPPED_INSUFFICIENT_DATA", "figure_count": 0}

        # write the two cohort tables the emitter consumes
        sfields = list(summary_rows[0].keys())
        with open(stage / "cohort_priority_summary.csv", "w", newline="", encoding="utf-8") as f:
            w = _SafeDictWriter(f, fieldnames=sfields)
            w.writeheader()
            w.writerows(summary_rows)

        if all_pairs:
            pfields = []
            seen = set()
            for pr in all_pairs:
                for k in pr:
                    if k not in seen:
                        pfields.append(k); seen.add(k)
            with open(stage / "cohort_ranked_pairs_all.csv", "w", newline="", encoding="utf-8") as f:
                w = _SafeDictWriter(f, fieldnames=pfields)
                w.writeheader()
                w.writerows(all_pairs)

        out_fig = run_dir / "cohort_figures"
        result = build_cross_strain_figures(str(stage), str(out_fig), make_zip=True)
        log(f"COHORT_FIGS: {result.get('figure_count', 0)} cross-strain figures from {len(summary_rows)} strains")
        return result
    except Exception as e:  # never break the batch
        log(f"COHORT_FIGS_ERRORED: {type(e).__name__}: {e}")
        return {"status": "ERRORED", "reason": f"{type(e).__name__}: {e}", "figure_count": 0}
