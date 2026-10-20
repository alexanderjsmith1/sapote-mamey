#!/usr/bin/env python3
"""Draw protein-class PCoA figures from an ordination kit: cohort proteins among reference and MIBiG proteins.

Input: a kit folder with out_<SET>/PCOA_<SET>.tsv (id, PC1, PC2, n_represented, source, strain, locus_tag, origin, ...),
optional NEAREST_<SET>.tsv (best reference/MIBiG identity per cohort protein) and RUN_<SET>.json (pct_axes).
A cohort table (strain, cohort) assigns cohort points to panels: --panel NAME=COHORT[,COHORT...].

What is drawn:
- reference genomes grey and MIBiG blue, sized by the members each centroid represents; cohort points on top;
- fill shows identity: solid when the best reference/MIBiG match is below --label-below % (default 70), open otherwise;
  with --mid-below M (for example 85), three tiers: solid below --label-below, light fill from --label-below to M, open at M or above;
- the class tag bold at top left; no title and no other text on the artwork (the caption carries it);
- labels, one of two rules:
  * --top-strains N: up to N strains by name, one label each; strains with a point below --label-below come first (lowest
    identity first), then the strains whose points lie farthest from any reference/MIBiG point; each label sits on the
    strain's most isolated point of the same fill; a panel with N or fewer cohort points labels every point;
  * otherwise distance only: a point is labelled when its distance to the nearest reference/MIBiG point exceeds the
    --quantile of the background's own nearest-neighbour distances; same-strain points close together share a label
    ("x n"); more than --number-above labels are numbered, with the key in LABELS_<SET>_<PANEL>.tsv.
Points whose origin is in --drop-origins and strains in --exclude-strain are not drawn (they stay in the ordination).

Renderer: R (ggplot2 + ggrepel, tools/protein_pcoa_render.R) when Rscript has those packages, else matplotlib. Python
chooses the labels either way, writes ONE stamped data file per panel, runs R on exactly that file and checks that R
wrote outputs for the same stamp, so a failed run can never leave stale inputs for a later drawing.
Every SVG's visible text passes mamey.figure_policy's banned-wording check.

Outputs per panel in --out (new or empty): PCOA_<SET>_<PANEL>.pdf/.svg/.png (PNG 600 dpi), LABELS_<SET>_<PANEL>.tsv and
panel_<SET>_<PANEL>.json (counts, threshold, stamp, renderer).
"""
from __future__ import annotations

import argparse
import re
import csv
import hashlib
import io
import json, re
import logging
import math
import os
import platform
import importlib.metadata
import shutil
import subprocess
import sys
import unicodedata
import uuid
from pathlib import Path
try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from mamey.figure_policy import FigureTextRefusal, assert_no_banned_figure_text, svg_visible_text  # noqa: E402

_LOG = logging.getLogger("protein_pcoa_render")
R_SCRIPT = Path(__file__).resolve().parent / "protein_pcoa_render.R"
PALETTE = ["#0072B2", "#009E73", "#8C510A", "#CC79A7", "#56B4E9", "#D55E00"]   # mamey.figure_policy.COHORT_PALETTE order
LEADER_MAX_IN = 0.35   # M5_452 page: longest label leader at print size, read back from the drawn PDF (M3 Integrator ruling, 13 Oct 2026)
LEADER_RGB = (0x55 / 255,) * 3   # protein_pcoa_page.R leader colour "#555555"
PAGE_EXPAND = dict(x=(0.22, 0.22), y=(0.18, 0.22))   # page panel limits: data range +/- these fractions (room for 8 pt labels)
BEE_TITLES = {"KS": "PKS ketosynthase (KS) domains", "AT": "PKS acyltransferase (AT) domains", "A": "NRPS adenylation (A) domains",
              "C": "NRPS condensation (C) domains", "KR": "PKS ketoreductase (KR) domains", "DH": "PKS dehydratase (DH) domains",
              "ER": "PKS enoylreductase (ER) domains", "TE": "Thioesterase (TE) domains", "MT": "Methyltransferase (MT) domains",
              "E": "NRPS epimerization (E) domains"}   # page titles: bee Fig. S9 wording (KS, AT, A, C as printed there), same form for the rest
REF_COLOUR, MIBIG_COLOUR = "#b5b5b5", "#3a78b5"


class RenderRefusal(RuntimeError):
    """An input or output that would make a figure wrong."""


def _input_is_file(path: Path) -> bool:
    """Distinguish optional absence from a malformed existing input path."""
    if path.is_file():
        return True
    if path.exists() or path.is_symlink():
        raise RenderRefusal(f"input must be a regular file: {path}")
    return False


def file_binding(path: Path) -> dict:
    """Record an input or its absence, including optional files created later."""
    try:
        if not _input_is_file(path):
            return {"path": str(path.resolve()), "state": "NOT_PROVIDED"}
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return {"path": str(path.resolve()), "state": "PRESENT", "bytes": path.stat().st_size,
                "sha256": digest.hexdigest()}
    except OSError as exc:
        raise RenderRefusal(f"cannot read input: {path}: {exc}") from exc


def read_bound_bytes(path: Path, expected: dict) -> bytes | None:
    """Check the exact buffer consumed, including admitted optional absence."""
    try:
        if _input_is_file(path):
            raw = path.read_bytes()
            actual = {"path": str(path.resolve()), "state": "PRESENT", "bytes": len(raw),
                      "sha256": hashlib.sha256(raw).hexdigest()}
        else:
            raw = None
            actual = {"path": str(path.resolve()), "state": "NOT_PROVIDED"}
    except OSError as exc:
        raise RenderRefusal(f"cannot read input: {path}: {exc}") from exc
    if actual != expected:
        raise RenderRefusal(f"consumed input differs from its admitted binding: {path}")
    return raw


def read_bound_json(path: Path, expected: dict) -> dict:
    """Parse supplied metadata from the admitted bytes; preserve missing metadata."""
    raw = read_bound_bytes(path, expected)
    if raw is None:
        return {}
    with io.TextIOWrapper(io.BytesIO(raw)) as stream:
        return json.load(stream)


def admit_output_ids(sets: list[str], panels: list[str]) -> None:
    """Keep each requested set/panel's artifacts distinct and inside the output."""
    names = []
    for panel in panels:
        parts = panel.split("=", 1)
        if len(parts) != 2 or not parts[0]:
            raise RenderRefusal("each panel requires a nonempty NAME=COHORT specification")
        names.append(parts[0])
    if len(set(sets)) != len(sets) or len(set(names)) != len(names):
        raise RenderRefusal("duplicate set IDs or panel names would overwrite replay artifacts")
    if any(not value or "/" in value or "\\" in value for value in [*sets, *names]):
        raise RenderRefusal("set IDs and panel names must be single output filename components")
    prefixes = [f"PCOA_{s}_{name}" for s in sets for name in names]
    collision_keys = [unicodedata.normalize("NFC", unicodedata.normalize("NFC", prefix).casefold())
                      for prefix in prefixes]
    if len(set(collision_keys)) != len(collision_keys):
        raise RenderRefusal("set/panel combinations would overwrite the same replay artifact prefix")



def historical_producer(run):
    """Never substitute current rendering versions for historical fit versions."""
    if run.get("resource_schema") == "sapote-mamey.protein-pcoa-resource.v1":
        return {"state": "RECORDED", "producer_sources": run.get("producer_sources"),
                "producer_runtime": run.get("producer_runtime")}
    supplied = {key: run[key] for key in ("producer_sources", "producer_runtime", "producer") if key in run}
    return {"state": "SUPPLIED_UNVERIFIED", "metadata": supplied} if supplied else {"state": "NOT_RECORDED"}


def render_runtime(renderer, rscript=None):
    packages = {}
    for name in ("numpy", "matplotlib", "scipy"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "executable": sys.executable, "installed_distributions": packages,
            "loaded_module_versions": {name: getattr(sys.modules.get(name), "__version__", "NOT_IMPORTED")
                                       for name in ("numpy", "matplotlib", "scipy")},
            "renderer": renderer, "r_executable": file_binding(Path(rscript)) if rscript else None,
            "r_runtime": "NOT_RECORDED", "fonts": "NOT_RECORDED",
            "byte_equivalent_replay_claim": False}


def admit_resource_run(directory, name, run, run_binding, input_paths, input_bindings, admitted):
    """New resource attempts cannot masquerade as legacy incomplete kits."""
    receipt_dir = directory / "RESOURCE_ATTEMPT"
    resource_schema = run.get("resource_schema")
    if resource_schema is None and not receipt_dir.exists():
        return
    if resource_schema != "sapote-mamey.protein-pcoa-resource.v1":
        raise RenderRefusal("incomplete or unknown resource-attempt RUN")
    for filename in ("monitored_resource.json", "terminal.json"):
        path = receipt_dir / filename
        binding = file_binding(path)
        input_paths.append(path); input_bindings.append(binding); admitted[path.absolute()] = binding
    resource_path, terminal_path = receipt_dir / "monitored_resource.json", receipt_dir / "terminal.json"
    resource_binding = admitted[resource_path.absolute()]
    terminal = read_bound_json(terminal_path, admitted[terminal_path.absolute()])
    resource = read_bound_json(resource_path, resource_binding)
    expected_resource = run.get("resource_receipt", {})
    if not all(isinstance(x, dict) for x in (terminal, resource, expected_resource)):
        raise RenderRefusal("resource receipt must contain metadata objects")
    if not isinstance(terminal.get("run"), dict) or not isinstance(resource.get("watch"), dict):
        raise RenderRefusal("resource receipt must contain metadata objects")
    if (resource_binding.get("state") != "PRESENT"
            or expected_resource.get("relative_path") != "RESOURCE_ATTEMPT/monitored_resource.json"
            or expected_resource.get("sha256") != resource_binding.get("sha256")
            or terminal.get("state") != "SUCCEEDED"
            or terminal.get("run", {}).get("sha256") != run_binding.get("sha256")
            or not run.get("attempt_id") or terminal.get("attempt_id") != run["attempt_id"]
            or resource.get("attempt_id") != run["attempt_id"]
            or resource.get("watch", {}).get("exit_code") != 0
            or resource.get("watch", {}).get("stop_reason")
            or resource.get("watch", {}).get("cleanup_error")):
        raise RenderRefusal("resource attempt lacks a matching successful terminal chain")
    outputs = run.get("outputs", {})
    expected_names = {f"PCOA_{name}.tsv", f"REFERENCE_CLUSTERS_{name}.tsv"}
    if not isinstance(outputs, dict) or set(outputs) != expected_names:
        raise RenderRefusal("resource RUN output roster is incomplete")
    for filename in sorted(expected_names):
        path = directory / filename
        binding = admitted.get(path.absolute())
        if binding is None:
            binding = file_binding(path)
            input_paths.append(path); input_bindings.append(binding); admitted[path.absolute()] = binding
        if (not isinstance(outputs[filename], dict) or binding.get("state") != "PRESENT"
                or outputs[filename].get("sha256") != binding.get("sha256")):
            raise RenderRefusal("resource RUN scientific output hash changed")
    return True


def axis_metadata(run: dict, *, required: bool = False) -> dict:
    """Validate finite annotations without assigning variance or execution meaning."""
    values = run.get("pct_axes")
    if values is None:
        if required:
            raise RenderRefusal("axis percentages missing; provide RUN_<SET>.json with pct_axes")
        return {"state": "NOT_PROVIDED", "pct_axes": None}
    try:
        if not isinstance(values, list) or len(values) < 2 or any(isinstance(v, bool) for v in values):
            raise ValueError
        values = [float(v) for v in values]
        if not all(math.isfinite(v) for v in values):
            raise ValueError
    except (ValueError, TypeError):
        raise RenderRefusal("pct_axes must contain at least two finite numeric axis percentages") from None
    return {"state": "AVAILABLE", "pct_axes": values,
            "definition": {"state": "SUPPLIED_UNVERIFIED", "name": None},
            "fit_execution": "UNVERIFIED_SUPPLIED_METADATA",
            "renderer_fit_execution": "NOT_EXECUTED"}


# A source-bound definition is supported only for this inspected numerical function.
# This token fingerprint excludes layout/comments and includes the complete function.
_NATIVE_PCOA_FUNCTION_SHA256 = "66e137cfad33f64123e36159a708aeaa356af30487755a5cc94d19049a9c8674"


def bound_axis_metadata(run: dict, coordinates: dict, source: dict, source_bytes: bytes | None,
                        run_binding: dict, resource_chain: bool) -> dict:
    """Associate the known native ratio with bound coordinates; never execute a fit.

    A supplied definition/seed/version field is insufficient. Native classification
    needs the independently admitted terminal chain and exact coordinate/source hashes.
    The historical source path is metadata only and is never opened.
    """
    axes = axis_metadata(run)
    if axes["state"] != "AVAILABLE":
        return axes
    axes["annotation_run"] = run_binding
    axes["coordinates"] = coordinates
    if not resource_chain or run.get("resource_schema") != "sapote-mamey.protein-pcoa-resource.v1":
        return axes
    outputs, producers = run.get("outputs"), run.get("producer_sources")
    if not isinstance(outputs, dict) or not isinstance(producers, list):
        return axes
    name = Path(coordinates.get("path", "")).name
    native = [record for record in producers if isinstance(record, dict)
              and Path(str(record.get("path", ""))).name == "protein_pcoa_ordinate.py"]
    output = outputs.get(name)
    if (len(native) != 1 or not isinstance(output, dict)
            or coordinates.get("state") != "PRESENT" or source.get("state") != "PRESENT"
            or output.get("sha256") != coordinates.get("sha256")
            or native[0].get("sha256") != source.get("sha256")
            or native[0].get("bytes") != source.get("bytes") or source_bytes is None
            or hashlib.sha256(source_bytes).hexdigest() != source.get("sha256")):
        return axes
    import ast, tokenize
    try:
        text = source_bytes.decode("utf-8")
        functions = [node for node in ast.parse(text).body
                     if isinstance(node, ast.FunctionDef) and node.name == "classical_pcoa"]
        snippet = ast.get_source_segment(text, functions[0])
        tokens = [(tokenize.tok_name[token.type], token.string)
                  for token in tokenize.generate_tokens(io.StringIO(snippet).readline)
                  if token.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                                        tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER)]
        function_hash = hashlib.sha256(json.dumps(tokens, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
        if len(functions) != 1 or function_hash != _NATIVE_PCOA_FUNCTION_SHA256:
            return axes
    except (ValueError, SyntaxError, UnicodeError, IndexError, tokenize.TokenError):
        return axes
    axes["definition"] = {"state": "NATIVE_COORDINATE_SOURCE_BOUND",
                          "name": "100 * eigenvalue / signed trace of the double-centred squared-distance matrix",
                          "numeric_function_sha256": function_hash, "source": source,
                          "negative_coordinate_eigenvalues": "clipped to zero for coordinates only",
                          "percentages": "retained without clipping or renormalization"}
    axes["fit_execution"] = "RECORDED_SUCCESSFUL_RESOURCE_CHAIN"
    return axes


def read_tsv(path: Path, *, expected_binding: dict | None = None) -> list[dict]:
    if expected_binding is None:
        with open(path, newline="") as fh:
            return list(csv.DictReader(fh, delimiter="\t"))
    raw = read_bound_bytes(path, expected_binding)
    if raw is None:
        raise RenderRefusal(f"required TSV input is missing: {path}")
    with io.TextIOWrapper(io.BytesIO(raw), newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def embedding_tsv_rows(path: Path, binding: dict) -> list[dict]:
    """Validate raw column authority and row widths before dictionary projection."""
    raw = read_bound_bytes(path, binding)
    if raw is None:
        raise RenderRefusal(f"{path}: required embedding table is missing")
    try:
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), delimiter="\t", strict=True)
        header = next(reader, None)
        if not header or any(not h.strip() or h != h.strip() for h in header) or len(set(header)) != len(header):
            raise RenderRefusal(f"{path}: embedding headers must be nonblank, unique and unpadded")
        rows = []
        for values in reader:
            if len(values) != len(header):
                raise RenderRefusal(f"{path}: embedding row {reader.line_num} has {len(values)} fields; expected {len(header)}")
            rows.append(dict(zip(header, values)))
        return rows
    except (UnicodeError, csv.Error) as exc:
        raise RenderRefusal(f"{path}: invalid embedding TSV: {exc}") from exc


def embedding_coordinates(path: Path, rows: list[dict], key: str, binding: dict) -> list[dict]:
    """Join a finite one-to-one saved embedding to the exact kit roster, preserving order."""
    ids = [r.get("id") for r in rows]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise RenderRefusal(f"{path}: kit ids must be nonempty and unique")
    emb = {}
    for r in embedding_tsv_rows(path, binding):
        identifier = r.get("id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in emb:
            raise RenderRefusal(f"{path}: embedding ids must be nonempty and unique")
        try:
            finite = all(math.isfinite(float(r[key + axis])) for axis in ("1", "2"))
        except (KeyError, TypeError, ValueError):
            finite = False
        if not finite:
            raise RenderRefusal(f"{path}: embedding coordinates must be finite numeric values")
        emb[identifier] = r
    if set(emb) != set(ids):
        raise RenderRefusal(f"{path}: coordinates do not cover the exact kit ids")
    return [dict(r, PC1=emb[r["id"]][key + "1"], PC2=emb[r["id"]][key + "2"]) for r in rows]


# ---------------------------------------------------------------- selection (pure, tested)
def nn_dist(points, others, k_self=False):
    """Distance from each point to its nearest point in `others` (excluding itself when k_self, where points is others)."""
    import numpy as np
    if not len(points) or not len(others):
        return [math.inf] * len(points)
    P, O = np.asarray(points, float), np.asarray(others, float)
    try:
        from scipy.spatial import cKDTree
        d, _ = cKDTree(O).query(P, k=2 if k_self else 1)
        return [float(x) for x in (d[:, 1] if k_self else d)]
    except ImportError:
        out = np.empty(len(P))
        for i0 in range(0, len(P), 512):
            block = ((P[i0:i0 + 512, None, :] - O[None, :, :]) ** 2).sum(-1)
            if k_self:
                block[np.arange(block.shape[0]), np.arange(i0, i0 + block.shape[0])] = np.inf
            out[i0:i0 + 512] = np.sqrt(block.min(1))
        return [float(x) for x in out]


def quantile(values, q):
    v = sorted(values)
    if not v:
        return math.inf
    pos = (len(v) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def identity_measurement(raw):
    """Keep missing/invalid similarity separate from finite percentage measurements."""
    if raw is None or isinstance(raw, str) and not raw.strip():
        return None, "NOT_PROVIDED"
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None, "NONNUMERIC"
    if not math.isfinite(value):
        return None, "NONFINITE"
    if not 0 <= value <= 100:
        raise RenderRefusal(f"nearest identity percentage outside [0, 100]: {raw!r}")
    return value, "AVAILABLE"


def choose_labels(cohort_pts, background, *, label_below=70.0, top_strains=0, q=0.95, number_above=30, span=None):
    """cohort_pts: list of dict(x, y, strain, pid (float or None)). background: list of (x, y).
    span: the plot span the 1.5% same-strain grouping distance is taken from. Pass the span of EVERY point in the kit
    (all cohorts, excluded strains included), as the v5 script does; when None it falls back to this panel's points.
    Returns (groups, texts, threshold, numbered): groups are lists of indices into cohort_pts."""
    bg_nn = nn_dist(background, background, k_self=True) if len(background) > 1 else []
    thr = quantile(bg_nn, q)
    d = nn_dist([(p["x"], p["y"]) for p in cohort_pts], background) if background else [math.inf] * len(cohort_pts)
    pids = [identity_measurement(p["pid"])[0] for p in cohort_pts]
    low = [pid is not None and pid < label_below for pid in pids]
    idx = list(range(len(cohort_pts)))
    if top_strains:
        if len(idx) <= top_strains:
            groups = [[i] for i in idx]
        else:
            order = sorted(idx, key=lambda i: (0, cohort_pts[i]["pid"], i) if low[i] else (1, -d[i], i))
            groups, seen = [], set()
            for i in order:
                s = cohort_pts[i]["strain"]
                if s in seen:
                    continue
                seen.add(s)
                same = [j for j in idx if cohort_pts[j]["strain"] == s and low[j] == low[i]
                        and (pids[j] is None) == (pids[i] is None)]
                groups.append([max(same, key=lambda j: (d[j], -j))])
                if len(groups) >= top_strains:
                    break
        return groups, [cohort_pts[g[0]]["strain"] for g in groups], thr, False
    if span is None:
        xs = [p["x"] for p in cohort_pts] + [u for u, _ in background]
        ys = [p["y"] for p in cohort_pts] + [v for _, v in background]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) if xs else 1.0
    cand = sorted([i for i in idx if d[i] > thr], key=lambda i: (-d[i], i))
    groups = []
    for i in cand:
        g = next((g for g in groups if cohort_pts[g[0]]["strain"] == cohort_pts[i]["strain"]
                  and (pids[g[0]] is None) == (pids[i] is None)
                  and math.hypot(cohort_pts[g[0]]["x"] - cohort_pts[i]["x"], cohort_pts[g[0]]["y"] - cohort_pts[i]["y"]) < .015 * span),
                 None)
        (g.append(i) if g else groups.append([i]))
    numbered = len(groups) > number_above
    texts = []
    for n, g in enumerate(groups, 1):
        if numbered:
            texts.append(str(n))
        else:
            known_pids = [pids[k] for k in g if pids[k] is not None]
            texts.append(f"{cohort_pts[g[0]]['strain']}{' x' + str(len(g)) if len(g) > 1 else ''}"
                         + (f" ({min(known_pids):.0f}%)" if known_pids else ""))
    return groups, texts, thr, numbered


# ---------------------------------------------------------------- rendering
def discover_rscript() -> str | None:
    exe = shutil.which("Rscript")
    if not exe:
        return None
    exe = str(Path(exe).absolute())
    r = subprocess.run([exe, "-e", 'q(status = as.integer(!all(sapply(c("ggplot2","ggrepel","jsonlite","svglite"), '
                              'requireNamespace, quietly = TRUE))))'], capture_output=True)
    return exe if r.returncode == 0 else None


def r_available() -> bool:
    return discover_rscript() is not None


def selected_rscript(a) -> str:
    exe = getattr(a, "_rscript", None)
    if exe is None:
        exe = discover_rscript()
        if exe is None:
            raise RenderRefusal("Rscript with required packages is unavailable")
        a._rscript = exe
    return exe


def render_r(spec: Path, out_prefix: Path, stamp: str, *, rscript: str | None = None) -> None:
    exe = rscript or discover_rscript()
    if exe is None:
        raise RenderRefusal("Rscript with required packages is unavailable")
    r = subprocess.run([exe, str(R_SCRIPT), str(spec), str(out_prefix), stamp], capture_output=True, text=True)
    if r.returncode != 0:
        raise RenderRefusal(f"R renderer failed for {out_prefix.name}: {r.stderr.strip()[-400:]}")
    done = Path(str(out_prefix) + ".stamp")
    if not done.exists() or done.read_text().strip() != stamp:
        raise RenderRefusal(f"R renderer did not confirm stamp {stamp} for {out_prefix.name}")
    done.unlink()


def tint(hex_colour: str, keep: float = 0.45) -> str:
    """The panel colour mixed with white (keep = share of the colour), the light fill of the middle identity tier."""
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join(f"{round(255 - (255 - c) * keep):02x}" for c in (r, g, b))


def render_matplotlib(spec: dict, out_prefix: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"pdf.fonttype": 42, "svg.fonttype": "none", "font.family": ["Arial", "Helvetica", "DejaVu Sans"]})
    fig, ax = plt.subplots(figsize=(7, 7.2))
    for layer, colour in (("ref", REF_COLOUR), ("mibig", MIBIG_COLOUR)):
        pts = [p for p in spec["points"] if p["layer"] == layer]
        if pts:
            ax.scatter([p["x"] for p in pts], [p["y"] for p in pts], s=[3 + 1.5 * math.sqrt(p["size"]) for p in pts], c=colour,
                       lw=0, alpha=.7, label=spec["legend"][layer])
    col = spec["colour"]
    lo = [p for p in spec["points"] if p["layer"] == "iso_low"]
    mid = [p for p in spec["points"] if p["layer"] == "iso_mid"]
    hi = [p for p in spec["points"] if p["layer"] == "iso_high"]
    unknown = [p for p in spec["points"] if p["layer"] == "iso_unknown"]
    if lo:
        ax.scatter([p["x"] for p in lo], [p["y"] for p in lo], s=22, c=col, edgecolors="black", lw=.4, zorder=3,
                   label=spec["legend"]["iso_low"])
    if mid:
        ax.scatter([p["x"] for p in mid], [p["y"] for p in mid], s=22, facecolors=spec["mid_fill"], edgecolors=col, lw=.8, zorder=3,
                   label=spec["legend"]["iso_mid"])
    if hi:
        ax.scatter([p["x"] for p in hi], [p["y"] for p in hi], s=22, facecolors="white", edgecolors=col, lw=1.1, zorder=3,
                   label=spec["legend"]["iso_high"])
    if unknown:
        ax.scatter([p["x"] for p in unknown], [p["y"] for p in unknown], s=22, marker="D", facecolors="white",
                   edgecolors="#555555", lw=1.1, zorder=3, label=spec["legend"]["iso_unknown"])
    for lab in spec["labels"]:
        ax.annotate(lab["label"], (lab["x"], lab["y"]), xytext=(6, 6), textcoords="offset points", fontsize=6,
                    arrowprops=dict(arrowstyle="-", lw=.35, color="#555555"))
    ax.text(0.01, 0.99, spec["tag"], transform=ax.transAxes, ha="left", va="top", fontsize=9, fontweight="bold")
    ax.set_xlabel(spec["xlab"]); ax.set_ylabel(spec["ylab"]); ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", bbox_to_anchor=(0, -0.1))
    for ext in ("pdf", "svg"):
        fig.savefig(f"{out_prefix}.{ext}", bbox_inches="tight")
    fig.savefig(f"{out_prefix}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- driver
def build_panel(a, s, rows, near, run, cohorts, panel, cohort_set, colour, label_text, titles, out: Path, renderer: str,
                *, drop_origins: set[str] | None = None, forced_groups=None, spec_only: bool = False, layout: str | None = None,
                keep_k: int | None = None):
    drop = ({l.strip() for l in open(a.drop_origins)} if a.drop_origins else set()) if drop_origins is None else drop_origins
    excluded = set(a.exclude_strain or [])
    bg, cpts, points = [], [], []
    n_ref = n_mib = 0
    for r in rows:
        x, y = float(r["PC1"]), float(r["PC2"])
        size = float(r.get("n_represented") or 1)
        if r["source"] == "isolate":
            if r.get("origin") in drop or r["strain"] in excluded or cohorts.get(r["strain"]) not in cohort_set:
                continue
            raw_identity = near.get(r["id"])
            pid, identity_state = identity_measurement(raw_identity)
            cpts.append(dict(x=x, y=y, strain=r["strain"], pid=pid, row=r, identity_state=identity_state,
                             identity_raw=None if raw_identity is None else str(raw_identity)))
        else:
            layer = "mibig" if r["source"] == "MIBiG" else "ref"
            bg.append((x, y))
            points.append(dict(x=x, y=y, layer=layer, size=size))
            if layer == "mibig":
                n_mib += int(size)
            else:
                n_ref += int(size)
    kx, ky = [float(r["PC1"]) for r in rows], [float(r["PC2"]) for r in rows]
    kit_span = max(max(kx) - min(kx), max(ky) - min(ky)) if rows else 1.0   # every kit point, as in v5
    groups, texts, thr, numbered = choose_labels(cpts, bg, label_below=a.label_below, top_strains=a.top_strains, q=a.quantile,
                                                 number_above=a.number_above, span=kit_span)
    if forced_groups is not None:   # label the same proteins as another panel
        groups = forced_groups
    all_groups = groups   # ranked: most distant outlier first (choose_labels)
    if keep_k is not None:   # M5_452 page: the keep_k most distant outlier groups
        groups = groups[:keep_k]; numbered = len(groups) > a.number_above
    short = ({r["strain"]: r.get("short") or r["strain"] for r in read_tsv(Path(a.label_names))} if getattr(a, "label_names", None) else {})
    if short and not numbered:   # short canvas label (house rule 6 name goes to the LABELS key)
        texts = [short.get(cpts[g[0]]["strain"], cpts[g[0]]["strain"]) + (f" x{len(g)}" if len(g) > 1 else "") for g in groups]
    elif forced_groups is not None or keep_k is not None:
        texts = ([str(n) for n in range(1, len(groups) + 1)] if numbered
                 else [cpts[g[0]]["strain"] + (f" x{len(g)}" if len(g) > 1 else "") for g in groups])
    low = [p["pid"] is not None and p["pid"] < a.label_below for p in cpts]
    mid = [not lw and a.mid_below is not None and p["pid"] is not None and p["pid"] < a.mid_below for p, lw in zip(cpts, low)]
    unknown = [p["pid"] is None for p in cpts]
    for p, lw, md, unk in zip(cpts, low, mid, unknown):
        points.append(dict(x=p["x"], y=p["y"], layer="iso_unknown" if unk else ("iso_low" if lw else ("iso_mid" if md else "iso_high")), size=1))
    title, tag, unit = titles.get(s, (s, s, "proteins"))
    axes = getattr(a, "_axis_metadata_by_set", {}).get(s) or axis_metadata(run, required=getattr(a, "require_axis_metadata", False))
    pct = axes["pct_axes"]
    mt = "reference/MIBiG" if n_mib else "reference"
    nlo = sum(low); nmd = sum(mid); n_unknown = sum(unknown); nhi = len(cpts) - nlo - nmd - n_unknown
    slo = len({p["strain"] for p, lw in zip(cpts, low) if lw}); smd = len({p["strain"] for p, md in zip(cpts, mid) if md})
    shi = len({p["strain"] for p, lw, md, unk in zip(cpts, low, mid, unknown) if not lw and not md and not unk})
    sun = len({p["strain"] for p, unk in zip(cpts, unknown) if unk})
    missingness = dict(states={state: sum(p["identity_state"] == state for p in cpts)
                               for state in ("AVAILABLE", "NOT_PROVIDED", "NONNUMERIC", "NONFINITE")},
                       records=[dict(id=p["row"]["id"], strain=p["strain"], state=p["identity_state"], raw=p["identity_raw"])
                                for p, unk in zip(cpts, unknown) if unk])
    top = a.mid_below if a.mid_below is not None else a.label_below
    spec = dict(set=s, panel=panel, tag=tag, colour=colour,
                xlab=({"trimap": "TriMap 1", "tsne": "t-SNE 1"}.get(layout or getattr(a, "layout", "pcoa"))
                      or (f"PCoA 1 ({pct[0]:.1f}%)" if pct is not None else "PCoA 1")),
                ylab=({"trimap": "TriMap 2", "tsne": "t-SNE 2"}.get(layout or getattr(a, "layout", "pcoa"))
                      or (f"PCoA 2 ({pct[1]:.1f}%)" if pct is not None else "PCoA 2")),
                legend=dict(ref=f"reference genomes ({n_ref:,} {unit})", mibig=f"MIBiG ({n_mib:,} {unit})",
                            iso_low=f"{label_text} ({nlo:,} {unit}, {slo} strains): best {mt} match < {a.label_below:.0f}% identity",
                            iso_high=f"{label_text} ({nhi:,} {unit}, {shi} strains): best {mt} match >= {top:.0f}% identity"),
                points=points, mid_fill=tint(colour),
                labels=[dict(x=sum(cpts[k]["x"] for k in g) / len(g), y=sum(cpts[k]["y"] for k in g) / len(g), label=t)
                        for g, t in zip(groups, texts)])
    if n_unknown:
        spec["legend"]["iso_unknown"] = f"{label_text} ({n_unknown:,} {unit}, {sun} strains): best {mt} identity unavailable"
    if getattr(a, "source_style", None):   # M5_452_pcoa_source_style
        spec["source_style"] = dict(genus=a.source_style, ref_fill=a.source_style_fill, mibig_fill=a.mibig_fill,
                                     ref_outline=a.source_style_outline, mibig_outline=a.mibig_outline)
    if a.mid_below is not None:
        spec["legend"]["iso_mid"] = (f"{label_text} ({nmd:,} {unit}, {smd} strains): best {mt} match "
                                     f"{a.label_below:.0f}–{a.mid_below:.0f}% identity")
    assert_no_banned_figure_text([spec["tag"], spec["xlab"], spec["ylab"], *spec["legend"].values(), *texts],
                                 figure_id=f"{s}_{panel}")
    lay = layout or getattr(a, "layout", "pcoa"); prefix = out / f"{lay.upper()}_{s}_{panel}"
    if spec_only:
        dist = nn_dist([(p["x"], p["y"]) for p in cpts], bg) if bg else [math.inf] * len(cpts)
        return dict(spec=spec, groups=groups, texts=texts, cpts=cpts, low=low, mid=mid, unknown=unknown, numbered=numbered, threshold=thr,
                    counts=dict(n_cohort_points=len(cpts), n_low=nlo, n_mid=nmd, n_high=nhi, n_unknown=n_unknown,
                                identity_missingness=missingness, n_ref=n_ref, n_mibig=n_mib), layout=lay,
                    all_groups=all_groups, dist=dist, short=short, axis_metadata=axes)
    stamp = uuid.uuid4().hex
    if getattr(a, "min_text_pt", None):
        spec["min_text"] = dict(min_text_pt=a.min_text_pt, print_width=a.print_width,
                                helper=str(_ROOT / "tools" / "sapote_min_text.R"), layout=str(_ROOT / "tools" / "sapote_pub_layout.R"))
    if renderer == "r":
        spec_path = out / f".render_{s}_{panel}_{stamp}.json"
        spec_path.write_text(json.dumps(dict(spec, stamp=stamp)))
        try:
            render_r(spec_path, prefix, stamp, rscript=selected_rscript(a))
        finally:
            spec_path.unlink(missing_ok=True)
    else:
        render_matplotlib(spec, prefix)
    for ext in ("pdf", "svg", "png"):
        if not Path(f"{prefix}.{ext}").exists():
            raise RenderRefusal(f"{prefix.name}.{ext} was not written")
    assert_no_banned_figure_text(svg_visible_text(Path(f"{prefix}.svg").read_text()), figure_id=prefix.name)
    if spec.get("min_text"):
        sys.path.insert(0, str(_ROOT)); from tools._min_text_check import enforce as _mt_enforce
        try:
            _mt_enforce(f"{prefix}.pdf", a.min_text_pt)
        except RuntimeError as exc:
            raise RenderRefusal(str(exc)) from None
    from mamey.figure_stamp import stamp_file
    for ext in (".png", ".pdf", ".svg"):
        stamp_file(Path(str(prefix) + ext), "protein_pcoa_render")
    names = ({r["strain"]: r["display"] for r in read_tsv(Path(a.label_names))} if getattr(a, "label_names", None) else {})
    with open(out / f"LABELS_{s}_{panel}.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["label", "label_text", "strain", "display_name", "region_file", "locus_tag", "X", "Y", "nearest_identity_pct", "fill", "nearest_identity_state"])
        for n, (g, t) in enumerate(zip(groups, texts), 1):
            for k in g:
                p = cpts[k]
                w.writerow([n, t, p["strain"], names.get(p["strain"], ""), p["row"].get("origin", ""), p["row"].get("locus_tag", ""), f"{p['x']:.5f}",
                            f"{p['y']:.5f}", f"{p['pid']:.1f}" if p["pid"] is not None else "",
                            "unknown" if unknown[k] else ("solid" if low[k] else ("light" if mid[k] else "open")), p["identity_state"]])
    receipt = dict(set=s, panel=panel, layout=lay, min_text=spec.get("min_text"), cohorts=sorted(cohort_set), renderer=renderer, stamp=stamp, labels=len(groups),
                   numbered=numbered, threshold=thr, n_cohort_points=len(cpts), n_low=nlo, n_mid=nmd, n_high=nhi, n_unknown=n_unknown,
                   identity_missingness=missingness, n_ref=n_ref, n_mibig=n_mib,
                   label_rule=("top_strains" if a.top_strains else "distance_quantile"), top_strains=a.top_strains,
                   quantile=a.quantile, label_below=a.label_below, mid_below=a.mid_below, title=title,
                   axis_metadata=axes)
    (out / f"panel_{s}_{panel}.json").write_text(json.dumps(receipt, indent=1))
    return receipt


def page_legend(a, leg, n_ref_genomes=None):
    '''Bee Fig. S9 shared-legend wording (build_pcoa_figures.py legend_handles), plus the reference genome count (M5_452 P4).'''
    who = (a.panel_label[0].split("=", 1)[1] if a.panel_label else "cohort protein")
    ref = (getattr(a, "reference_label", None)
           or (f"reference genomes, n = {n_ref_genomes:,} (cluster centroids)" if n_ref_genomes else "reference genomes (cluster centroids)"))
    out = dict(ref=ref, mibig="MIBiG characterized clusters",
               iso_low=f"{who}, best reference/MIBiG match < {a.label_below:.0f}% identity")
    top = a.mid_below if a.mid_below is not None else a.label_below
    if a.mid_below is not None:
        out["iso_mid"] = f"{who}, best reference/MIBiG match {a.label_below:.0f}–{a.mid_below:.0f}% identity"
    out["iso_high"] = f"{who}, best reference/MIBiG match ≥ {top:.0f}% identity"
    if leg.get("iso_unknown"):
        out["iso_unknown"] = f"{who}, best reference/MIBiG identity unavailable"
    return out


def point_radius_pt(size_mm, stroke=0.35):
    """Drawn radius (pt) of a ggplot2 shape 16/21 point: fontsize = size * .pt + stroke * .stroke / 2; circle radius 0.375 x fontsize,
    plus half the outline."""
    return 0.375 * (size_mm * 72.27 / 25.4 + stroke * 96 / 25.4 / 2) + stroke * 72.27 / 25.4 / 2


def _boxes_overlap(a, b):
    return a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]


def _segment_hits_box(seg, box):
    """Liang-Barsky clip: does the segment (x0, y0, x1, y1) pass through the box (x0, x1, y0, y1)?"""
    x0, y0, x1, y1 = seg; dx, dy = x1 - x0, y1 - y0; t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - box[0]), (dx, box[1] - x0), (-dy, y0 - box[2]), (dy, box[3] - y0)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def _segments_cross(p, q):
    """Proper crossing of two segments (x0, y0, x1, y1); touching end points do not count."""
    def orient(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d1 = orient(*q[:2], *q[2:], *p[:2]); d2 = orient(*q[:2], *q[2:], *p[2:])
    d3 = orient(*p[:2], *p[2:], *q[:2]); d4 = orient(*p[:2], *p[2:], *q[2:])
    return d1 * d2 < 0 and d3 * d4 < 0


def place_labels_pt(targets, texts, obstacles, rect, blocked, *, font_size, italic, max_leader_pt, pad=1.5, step=1.5):
    """M5_452 P2/P3: bee Fig. S9 label placement (bee kit plot_pcoa.py place_labels, lines 62-65), in print points on the final page:
    for each label in rank order, anchor points on rings around its target (3 pt to max_leader_pt from the point edge, step pt apart,
    16 directions, nearest ring first); keep the first label box that lies inside the panel rectangle and covers no point (any layer),
    no earlier label or leader and no blocked box (panel title), and whose leader crosses no earlier leader. A label with no free spot is not drawn (None).
    targets: [(x, y, radius)]; obstacles: (n, 3) array of point centre x, y and radius; rect and boxes: (x0, x1, y0, y1)."""
    import numpy as np
    from tools._min_text_check import _font_length
    face, h = ("Arial-ItalicMT" if italic else "ArialMT"), 0.93 * font_size   # ascent 0.72 + descent 0.21 em
    X, Y, R = obstacles[:, 0], obstacles[:, 1], obstacles[:, 2]
    boxes, segs, out = list(blocked), [], []
    angles = [k * math.pi / 8 for k in range(16)]
    radii = [3.0 + step * n for n in range(int((max_leader_pt - 3.0) / step) + 1)]
    for (tx, ty, tr), text in zip(targets, texts):
        w = _font_length(text, face, font_size); best = None
        for r in radii:
            for th in angles:
                c, s = math.cos(th), math.sin(th)
                ax, ay = tx + (tr + r) * c, ty + (tr + r) * s
                hj = 0.0 if c > 0.38 else (1.0 if c < -0.38 else 0.5); vj = 0.0 if s > 0.38 else (1.0 if s < -0.38 else 0.5)
                b = (ax - hj * w - pad, ax + (1 - hj) * w + pad, ay - vj * h - pad, ay + (1 - vj) * h + pad)
                if b[0] < rect[0] or b[1] > rect[1] or b[2] < rect[2] or b[3] > rect[3]:
                    continue
                dx = np.maximum(np.maximum(b[0] - X, 0.0), X - b[1]); dy = np.maximum(np.maximum(b[2] - Y, 0.0), Y - b[3])
                if np.any(dx * dx + dy * dy < R * R):
                    continue
                seg = (tx + tr * c, ty + tr * s, ax, ay)
                if any(_boxes_overlap(b, o) or _segment_hits_box(seg, o) for o in boxes) or any(_segment_hits_box(q, b) for q in segs):
                    continue
                if any(_segments_cross(seg, q) for q in segs):
                    continue
                best = dict(anchor=(ax, ay), seg=seg, hjust=hj, vjust=vj, box=b, leader_pt=r); break
            if best:
                break
        out.append(best)
        if best:
            boxes.append(best["box"]); segs.append(best["seg"])
    return out


def embedding_meta(table, lays, admitted=None):
    """Optional exact sidecar metadata; binding is not proof that a fit was executed."""
    if not table or all(l == "pcoa" for l in lays):
        return {}
    t = Path(table); sidecar = t.with_suffix(".json")
    table_binding = admitted[t.absolute()] if admitted is not None else file_binding(t)
    binding = admitted[sidecar.absolute()] if admitted is not None else file_binding(sidecar)
    result = dict(state="NOT_PROVIDED", table=table_binding, receipt=binding, by_layout={},
                  fit_execution="NOT_ESTABLISHED_BY_RENDER_REPLAY")
    raw = read_bound_bytes(sidecar, binding)
    if raw is None:
        return result
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise RenderRefusal(f"{sidecar}: invalid embedding metadata JSON") from exc
    if not isinstance(payload, dict):
        raise RenderRefusal(f"{sidecar}: embedding metadata must be an object")
    if table_binding["state"] != "PRESENT" or payload.get("coordinates_sha256") != table_binding["sha256"]:
        result["state"] = "UNBOUND_METADATA"
        return result
    result["state"] = "SUPPLIED_COORDINATE_BOUND"
    for lay in dict.fromkeys(l for l in lays if l != "pcoa"):
        metadata = payload.get(lay)
        if not isinstance(metadata, dict):
            result["by_layout"][lay] = {"state": "METHOD_NOT_PROVIDED"}
            continue
        version, seed = metadata.get("version"), metadata.get("seed")
        if not isinstance(version, str) or not version.strip() or type(seed) is not int or seed < 0:
            result["by_layout"][lay] = {"state": "INCOMPLETE_METHOD_METADATA"}
            continue
        result["by_layout"][lay] = dict(state="SUPPLIED_COORDINATE_BOUND", version=version, seed=seed,
                                        parameters=metadata.get("parameters", {}))
    return result


def page_execution_record(prefix: Path, stamp: str) -> dict:
    """Read the exact in-run R record and observe fonts used in the final PDF."""
    path = Path(str(prefix) + "_runtime.json")
    binding = file_binding(path)
    if binding["state"] != "PRESENT":
        raise RenderRefusal("page renderer did not supply an in-run runtime record")
    payload = read_bound_json(path, binding)
    versions = payload.get("loaded_namespace_versions") if isinstance(payload, dict) else None
    if (not isinstance(payload, dict) or payload.get("schema") != "sapote-mamey.r-page-execution.v1"
            or payload.get("stamp") != stamp or payload.get("scope") != "CURRENT_RENDER_PROCESS"
            or payload.get("labeler") != "BEE_GREEDY_PRINT_POINT_PLACEMENT_AND_R_GEOM_TEXT"
            or payload.get("numeric_fit_execution") != "NOT_EXECUTED_BY_THIS_RENDERER"
            or not isinstance(payload.get("r_version"), str) or not payload["r_version"]
            or not isinstance(versions, dict)
            or any(not isinstance(versions.get(name), str) or not versions[name]
                   for name in ("ggplot2", "jsonlite", "patchwork", "svglite", "ggtext"))):
        raise RenderRefusal("page runtime record is incomplete or does not match the render stamp")
    from pypdf import PdfReader
    pdf = Path(str(prefix) + ".pdf")
    pdf_binding = file_binding(pdf)
    faces, raw_names, runs = set(), set(), []
    def font_use(text, cm, tm, font, size):
        if not text or not text.strip():
            return
        name = str(font.get("/BaseFont", "")) if font else ""
        if not name:
            raise RenderRefusal("final page PDF text has an unrecorded font")
        raw_names.add(name)
        faces.add(re.sub(r"^[A-Z]{6}\+", "", name.lstrip("/")))
        runs.append(1)
    try:
        for page in PdfReader(pdf).pages:
            page.extract_text(visitor_text=font_use)
    except RenderRefusal:
        raise
    except Exception as exc:
        raise RenderRefusal(f"cannot observe final PDF fonts: {exc}") from exc
    if not faces or file_binding(pdf) != pdf_binding:
        raise RenderRefusal("final page PDF font observation failed or PDF changed")
    return dict(r_runtime=dict(state="RECORDED_IN_RENDER_PROCESS", binding=binding, record=payload),
                fonts=dict(state="OBSERVED_FINAL_PDF_TEXT", faces=sorted(faces), base_fonts=sorted(raw_names),
                           text_runs=len(runs), source_pdf=pdf_binding))


def page_raster_artifacts(prefix: Path, print_width: float) -> list[dict]:
    """Bind direct-R rasters at their declared width; metadata alone is insufficient."""
    from PIL import Image
    if not math.isfinite(print_width) or print_width <= 0:
        raise RenderRefusal("page print width must be finite and positive")
    records = []
    for suffix, role in ((".png", "CLEAN_NATIVE_ARTWORK"), ("_plot_only.png", "CLEAN_NATIVE_SLIDE_ARTWORK")):
        path = Path(str(prefix) + suffix)
        if not path.is_file():
            raise RenderRefusal(f"page native raster missing: {path.name}")
        with Image.open(path) as image:
            width, height = image.size
            metadata_dpi = list(image.info.get("dpi", ())) or None
        if width + 1 < print_width * 300:
            raise RenderRefusal(f"page native-pixel floor failed: {path.name}: {width}px at {print_width}in")
        records.append(dict(**file_binding(path), role=role, pixels=[width, height],
                            declared_print_width_in=print_width, effective_dpi_by_width=width / print_width,
                            metadata_dpi=metadata_dpi, provenance="DIRECT_NATIVE_R_RENDER_BY_BOUND_SOURCE"))
    return records


def write_page_labels(path, lays, full, placed, genome_no, names, q):
    """Write new page tables; append canonical fields and retain the default p95 column."""
    from tools.protein_pcoa_page_docs import label_selection_metadata
    schema = label_selection_metadata(q)
    with open(path, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["panel", "layout", "outlier_rank", "drawn", "label_text", "leader_in", "genome_number", "strain", "display_name", "region_file", "locus_tag",
                    "nearest_identity_pct", "fill", "x", "y", "distance_to_nearest_background", "threshold_p95", "nearest_identity_state", "threshold_distance", "label_quantile"])
        for c, (lay, b) in enumerate(zip(lays, full)):
            for l, g in zip(placed[c], b["all_groups"]):
                for k in g:
                    p = b["cpts"][k]
                    w.writerow(["abcdefgh"[c], lay, l["rank"], "yes" if l["res"] else ("no: " + l.get("dropped", f"no free spot within {LEADER_MAX_IN} in")),
                                l["text"], f"{l['res']['leader_pt'] / 72:.3f}" if l["res"] else "", genome_no.get(p["strain"], ""), p["strain"],
                                names.get(p["strain"], ""),
                                p["row"].get("origin", ""), p["row"].get("locus_tag", ""), f"{p['pid']:.1f}" if p["pid"] is not None else "",
                                "unknown" if b["unknown"][k] else ("solid" if b["low"][k] else ("light" if b["mid"][k] else "open")), f"{p['x']:.5f}", f"{p['y']:.5f}",
                                f"{b['dist'][k]:.5f}", f"{b['threshold']:.5f}" if q == 0.95 else "", p["identity_state"],
                                f"{b['threshold']:.5f}", q])
    return schema


def build_page(a, s, rows, near, run, cohorts, emb_tables, admitted, colours, labels, titles, out, drop_origins, meta):
    '''M5_452 page mode, defaults not knobs: one panel per layout in --page, bee Fig. S9 print style (tools/protein_pcoa_page.R), one
    shared legend. Labels: the bee Fig. S9 outlier rule computed in each panel (choose_labels distance branch; bee kit plot_pcoa.py lines
    85-90, 105-116), placed by the bee greedy placement (place_labels_pt) on the final page geometry read from a label-free trial PDF,
    leaders <= LEADER_MAX_IN; the drawn PDF is read back (overlaps, leader lengths) and the page refused if a fault cannot be removed.'''
    if not getattr(a, "min_text_pt", None):
        raise RenderRefusal("--page needs --min-text-pt (the page is always saved through the min-text gate)")
    if len(a.panel) != 1:
        raise RenderRefusal("--page draws one cohort panel per layout; pass exactly one --panel")
    if a.top_strains:
        raise RenderRefusal("--page labels the bee Fig. S9 outliers and places them automatically; --top-strains is not used in page mode")
    import numpy as np
    from tools._min_text_check import enforce as _mt_enforce, page_label_faults as _faults, pdf_axis_panels as _axis_panels
    name, cs = a.panel[0].split("=", 1); cohort_set = set(cs.split(",")); lays = a.page.split(","); P = len(lays)
    by_lay = {}
    for lay in lays:
        r2 = rows
        if lay != "pcoa":
            ep = Path(emb_tables[s]); key = "TRIMAP" if lay == "trimap" else "TSNE"
            r2 = embedding_coordinates(ep, rows, key, admitted[ep.absolute()])
        by_lay[lay] = r2
    full = [build_panel(a, s, by_lay[lay], near, run, cohorts, name, cohort_set, colours.get(name, PALETTE[0]),
                        labels.get(name, f"{name} isolates"), titles, out, "r", drop_origins=drop_origins,
                        spec_only=True, layout=lay, keep_k=None) for lay in lays]
    n_out = [len(b["all_groups"]) for b in full]
    genome_no = {}   # cohort table order: number n is the same genome in every panel and every page drawn from this table
    for strain, coh in cohorts.items():
        if coh in cohort_set and strain not in genome_no:
            genome_no[strain] = len(genome_no) + 1
    cohort_strains = {p["strain"] for b in full for p in b["cpts"]}
    n_ref_genomes = len({r["strain"] for r in meta if r.get("strain") and r.get("source") not in ("isolate", "MIBiG")
                         and r["strain"] not in cohort_strains})
    legend = page_legend(a, full[0]["spec"]["legend"], n_ref_genomes)
    lims = []
    for b in full:
        xs = [p["x"] for p in b["spec"]["points"]]; ys = [p["y"] for p in b["spec"]["points"]]
        dx, dy = (max(xs) - min(xs)) or 1.0, (max(ys) - min(ys)) or 1.0
        lims.append(dict(xlim=[min(xs) - PAGE_EXPAND["x"][0] * dx, max(xs) + PAGE_EXPAND["x"][1] * dx],
                         ylim=[min(ys) - PAGE_EXPAND["y"][0] * dy, max(ys) + PAGE_EXPAND["y"][1] * dy]))
    prefix = out / f"PAGE_{s}_{name}_{'_'.join(l.upper() for l in lays)}"
    trials = out / f"fit_trials_{s}"; trials.mkdir(exist_ok=True)
    col = lambda pts, k: [p[k] for p in pts]

    def draw(labs, probe, tag=""):
        stamp = uuid.uuid4().hex; pre = (trials / f"{prefix.name}_{tag}") if probe else prefix
        page = dict(stamp=stamp, probe=probe, ncol=P, panel_height=3.6, italic_labels=bool(getattr(a, "italic_labels", False)),
                    legend=legend, leader_colour="#555555",
                    panels=[dict(tag=b["spec"]["tag"], xlab=b["spec"]["xlab"], ylab=b["spec"]["ylab"], **lims[c],
                                 points={k: col(b["spec"]["points"], k) for k in ("x", "y", "layer", "size")},
                                 labels={k: [l[k] for l in labs[c]] for k in ("x", "y", "label", "hjust", "vjust", "sx", "sy", "face")})
                            for c, b in enumerate(full)],
                    min_text=dict(min_text_pt=a.min_text_pt, print_width=a.print_width,
                                  helper=str(_ROOT / "tools" / "sapote_min_text.R"), layout=str(_ROOT / "tools" / "sapote_pub_layout.R")))
        spec_path = out / f".page_{s}_{stamp}.json"; spec_path.write_text(json.dumps(page))
        try:
            r = subprocess.run([selected_rscript(a), str(_ROOT / "tools" / "protein_pcoa_page.R"), str(spec_path), str(pre), stamp],
                               capture_output=True, text=True)
        finally:
            spec_path.unlink(missing_ok=True)
        if r.returncode == 0:
            done = Path(str(pre) + ".stamp")
            if not done.exists() or done.read_text().strip() != stamp:
                raise RenderRefusal(f"page renderer did not confirm stamp for {pre.name}")
            done.unlink()
        return pre, r, page

    # 1. label-free trial page at the final size: panel rectangles (pt) from the drawn axis lines
    pre, r, _ = draw([[] for _ in range(P)], True, "geometry")
    if r.returncode != 0:
        raise RenderRefusal(f"trial page failed for {prefix.name}: {r.stderr.strip()[-600:]}")
    rects = _axis_panels(f"{pre}.pdf", P)
    if len(rects) != P:
        raise RenderRefusal(f"{pre.name}: found {len(rects)} panel axis frames, expected {P}")
    # 2. bee greedy placement per panel, in print points
    from tools._min_text_check import _font_length
    placed, fs = [], float(a.min_text_pt)
    for c, b in enumerate(full):
        rx0, rx1, ry0, ry1 = rects[c]; (xl0, xl1), (yl0, yl1) = lims[c]["xlim"], lims[c]["ylim"]
        tx = lambda x: rx0 + (x - xl0) / (xl1 - xl0) * (rx1 - rx0); ty = lambda y: ry0 + (y - yl0) / (yl1 - yl0) * (ry1 - ry0)
        pts = b["spec"]["points"]
        obst = np.array([(tx(p["x"]), ty(p["y"]), point_radius_pt(1.25 if p["layer"].startswith("iso") else
                         0.17 * math.sqrt(3 + 1.5 * math.sqrt(p["size"])))) for p in pts])
        title_w = _font_length(b["spec"]["tag"], "Arial-BoldMT", fs)
        blocked = [(rx0, rx0 + title_w * 1.04 + 4.0, ry1 - 2.0 * fs, ry1)]   # annotate(hjust = -0.04, vjust = 1.4) top-left title
        cp = b["cpts"]; groups = b["all_groups"]
        texts = [b["short"].get(cp[g[0]]["strain"], cp[g[0]]["strain"]) + (f" x{len(g)}" if len(g) > 1 else "") for g in groups]
        # page labels are always names (FIGURE_HOUSE_RULES rule 6): no numbered labels in page mode, whatever the outlier count
        targets = [(tx(sum(cp[k]["x"] for k in g) / len(g)), ty(sum(cp[k]["y"] for k in g) / len(g)), point_radius_pt(1.25)) for g in groups]
        italic = bool(getattr(a, "italic_labels", False))   # species names in italic
        res = place_labels_pt(targets, texts, obst, (rx0, rx1, ry0, ry1), blocked, font_size=fs, italic=italic,
                              max_leader_pt=LEADER_MAX_IN * 72)
        dx_ = lambda X: xl0 + (X - rx0) / (rx1 - rx0) * (xl1 - xl0); dy_ = lambda Y: yl0 + (Y - ry0) / (ry1 - ry0) * (yl1 - yl0)
        placed.append([dict(rank=n, text=t, res=q, face="italic" if italic else "plain", x=dx_(q["anchor"][0]) if q else None, y=dy_(q["anchor"][1]) if q else None,
                            sx=dx_(q["seg"][0]) if q else None, sy=dy_(q["seg"][1]) if q else None)
                       for n, (t, q) in enumerate(zip(texts, res), 1)])
    # 3. final page through the full gate; the PDF is read back and a fault drops that panel's last placed label
    final_log = []
    for attempt in range(12):
        labs = [[dict(x=l["x"], y=l["y"], label=l["text"], hjust=l["res"]["hjust"], vjust=l["res"]["vjust"], sx=l["sx"], sy=l["sy"],
                      face=l["face"])
                 for l in pl if l["res"]] for pl in placed]
        pre, r, page = draw(labs, False)
        bad = set()
        if r.returncode != 0:
            msg = r.stderr.strip()[-600:]
            if "MIN_TEXT_DOES_NOT_FIT" not in msg:
                raise RenderRefusal(f"page renderer failed for {prefix.name}: {msg}")
            bad = {c for c, pl in enumerate(placed) if any(l["res"] and l["text"] in msg for l in pl)} or {c for c in range(P) if labs[c]}
            final_log.append(dict(labelled={lays[c]: len(labs[c]) for c in range(P)}, refused=msg[-300:]))
        else:
            try:
                _mt_enforce(f"{prefix}.pdf", a.min_text_pt)
            except RuntimeError as exc:
                raise RenderRefusal(str(exc)) from None
            f = _faults(f"{prefix}.pdf", P, LEADER_MAX_IN, LEADER_RGB)
            bad = {c for c, v in f.items() if v}
            final_log.append(dict(labelled={lays[c]: len(labs[c]) for c in range(P)}, faults={lays[c]: v[:8] for c, v in f.items() if v}))
            if not bad:
                break
        if not any(labs[c] for c in bad):
            raise RenderRefusal(f"MIN_TEXT_DOES_NOT_FIT: {prefix.name} fails with no labels left to drop: {final_log[-1]}")
        for c in bad:
            last = max((l for l in placed[c] if l["res"]), key=lambda l: l["rank"], default=None)
            if last:
                last["res"] = None; last["dropped"] = "PDF read-back fault"
    else:
        raise RenderRefusal(f"{prefix.name}: no passing page after 12 final draws: {final_log[-3:]}")
    assert_no_banned_figure_text(svg_visible_text(Path(f"{prefix}.svg").read_text()), figure_id=prefix.name)
    # Preserve native R rasters and vector masters; PDF previews are review-only.
    raster_artifacts = page_raster_artifacts(prefix, a.print_width)
    execution = page_execution_record(prefix, page["stamp"])
    names = ({r["strain"]: r["display"] for r in read_tsv(Path(a.label_names))} if getattr(a, "label_names", None) else {})
    label_schema = write_page_labels(out / f"LABELS_{s}_{name}_PAGE.tsv", lays, full, placed, genome_no, names, a.quantile)
    b0 = full[0]
    receipt = dict(set=s, panel=name, page=lays, stamp=page["stamp"], style="bee Fig. S9 print (render_pcoa_print.R values)", staged=".452",
                   label_rule=label_schema["label_rule"] + " (bee plot_pcoa.py lines 105-116; configured quantile)",
                   label_table_schema=label_schema,
                   placement=f"bee greedy placement (plot_pcoa.py place_labels, lines 62-65) in print points, leaders <= {LEADER_MAX_IN} in; "
                             "labels cover no point, label, leader or panel title",
                   labels={lay: dict(outlier_groups=n_out[c], outlier_points=sum(len(g) for g in full[c]["all_groups"]),
                                     labelled=sum(1 for l in placed[c] if l["res"]), threshold=full[c]["threshold"],
                                     numbered=False,
                                     longest_leader_in=max((l["res"]["leader_pt"] / 72 for l in placed[c] if l["res"]), default=0.0))
                           for c, lay in enumerate(lays)},
                   genome_numbers=genome_no, prefix=prefix.name, title=titles.get(s, (s, s, "proteins"))[0],
                   cohort_genomes={st: sum(1 for p in b0["cpts"] if p["strain"] == st) for st in dict.fromkeys(p["strain"] for p in b0["cpts"])},
                   n_ref_centroids=sum(1 for p in b0["spec"]["points"] if p["layer"] == "ref"),
                   n_mibig_centroids=sum(1 for p in b0["spec"]["points"] if p["layer"] == "mibig"),
                   approx_id=run.get("approx_id"), pct_axes=(run.get("pct_axes") or [None, None])[:2],
                   axis_metadata=b0["axis_metadata"], distance=run.get("distance"),
                   embedding=embedding_meta(emb_tables.get(s), lays, admitted),
                   leader_max_in=LEADER_MAX_IN, panel_rects_pt=rects, limits=lims, final_draws=final_log, n_reference_genomes=n_ref_genomes,
                   legend=legend, **b0["counts"], quantile=a.quantile, label_below=a.label_below, mid_below=a.mid_below,
                   min_text=page["min_text"], execution=execution,
                   artwork=dict(vector_masters=[prefix.name + ".pdf", prefix.name + ".svg"],
                                rasters=raster_artifacts, caption="SEPARATE_EDITABLE_MARKDOWN",
                                caption_band="NOT_GENERATED", publication_acceptance="NOT_ESTABLISHED"))
    (out / f"page_{s}_{name}.json").write_text(json.dumps(receipt, indent=1))
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit", required=True, help="folder with out_<SET>/PCOA_<SET>.tsv")
    ap.add_argument("--set", action="append", help="set id to draw (repeatable); default: every set in the kit")
    ap.add_argument("--out", required=True, help="new or empty output folder")
    ap.add_argument("--cohort-table", help="TSV with strain and cohort columns (required unless --source-style)")
    ap.add_argument("--panel", action="append", help="NAME=COHORT[,COHORT...] (repeatable; required unless --source-style)")
    ap.add_argument("--source-style", metavar="GENUS",
                    help="reference-only figure, no cohort (M5_452_pcoa_source_style): reference points as outlined circles in GENUS's "
                         "colour from mamey/data/genus_palette.json, drawn above MIBiG points as outlined triangles, legend boxed; R renderer only")
    ap.add_argument("--panel-label", action="append", default=[], help="NAME=legend text for the cohort points")
    ap.add_argument("--cohort-colour", action="append", default=[], help="NAME=#hex fill for a panel's points")
    ap.add_argument("--set-names", help="TSV: set, title (or amr_gene_family), optional tag and unit columns")
    ap.add_argument("--exclude-strain", action="append", help="strain not drawn (repeatable)")
    ap.add_argument("--drop-origins", help="file listing region files whose points are not drawn")
    ap.add_argument("--label-below", type=float, default=70.0)
    ap.add_argument("--mid-below", type=float, default=None,
                    help="three identity tiers: light fill from --label-below up to this value (for example 85); default two tiers")
    ap.add_argument("--top-strains", type=int, default=0, help="label up to N strains by name (0 = distance rule)")
    ap.add_argument("--quantile", type=float, default=0.95)
    ap.add_argument("--number-above", type=int, default=30)
    ap.add_argument("--renderer", choices=["auto", "r", "matplotlib"], default="auto")
    ap.add_argument("--layout", choices=["pcoa", "trimap", "tsne"], default="pcoa",
                    help="saved coordinates only: pcoa uses kit PC1/PC2; trimap/tsne use --embedding-table; no embedding fit is executed")
    ap.add_argument("--embedding-table", action="append", default=[], help="SET=TSV with id and TRIMAP1/TRIMAP2 or TSNE1/TSNE2 (layout trimap/tsne)")
    ap.add_argument("--label-names", help="TSV: strain, display (house rule 6 name) for the LABELS key table")
    ap.add_argument("--min-text-pt", type=float, default=None, help="floor for every text item at print size (enables the 8 pt gate)")
    ap.add_argument("--print-width", type=float, default=7.2, help="declared print width in inches for the min-text gate")
    ap.add_argument("--page", help="saved layouts side by side on one R page (e.g. pcoa,trimap); default 8 pt floor")
    ap.add_argument("--italic-labels", action="store_true", help="page mode: canvas labels in italic (species names)")
    ap.add_argument("--caption-note", help="page mode: one study-design sentence appended to the written caption (checked by caption_guard)")
    ap.add_argument("--reference-label", help="page mode: legend text for the grey reference points (e.g. reference genomes, n = 1,705 (cluster centroids; query genomes excluded))")
    ap.add_argument("--source-style-fill", metavar="HEX", default=None,
                    help="with --source-style: fill for the genus's reference points; default is the genus colour in "
                         "mamey/data/genus_palette.json")
    ap.add_argument("--mibig-fill", metavar="HEX", default=None,
                    help="with --source-style: fill for the MIBiG triangles (default #D9D9D9, pale grey); choose a colour far from the genus fill")
    ap.add_argument("--source-style-outline", metavar="HEX", default=None,
                    help="with --source-style: outline of the genus's points (default: the fill colour, i.e. no dark rim)")
    ap.add_argument("--mibig-outline", metavar="HEX", default=None,
                    help="with --source-style: outline of the MIBiG triangles (default #A6A6A6)")
    ap.add_argument("--require-axis-metadata", action="store_true",
                    help="require finite supplied axis annotations; does not verify their definition or fit execution")
    a = ap.parse_args(argv)
    if a.source_style:   # M5_452_pcoa_source_style
        if a.page or a.renderer == "matplotlib":
            ap.error("--source-style draws single panels with the R renderer (no --page, no --renderer matplotlib)")
        a.panel = a.panel or ["references=__no_cohort__"]
        pal = json.loads((_ROOT / "mamey" / "data" / "genus_palette.json").read_text())
        for flag, v in (("--source-style-fill", a.source_style_fill), ("--mibig-fill", a.mibig_fill),
                        ("--source-style-outline", a.source_style_outline), ("--mibig-outline", a.mibig_outline)):
            if v is not None and not re.fullmatch(r"#[0-9A-Fa-f]{6}", v):
                ap.error(f"{flag} needs a colour like #14325C, got {v!r}")
        if a.source_style_fill is None:
            a.source_style_fill = pal["default"].get(a.source_style, pal["fallback"])
        if a.mibig_fill is None:   # paper-ready default (owner ruling 15 Oct, Fig. 7 option F): pale grey MIBiG behind the genus
            a.mibig_fill = "#D9D9D9"
        a.source_style_outline = a.source_style_outline or a.source_style_fill   # no dark outline: black rims read as black dots
        a.mibig_outline = a.mibig_outline or "#A6A6A6"
    elif any(v is not None for v in (a.source_style_fill, a.mibig_fill, a.source_style_outline, a.mibig_outline)):
        ap.error("--source-style-fill, --mibig-fill, --source-style-outline and --mibig-outline apply only with --source-style")
    elif not a.cohort_table or not a.panel:
        ap.error("--cohort-table and --panel are required unless --source-style")
    if a.page and a.renderer == "matplotlib":
        ap.error("--page requires R; choose --renderer r or auto")
    if a.page:   # M5_452 P1b page defaults (bee Fig. S9 print): tiers 70/85 %, 8 pt floor, italic species labels; no hand knobs
        a.mid_below = 85.0 if a.mid_below is None else a.mid_below
        a.min_text_pt = a.min_text_pt or 8.0
        a.italic_labels = a.italic_labels or bool(a.label_names)
    if a.mid_below is not None and a.mid_below <= a.label_below:
        ap.error("--mid-below must be above --label-below")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        from tools.protein_pcoa_page_docs import label_selection_metadata
        try:
            label_selection_metadata(a.quantile)
        except ValueError as exc:
            raise RenderRefusal(str(exc)) from exc
        out = Path(a.out)
        kit = Path(a.kit)
        sets = a.set or sorted(p.stem[len("PCOA_"):] for p in kit.glob("out_*/PCOA_*.tsv"))
        if not sets:
            raise RenderRefusal(f"{kit}: no out_<SET>/PCOA_<SET>.tsv")
        admit_output_ids(sets, a.panel)
        if out.exists() and any(out.iterdir()):
            raise RenderRefusal(f"{out} is not empty; choose a new folder (delivered figures are never overwritten)")
        out.mkdir(parents=True, exist_ok=True)
        input_paths = [Path(a.cohort_table)] if a.cohort_table else []
        input_paths.extend(Path(p) for p in (a.drop_origins, a.set_names, a.label_names) if p)
        emb_tables = dict(x.split("=", 1) for x in a.embedding_table)
        if (a.layout != "pcoa" or (a.page and a.page != "pcoa")) and set(emb_tables) != set(sets):
            raise RenderRefusal("--layout trimap/tsne needs one --embedding-table per drawn --set")
        for embedding_table in emb_tables.values():
            input_paths.extend([Path(embedding_table), Path(embedding_table).with_suffix(".json")])
        for s in sets:
            directory = kit / f"out_{s}"
            input_paths.extend(directory / f"{prefix}_{s}.{suffix}" for prefix, suffix in
                               (("PCOA", "tsv"), ("NEAREST", "tsv"), ("RUN", "json")))
            if a.page:   # M5_452 P4: the legend states the reference genome count, read from the kit metadata
                if not (kit / f"{s}_META.tsv").is_file():
                    raise RenderRefusal(f"--page needs {kit / (s + '_META.tsv')} (the legend states the reference genome count)")
                input_paths.append(kit / f"{s}_META.tsv")
        # This inspected source is an input to definition provenance, not a fitter run.
        axis_source_path = _ROOT / "tools" / "protein_pcoa_ordinate.py"
        input_paths.append(axis_source_path)
        input_bindings = [file_binding(p) for p in input_paths]
        # Keep each supplied path tied to its original binding even if a symlink
        # is retargeted before consumption. The reader still checks its target.
        admitted = {path.absolute(): record for path, record in zip(input_paths, input_bindings)}
        runs = {}
        a._axis_metadata_by_set = {}
        for s in sets:
            run_path = kit / f"out_{s}" / f"RUN_{s}.json"
            try:
                metadata = read_bound_json(run_path, admitted[run_path.absolute()])
                if not isinstance(metadata, dict):
                    raise RenderRefusal(f"{run_path}: expected a metadata object")
                axis_metadata(metadata, required=a.require_axis_metadata)
                resource_chain = admit_resource_run(kit / f"out_{s}", s, metadata, admitted[run_path.absolute()],
                                   input_paths, input_bindings, admitted)
                source_binding = admitted[axis_source_path.absolute()]
                a._axis_metadata_by_set[s] = bound_axis_metadata(
                    metadata, admitted[(kit / f"out_{s}" / f"PCOA_{s}.tsv").absolute()],
                    source_binding, read_bound_bytes(axis_source_path, source_binding),
                    admitted[run_path.absolute()], bool(resource_chain))
                runs[s] = metadata
            except (ValueError, TypeError) as exc:
                raise RenderRefusal(f"{run_path}: invalid axis metadata: {exc}") from exc
        cohorts = {}
        if a.cohort_table:
            cohorts_path = Path(a.cohort_table)
            cohorts = {r["strain"]: r.get("cohort", "") for r in
                       read_tsv(cohorts_path, expected_binding=admitted[cohorts_path.absolute()])}
        titles = {k: (v, v, "proteins") for k, v in BEE_TITLES.items()} if a.page else {}   # M5_452 P6
        if a.set_names:
            names_path = Path(a.set_names)
            for r in read_tsv(names_path, expected_binding=admitted[names_path.absolute()]):
                t = r.get("title") or r.get("amr_gene_family") or r["set"]
                titles[r["set"]] = (t, r.get("tag") or t, r.get("unit") or "proteins")
        drop_origins = set()
        if a.drop_origins:
            drop_path = Path(a.drop_origins)
            raw = read_bound_bytes(drop_path, admitted[drop_path.absolute()])
            if raw is None:
                raise RenderRefusal(f"drop-origin input is missing: {drop_path}")
            with io.TextIOWrapper(io.BytesIO(raw)) as stream:
                drop_origins = {line.strip() for line in stream}
        labels = dict(x.split("=", 1) for x in a.panel_label)
        colours = dict(x.split("=", 1) for x in a.cohort_colour)
        a._rscript = discover_rscript() if a.renderer != "matplotlib" or a.page or a.source_style else None
        renderer = "r" if a.page or a.source_style else (a.renderer if a.renderer != "auto" else ("r" if a._rscript else "matplotlib"))
        if renderer == "r" and a._rscript is None:
            raise RenderRefusal("Rscript with required packages is unavailable; install/select the documented R profile")
        producer_paths = [Path(__file__), _ROOT / "mamey" / "figure_policy.py"]
        if renderer == "r":
            producer_paths.extend([R_SCRIPT, Path(a._rscript)])
        if a.page:
            producer_paths.extend(_ROOT / "tools" / name for name in (
                "protein_pcoa_page.R", "protein_pcoa_page_docs.py", "figure_render_qc.py", "caption_guard.py",
                "sapote_min_text.R", "sapote_pub_layout.R", "sapote_stamp_required.R", "sapote_figure_theme.R", "stamp_figure.py", "_min_text_check.py"))
        producer_bindings = [file_binding(p) for p in producer_paths]
        receipts = []
        for s in sets:
            f = kit / f"out_{s}" / f"PCOA_{s}.tsv"
            if not f.exists():
                raise RenderRefusal(f"{f} missing")
            rows = read_tsv(f, expected_binding=admitted[f.absolute()])
            nf = f.parent / f"NEAREST_{s}.tsv"
            nearest_binding = admitted[nf.absolute()]
            if nearest_binding["state"] == "PRESENT":
                near = {r["id"]: r.get("nearest_pident") for r in
                        read_tsv(nf, expected_binding=nearest_binding)}
            else:
                read_bound_bytes(nf, nearest_binding)
                near = {}
            run = runs[s]
            if a.page:
                mp = kit / f"{s}_META.tsv"
                receipts.append(build_page(a, s, rows, near, run, cohorts, emb_tables, admitted, colours, labels, titles, out,
                                           drop_origins, read_tsv(mp, expected_binding=admitted[mp.absolute()])))
                continue
            if a.layout != "pcoa":
                ep = Path(emb_tables[s]); key = "TRIMAP" if a.layout == "trimap" else "TSNE"
                rows = embedding_coordinates(ep, rows, key, admitted[ep.absolute()])
            for i, spec in enumerate(a.panel):
                name, cs = spec.split("=", 1)
                receipts.append(build_panel(a, s, rows, near, run, cohorts, name, set(cs.split(",")),
                                            colours.get(name, PALETTE[i % len(PALETTE)]), labels.get(name, f"{name} isolates"),
                                            titles, out, renderer, drop_origins=drop_origins))
        if input_bindings != [file_binding(p) for p in input_paths]:
            raise RenderRefusal("render inputs changed during drawing; retain outputs as an incomplete attempt")
        if producer_bindings != [file_binding(p) for p in producer_paths]:
            raise RenderRefusal("renderer source changed during drawing; retain outputs as an incomplete attempt")
        outputs = [file_binding(p) for p in sorted(out.iterdir()) if p.is_file()]
        runtime = render_runtime(renderer, a._rscript)
        page_executions = [rec["execution"] for rec in receipts if rec.get("execution")]
        if a.page and page_executions:
            runtime["r_runtime"] = dict(state="PER_PAGE_IN_RUN_RECORDS", pages=[x["r_runtime"] for x in page_executions])
            runtime["fonts"] = dict(state="OBSERVED_FINAL_PDFS", pages=[x["fonts"] for x in page_executions])
        render = dict(args={k: v for k, v in vars(a).items() if k != "_axis_metadata_by_set"}, renderer=renderer, panels=receipts,
            inputs=input_bindings, outputs=outputs, producers=producer_bindings,
            replay_mode="SAVED_COORDINATE_REPLAY", historical_producers={s: historical_producer(runs[s]) for s in sets},
            rendering_runtime=runtime, artifact_schema="sapote-mamey.render-packet.v1",
            artifact_root=str(out.resolve()))
        if a.page:   # M5_452 P5: documents written from the receipts, then the bundle text and render checks; any finding refuses
            from tools.protein_pcoa_page_docs import write_page_docs, check_page_docs
            names_path = Path(a.label_names) if a.label_names else None
            names = ({r["strain"]: r["display"] for r in
                      read_tsv(names_path, expected_binding=admitted[names_path.absolute()])} if names_path else {})
            stamp_date = subprocess.run(["date", "-u", "+%Y-%m-%d %H:%M:%SZ"], capture_output=True, text=True).stdout.strip()
            page_docs = []
            for rec in receipts:
                mp = kit / f"{rec['set']}_META.tsv"
                docs = write_page_docs(out, rec, render, read_tsv(mp, expected_binding=admitted[mp.absolute()]), names, a.caption_note, stamp_date)
                page_docs.append(docs)
            qc = check_page_docs(out, _ROOT, page_docs)
            if qc["caption_guard"] or qc["figure_render_qc_exit"] != 0 or "errors 0," not in qc["figure_render_qc"]:
                raise RenderRefusal(f"page documents failed the bundle checks: {json.dumps(qc)[:500]}")
        # A completion receipt covers the companion/QC phase as well as drawing.
        # Failed attempts retain partial files but never receive this final receipt.
        if input_bindings != [file_binding(p) for p in input_paths]:
            raise RenderRefusal("render inputs changed during finalization; retain outputs as an incomplete attempt")
        if producer_bindings != [file_binding(p) for p in producer_paths]:
            raise RenderRefusal("renderer source changed during finalization; retain outputs as an incomplete attempt")
        if outputs != [file_binding(Path(record["path"])) for record in outputs]:
            raise RenderRefusal("drawn artifacts changed during finalization; retain outputs as an incomplete attempt")
        render["outputs"] = [dict(file_binding(p), relative_path=p.relative_to(out).as_posix())
                             for p in sorted(out.rglob("*")) if p.is_file()]
        render["completion_state"] = "COMPLETE"
        (out / "render_receipt.json").write_text(json.dumps(render, indent=1))
    except (RenderRefusal, FigureTextRefusal) as exc:
        _LOG.error("REFUSED: %s", exc)
        return 2
    _LOG.info("%d panels drawn with %s", len(receipts), renderer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
