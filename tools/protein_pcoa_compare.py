#!/usr/bin/env python3
"""Compare cohort collections on a protein PCoA kit, with statistics, dot plots and resistance-family carriage.

Reads a kit written by tools/protein_pcoa_ordinate.py (out_<SET>/PCOA_<SET>.tsv, NEAREST_<SET>.tsv, RUN_<SET>.json) and a
cohort table, and writes to --out (new or empty; never inside the bundle):
- STATS.tsv: one row per set. Per collection: proteins, genomes, median identity to the closest reference/MIBiG protein,
  and the number and share below --cut. Tests:
  - genome level (primary): one median identity per genome, Kruskal-Wallis across collections with >= 3 genomes.
    Proteins of one genome are not independent, so this is the test to quote;
  - protein level (secondary): Kruskal-Wallis, and pairwise two-sided Mann-Whitney;
  - share below --cut: chi-square on the collection x (below, not below) table, or a permutation of the chi-square
    statistic (--permutations draws, fixed seed) when any cell is under 5;
  - Benjamini-Hochberg q values across the selected sets for the genome-level, protein-level and share tests. The pairwise
    Mann-Whitney values are raw (column suffix _p_raw), exploratory and not corrected.
- SHARE_BELOW_<cut>.png/.pdf: one row per set, one dot per collection (size = proteins); * marks genome-level q < 0.05.
- IDENTITY_DOTPLOTS.png/.pdf: identity by collection for every set, with medians.
- BY_COLLECTION_<SET>.png/.pdf (--by-collection SET, repeatable): one panel per collection on the shared reference and
  MIBiG cloud, PC1 against PC2.
- CARRIAGE.tsv, CARRIAGE_PER_GENOME.tsv and CARRIAGE.png/.pdf for sets whose name starts with --carriage-prefix (default
  RES): the share of genomes carrying each set by collection (permutation chi-square), and per genome the number of
  proteins in those sets. With --region-kb (strain -> kb of antiSMASH region), density per 100 kb is the primary per-genome
  measure and the raw count is kept beside it.
- SOURCES.tsv (inputs with sha256, strains left out, genus disagreements) and CAPTION.md (wording for captions; none of it
  is drawn on the figures).

Cohort table (TSV): `strain` and `collection` columns; optional `genus` (wins over the kit's genus column, and every
disagreement is listed), `color` (hex, per collection) and `order` (collection order). Isolate points of strains not in
the table are left out and listed. A strain listed twice with two collections is refused. A collection's denominator is
its strains with at least one protein in ANY set of the kit, built before --sets narrows the analysis, so selecting one
set never shrinks it; DENOMINATOR.tsv lists the members, the scope and the strains left out, and SOURCES.tsv hashes it.
An identity value that is not a finite number from 0 to 100 is refused, never classified.

Display rule: a point without an identity value (SID-type public collections, references, MIBiG) is never drawn with
the filled/open identity code. Collection points with a value are filled below --cut and open at or above it.

Requires SciPy and matplotlib; a missing one is refused by name, never replaced.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import logging
import json
import sys
from pathlib import Path

try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from mamey.path_safety import assert_output_outside_bundle  # noqa: E402

from mamey.logging_setup import get_logger as _get_logger

_OUT = _get_logger(__name__)

DEFAULT_COLORS = ["#C9A227", "#2E7D4F", "#8C4A2F", "#4F6D8F", "#6B4E9B", "#A3B86C", "#C49A6C"]
REF_COLOR, MIBIG_COLOR, SID_COLOR, INK, MUTED = "#C9CDD3", "#7FA3C7", "#B0487A", "#17212E", "#6B778A"
CAPTION = """# Caption notes

- Identity is DIAMOND amino-acid identity to the closest reference, SID or MIBiG protein of the same set; cohort proteins
  are not compared with each other. Positions and identities are sequence similarity.
- Genome-level tests use one median per genome. Protein-level results are reported but proteins of one genome are not
  independent.
- A match to a CARD family is similarity to a resistance protein; it does not show that a strain is resistant.
- Points without identity values (public collections, MIBiG) carry no identity code.
"""


class CompareRefusal(RuntimeError):
    """A precondition failed; the message names it."""


def _need(module: str):
    try:
        return __import__(module)
    except ImportError as exc:
        raise CompareRefusal(f"MISSING_DEPENDENCY: {module} is required ({exc}); install it, nothing is replaced") from exc


def _identity(v, setname, pid):
    """A NEAREST identity: None when absent; a finite value in [0, 100]; anything else is refused."""
    if v in ("", None):
        return None
    try:
        x = float(v)
    except ValueError:
        raise CompareRefusal(f"BAD_IDENTITY: set {setname} point {pid} has nearest_pident {v!r}")
    if not (x == x) or x in (float("inf"), float("-inf")) or not 0 <= x <= 100:
        raise CompareRefusal(f"BAD_IDENTITY: set {setname} point {pid} has nearest_pident {v!r} (must be 0-100)")
    return x


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def bh(pvalues: list[float]) -> list[float]:
    """Benjamini-Hochberg adjusted q values; NaN inputs stay NaN and are not counted."""
    idx = [i for i, p in enumerate(pvalues) if p == p]
    q = [float("nan")] * len(pvalues)
    if not idx:
        return q
    order = sorted(idx, key=lambda i: pvalues[i])
    n = len(idx); running = 1.0
    for rank in range(n, 0, -1):
        i = order[rank - 1]
        running = min(running, pvalues[i] * n / rank)
        q[i] = min(running, 1.0)
    return q


def median(values):
    v = sorted(values); n = len(v)
    return float("nan") if not n else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


def identity_style(point: dict, cut: float) -> str:
    """'below', 'at_or_above', or 'none' (no identity value: never drawn with the identity code)."""
    v = point.get("identity")
    if v is None:
        return "none"
    return "below" if v < cut else "at_or_above"


def chi2_or_permutation(table, permutations: int, seed: int = 1) -> float:
    """P value for a k x 2 table: chi-square when every cell is >= 5, else a permutation of the chi-square statistic."""
    np = _need("numpy")
    from scipy import stats
    t = np.asarray(table, dtype=float)
    t = t[t.sum(axis=1) > 0]
    if len(t) < 2 or t[:, 0].sum() in (0, t.sum()):
        return float("nan")
    if t.min() >= 5:
        return float(stats.chi2_contingency(t).pvalue)
    labels = np.repeat(np.arange(len(t)), t.sum(axis=1).astype(int))
    has = np.concatenate([[1] * int(a) + [0] * int(b) for a, b in t])

    def chi(lab):
        obs = np.array([[has[lab == j].sum(), (1 - has[lab == j]).sum()] for j in range(len(t))], dtype=float)
        exp = obs.sum(1, keepdims=True) * obs.sum(0, keepdims=True) / obs.sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            return float(np.nansum(np.where(exp > 0, (obs - exp) ** 2 / exp, 0)))
    observed = chi(labels); rng = np.random.default_rng(seed)
    hits = sum(chi(rng.permutation(labels)) >= observed - 1e-12 for _ in range(permutations))
    return (1 + hits) / (1 + permutations)


def load_cohort(path: Path):
    rows = read_tsv(path)
    if not rows or not {"strain", "collection"} <= set(rows[0]):
        raise CompareRefusal(f"COHORT_TABLE: {path} needs 'strain' and 'collection' columns")
    of = {}
    for r in rows:
        prev = of.get(r["strain"])
        if prev is not None and prev != r["collection"]:
            raise CompareRefusal(f"COHORT_CONFLICT: {r['strain']} is listed under {prev} and {r['collection']}")
        of[r["strain"]] = r["collection"]
    genus = {r["strain"]: r["genus"] for r in rows if r.get("genus")}
    order = {}
    for r in rows:
        key = r["collection"]
        if key not in order:
            order[key] = (float(r["order"]) if r.get("order") else len(order), r.get("color") or "")
    cols = sorted(order, key=lambda k: order[k][0])
    colors = {k: order[k][1] or DEFAULT_COLORS[i % len(DEFAULT_COLORS)] for i, k in enumerate(cols)}
    return of, genus, cols, colors


def kit_tables(kit: Path) -> dict[str, Path]:
    """Canonical tables shared by loading, denominator membership and provenance."""
    return {p.name[4:]: p / f"PCOA_{p.name[4:]}.tsv"
            for p in sorted(kit.glob("out_*"))
            if (p / f"PCOA_{p.name[4:]}.tsv").is_file()}


def cohort_roster(kit: Path, of: dict):
    """Cohort strains with at least one isolate point in ANY set of the kit, independent of --sets."""
    present, per_set = set(), {}
    for pf in kit_tables(kit).values():
        seen = {r["strain"] for r in read_tsv(pf) if r.get("source") == "isolate" and r.get("strain") in of}
        per_set[pf.parent.name[4:]] = seen; present |= seen
    return present, per_set


def load_kit(kit: Path, of: dict, genus_override: dict, sets: list[str] | None):
    found = list(kit_tables(kit))
    if sets:
        missing = [s for s in sets if s not in found]
        if missing:
            raise CompareRefusal(f"SET_NOT_IN_KIT: {missing}")
        found = sets
    if not found:
        raise CompareRefusal(f"EMPTY_KIT: no out_<SET>/PCOA_<SET>.tsv under {kit}")
    data, files, left_out, disagreements = {}, [], set(), {}
    for s in found:
        pf = kit / f"out_{s}" / f"PCOA_{s}.tsv"; nf = kit / f"out_{s}" / f"NEAREST_{s}.tsv"; rf = kit / f"out_{s}" / f"RUN_{s}.json"
        files.append(pf)
        near = {}
        if nf.exists():
            files.append(nf)
            near = {r["id"]: r for r in read_tsv(nf)}
        run = {}
        if rf.exists():
            files.append(rf); run = json.loads(rf.read_text())
        pts = {"cohort": [], "sid": [], "reference": [], "mibig": []}
        for r in read_tsv(pf):
            p = {"id": r["id"], "x": float(r["PC1"]), "y": float(r["PC2"]), "z": float(r.get("PC3") or 0), "strain": r["strain"],
                 "genus": r.get("genus", "")}
            src = r["source"]
            if src == "isolate":
                if r["strain"] not in of:
                    left_out.add(r["strain"]); continue
                g = genus_override.get(r["strain"])
                if g and g != p["genus"]:
                    disagreements[r["strain"]] = (p["genus"], g)
                    p["genus"] = g
                v = near.get(r["id"], {}).get("nearest_pident", "")
                p["identity"] = _identity(v, s, r["id"])
                p["collection"] = of[r["strain"]]
                pts["cohort"].append(p)
            elif src == "MIBiG":
                pts["mibig"].append(p)
            elif src.startswith("SID"):
                pts["sid"].append(p)
            else:
                pts["reference"].append(p)
        data[s] = {"points": pts, "pct": run.get("pct_axes", [float("nan")] * 3)}
    return data, files, sorted(left_out), disagreements


def set_stats(data, cols, cut, permutations):
    from scipy import stats
    rows = []
    for s, d in data.items():
        cohort = [p for p in d["points"]["cohort"] if p["identity"] is not None]
        row = {"set": s}
        vals, gmed = {}, {}
        for k in cols:
            v = [p["identity"] for p in cohort if p["collection"] == k]
            per = {}
            for p in cohort:
                if p["collection"] == k:
                    per.setdefault(p["strain"], []).append(p["identity"])
            vals[k] = v; gmed[k] = [median(x) for x in per.values()]
            row[f"{k}_proteins"] = len(v); row[f"{k}_genomes"] = len(per)
            row[f"{k}_median_identity"] = round(median(v), 2) if v else ""
            row[f"{k}_below"] = sum(x < cut for x in v)
            row[f"{k}_share_below"] = round(row[f"{k}_below"] / len(v), 4) if v else ""
        ok_g = [k for k in cols if len(gmed[k]) >= 3]
        row["genome_test_collections"] = ",".join(ok_g)
        row["genome_KW_p"] = float(stats.kruskal(*[gmed[k] for k in ok_g]).pvalue) if len(ok_g) >= 2 else float("nan")
        ok_p = [k for k in cols if len(vals[k]) >= 3]
        row["protein_KW_p"] = float(stats.kruskal(*[vals[k] for k in ok_p]).pvalue) if len(ok_p) >= 2 else float("nan")
        for a, b in itertools.combinations(cols, 2):
            row[f"protein_MW_{a}_vs_{b}_p_raw"] = (float(stats.mannwhitneyu(vals[a], vals[b], alternative="two-sided").pvalue)
                                              if len(vals[a]) >= 3 and len(vals[b]) >= 3 else float("nan"))
        row["share_p"] = chi2_or_permutation([[row[f"{k}_below"], row[f"{k}_proteins"] - row[f"{k}_below"]] for k in cols],
                                             permutations)
        rows.append(row)
    for col in ("genome_KW_p", "protein_KW_p", "share_p"):
        for r, q in zip(rows, bh([r[col] for r in rows])):
            r[col[:-2] + "_q"] = q
    return rows


def carriage(data, cols, prefix, genomes, region_kb, permutations):
    from scipy import stats
    sets = [s for s in data if s.startswith(prefix)]
    if not sets:
        return [], [], {}
    counts = {s: {} for s in sets}
    for s in sets:
        for p in data[s]["points"]["cohort"]:
            counts[s][p["strain"]] = counts[s].get(p["strain"], 0) + 1
    rows = []
    for s in sets:
        row = {"set": s}; table = []
        for k in cols:
            g = genomes[k]; a = sum(1 for x in g if x in counts[s])
            row[f"{k}_genomes_carrying"] = f"{a}/{len(g)}"; row[f"{k}_share"] = round(a / len(g), 4) if g else ""
            table.append([a, len(g) - a])
        row["carriage_p"] = chi2_or_permutation(table, permutations)
        rows.append(row)
    for r, q in zip(rows, bh([r["carriage_p"] for r in rows])):
        r["carriage_q"] = q
    per_genome = []
    raw, dens = {k: [] for k in cols}, {k: [] for k in cols}
    for k in cols:
        for x in genomes[k]:
            n = sum(counts[s].get(x, 0) for s in sets)
            kb = region_kb.get(x)
            d = n / kb * 100 if kb else None
            per_genome.append({"collection": k, "strain": x, "proteins": n, "region_kb": kb if kb else "",
                               "per_100kb_region": round(d, 4) if d is not None else ""})
            raw[k].append(n)
            if d is not None:
                dens[k].append(d)
    tests = {}
    for name, vals in (("density", dens), ("raw", raw)):
        ok = [k for k in cols if len(vals[k]) >= 3]
        if len(ok) < 2:
            continue
        tests[name] = {"kw_p": float(stats.kruskal(*[vals[k] for k in ok]).pvalue), "medians": {k: median(vals[k]) for k in ok},
                       "values": vals}
    return rows, per_genome, tests


def write_tsv(path: Path, rows: list[dict]):
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow({k: (("" if v != v else f"{v:.4g}") if isinstance(v, float) and (k.endswith("_p") or k.endswith("_q") or k.endswith("_p_raw")) else v)
                        for k, v in r.items()})


def figures(out, data, rows, cols, colors, cut, by_collection, carr, plt):
    np = _need("numpy")
    from mamey.figure_policy import assert_no_banned_figure_text
    texts = []

    def save(fig, name):
        assert_no_banned_figure_text(texts, figure_id=name)
        fig.savefig(out / f"{name}.png", dpi=400, facecolor="white"); fig.savefig(out / f"{name}.pdf", facecolor="white")
        plt.close(fig); texts.clear()

    # share below cut, one row per set
    fig, ax = plt.subplots(figsize=(6.4, 0.26 * len(rows) + 1.4))
    labels = []
    for i, r in enumerate(rows):
        y = len(rows) - 1 - i
        xs = [r[f"{k}_share_below"] * 100 for k in cols if r[f"{k}_share_below"] != ""]
        if xs:
            ax.plot([min(xs), max(xs)], [y, y], color=REF_COLOR, lw=1, zorder=1)
        for k in cols:
            v = r[f"{k}_share_below"]
            if v != "":
                ax.scatter(v * 100, y, s=12 + 1.2 * min(r[f"{k}_proteins"], 120), color=colors[k], edgecolor=INK, lw=0.4, zorder=3)
        q = r.get("genome_KW_q", float("nan"))
        labels.append(f"{r['set']}{' *' if q == q and q < 0.05 else ''}  (n {'/'.join(str(r[f'{k}_proteins']) for k in cols)})")
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(labels[::-1], fontsize=6.2)
    ax.set_xlim(-2, 102); ax.set_xlabel(f"Proteins whose closest reference or MIBiG protein is below {cut:g}% identity (%)", fontsize=7)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend([plt.Line2D([], [], ls="", marker="o", ms=6, mfc=colors[k], mec=INK, mew=0.4) for k in cols], cols, fontsize=6.5,
              frameon=False, loc="lower right")
    texts += labels + cols
    fig.tight_layout(); save(fig, f"SHARE_BELOW_{cut:g}")

    # identity dot plots
    sets = list(data); ncol = 4; nrow = max(1, -(-len(sets) // ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(7.2, 1.55 * nrow + 0.6), sharey=True, squeeze=False)
    rng = np.random.default_rng(7)
    for ax, s in zip(axs.flat, sets):
        r = next(x for x in rows if x["set"] == s)
        for i, k in enumerate(cols):
            v = [p["identity"] for p in data[s]["points"]["cohort"] if p["collection"] == k and p["identity"] is not None]
            if v:
                ax.scatter(i + rng.uniform(-0.25, 0.25, len(v)), v, s=3.5, color=colors[k], lw=0, alpha=0.75)
                ax.plot([i - 0.32, i + 0.32], [median(v)] * 2, color=INK, lw=1.3)
        ax.axhline(cut, ls=(0, (2, 2)), lw=0.6, color=MUTED)
        q = r.get("genome_KW_q", float("nan"))
        ax.set_title(f"{s}\n" + (f"genome-level q = {q:.2g}" if q == q else "too few genomes to test"), fontsize=5.8, loc="left")
        ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, fontsize=5.2, rotation=0)
        ax.tick_params(axis="y", labelsize=5.4)
        texts += [s] + cols
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    for ax in list(axs.flat)[len(sets):]:
        ax.axis("off")
    fig.subplots_adjust(left=0.07, right=0.99, top=0.95, bottom=0.05, hspace=0.75, wspace=0.12)
    save(fig, "IDENTITY_DOTPLOTS")

    # one panel per collection
    for s in by_collection:
        pts = data[s]["points"]; pct = data[s]["pct"]
        panels = cols + (["public collection (SID)"] if pts["sid"] else [])
        n = len(panels); ncol = 2; nrow = -(-n // ncol)
        fig, axs = plt.subplots(nrow, ncol, figsize=(7.2, 3.3 * nrow + 0.6), sharex=True, sharey=True, squeeze=False)
        for ax, k in zip(axs.flat, panels):
            ax.scatter([p["x"] for p in pts["reference"]], [p["y"] for p in pts["reference"]], s=1.2, color=REF_COLOR, lw=0, rasterized=True)
            ax.scatter([p["x"] for p in pts["mibig"]], [p["y"] for p in pts["mibig"]], s=1.4, color=MIBIG_COLOR, lw=0, rasterized=True)
            if k in colors:
                c = [p for p in pts["cohort"] if p["collection"] == k]
                st = {sty: [p for p in c if identity_style(p, cut) == sty] for sty in ("below", "at_or_above", "none")}
                ax.scatter([p["x"] for p in st["at_or_above"]], [p["y"] for p in st["at_or_above"]], s=11, facecolor="white", edgecolor=colors[k], lw=0.7)
                ax.scatter([p["x"] for p in st["below"]], [p["y"] for p in st["below"]], s=11, facecolor=colors[k], edgecolor=INK, lw=0.3)
                ax.scatter([p["x"] for p in st["none"]], [p["y"] for p in st["none"]], s=10, marker="D", facecolor="none", edgecolor=colors[k], lw=0.6)
                title = f"{k}: {len(c)} proteins from {len({p['strain'] for p in c})} genomes, {len(st['below'])} below {cut:g}%"
            else:
                ax.scatter([p["x"] for p in pts["sid"]], [p["y"] for p in pts["sid"]], s=10, marker="D", facecolor="none", edgecolor=SID_COLOR, lw=0.6)
                title = f"{k}: {len(pts['sid'])} cluster centroids"
            ax.set_title(title, fontsize=7, loc="left"); texts.append(title)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            ax.tick_params(labelsize=6)
        for ax in list(axs.flat)[n:]:
            ax.axis("off")
        for ax in axs[-1]:
            ax.set_xlabel(f"PCoA 1 ({pct[0]:.1f}%)", fontsize=7)
        for ax in axs[:, 0]:
            ax.set_ylabel(f"PCoA 2 ({pct[1]:.1f}%)", fontsize=7)
        leg = [("public genomes (cluster centroids)", dict(marker="o", ms=3, mfc=REF_COLOR, mec="none")),
               ("MIBiG", dict(marker="o", ms=3, mfc=MIBIG_COLOR, mec="none")),
               (f"closest match below {cut:g}% identity", dict(marker="o", ms=4.5, mfc=MUTED, mec=INK, mew=0.4)),
               (f"closest match {cut:g}% or more", dict(marker="o", ms=4.5, mfc="white", mec=MUTED, mew=0.8)),
               ("no identity value", dict(marker="D", ms=3.8, mfc="none", mec=MUTED, mew=0.8))]
        fig.legend([plt.Line2D([], [], ls="", **kw) for _, kw in leg], [t for t, _ in leg], loc="lower center", ncol=3, fontsize=6.3, frameon=False)
        texts += [t for t, _ in leg]
        fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.10 + 0.02 * (2 - min(nrow, 2)), hspace=0.25, wspace=0.08)
        save(fig, f"BY_COLLECTION_{s}")

    # carriage
    crow, per_genome, tests = carr
    if crow:
        has_d = "density" in tests
        fig = plt.figure(figsize=(7.2, 0.3 * len(crow) + 1.6))
        A = fig.add_axes([0.13, 0.12, 0.42, 0.78])
        M = np.array([[r[f"{k}_share"] if r[f"{k}_share"] != "" else 0 for k in cols] for r in crow])
        A.imshow(M, cmap="Greys", vmin=0, vmax=1, aspect="auto")
        for i, r in enumerate(crow):
            for j, k in enumerate(cols):
                A.text(j, i, r[f"{k}_genomes_carrying"], ha="center", va="center", fontsize=5.6, color="white" if M[i, j] > 0.55 else INK)
        A.set_xticks(range(len(cols))); A.set_xticklabels(cols, fontsize=6.2); A.xaxis.tick_top()
        A.set_yticks(range(len(crow)))
        A.set_yticklabels([f"{r['set']}{' *' if r['carriage_q'] == r['carriage_q'] and r['carriage_q'] < 0.05 else ''}" for r in crow], fontsize=6)
        A.tick_params(length=0)
        for sp in A.spines.values():
            sp.set_visible(False)
        panels = (["density"] if has_d else []) + (["raw"] if "raw" in tests else [])
        rng = np.random.default_rng(7)
        for i, name in enumerate(panels):
            ax = fig.add_axes([0.66 + i * 0.20, 0.12, 0.12, 0.78])
            vals = tests[name]["values"]
            for j, k in enumerate(cols):
                v = vals[k]
                if v:
                    ax.scatter(j + rng.uniform(-0.18, 0.18, len(v)), v, s=10, color=colors[k], edgecolor="white", lw=0.3)
                    ax.plot([j - 0.26, j + 0.26], [median(v)] * 2, color=INK, lw=1.2)
            ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, fontsize=5, rotation=90); ax.tick_params(labelsize=5.6)
            ax.set_ylim(bottom=0)
            lab = "per 100 kb of region" if name == "density" else "proteins per genome (raw)"
            ax.set_ylabel(lab, fontsize=6); ax.set_title(f"{'Density' if name == 'density' else 'Raw count'}\np = {tests[name]['kw_p']:.2g}", fontsize=6, loc="left")
            texts.append(lab)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
        save(fig, "CARRIAGE")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit", required=True, type=Path, help="PCoA kit folder holding out_<SET>/")
    ap.add_argument("--cohort", required=True, type=Path, help="TSV: strain, collection[, genus, color, order]")
    ap.add_argument("--out", required=True, type=Path, help="output folder (new or empty)")
    ap.add_argument("--sets", nargs="*", help="sets to use (default: every set in the kit)")
    ap.add_argument("--cut", type=float, default=70.0, help="identity cut-off in percent (default 70)")
    ap.add_argument("--by-collection", action="append", default=[], help="draw per-collection panels for this set (repeatable)")
    ap.add_argument("--carriage-prefix", default="RES", help="sets compared by carriage (default RES)")
    ap.add_argument("--region-kb", type=Path, help="TSV: strain, region_kb (antiSMASH region length per genome) for density")
    ap.add_argument("--permutations", type=int, default=20000)
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args(argv)
    try:
        _need("scipy"); _need("numpy")
        out = assert_output_outside_bundle(a.out, __file__)
        if out.exists() and any(out.iterdir()):
            raise CompareRefusal(f"OUTPUT_NOT_EMPTY: {out}")
        out.mkdir(parents=True, exist_ok=True)
        of, genus, cols, colors = load_cohort(a.cohort)
        data, files, left_out, disagree = load_kit(a.kit, of, genus, a.sets)
        for s in a.by_collection:
            if s not in data:
                raise CompareRefusal(f"SET_NOT_IN_KIT: {s}")
        present, per_set = cohort_roster(a.kit, of)
        genomes = {k: sorted(x for x in present if of[x] == k) for k in cols}
        with open(out / "DENOMINATOR.tsv", "w", newline="") as fh:
            w = _SafeWriter(fh, delimiter="\t")
            w.writerow(["collection", "strain", "status", "scope"])
            for k in cols:
                for x in genomes[k]:
                    w.writerow([k, x, "member", f"present in {sum(x in v for v in per_set.values())} of {len(per_set)} kit sets"])
            for x in sorted(set(of) - present):
                w.writerow([of[x], x, "excluded", "in the cohort table but in no set of the kit"])
        region_kb = {}
        if a.region_kb:
            region_kb = {r["strain"]: float(r["region_kb"]) for r in read_tsv(a.region_kb) if r.get("region_kb")}
        rows = set_stats(data, cols, a.cut, a.permutations)
        write_tsv(out / "STATS.tsv", rows)
        carr = carriage(data, cols, a.carriage_prefix, genomes, region_kb, a.permutations)
        write_tsv(out / "CARRIAGE.tsv", carr[0]); write_tsv(out / "CARRIAGE_PER_GENOME.tsv", carr[1])
        if not a.no_figures:
            matplotlib = _need("matplotlib"); matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            figures(out, data, rows, cols, colors, a.cut, a.by_collection, carr, plt)
        (out / "CAPTION.md").write_text(CAPTION)
        with open(out / "SOURCES.tsv", "w", newline="") as fh:
            w = _SafeWriter(fh, delimiter="\t")
            w.writerow(["kind", "item", "detail"])
            for f in dict.fromkeys([a.cohort, *([a.region_kb] if a.region_kb else []),
                                    *files, *kit_tables(a.kit).values()]):
                w.writerow(["input", str(f), sha256(Path(f))])
            w.writerow(["output", "DENOMINATOR.tsv", sha256(out / "DENOMINATOR.tsv")])
            import platform, numpy, scipy
            w.writerow(["software", "python", platform.python_version()])
            w.writerow(["software", "numpy", numpy.__version__]); w.writerow(["software", "scipy", scipy.__version__])
            if not a.no_figures:
                w.writerow(["software", "matplotlib", matplotlib.__version__])
            w.writerow(["software", "tool_sha256", sha256(Path(__file__))])
            for k, v in sorted(vars(a).items()):
                w.writerow(["option", k, str(v)])
            for k in cols:
                w.writerow(["denominator", k, f"{len(genomes[k])} genomes"])
            for x in left_out:
                w.writerow(["left_out", x, "isolate points of a strain not in the cohort table"])
            for x, (kit_g, tab_g) in sorted(disagree.items()):
                w.writerow(["genus_disagreement", x, f"kit {kit_g}; cohort table {tab_g} (table used)"])
            for k in cols:
                for x in genomes[k]:
                    if a.region_kb and x not in region_kb:
                        w.writerow(["no_region_kb", x, "left out of density"])
        _OUT.info(f"[protein_pcoa_compare] {len(data)} sets, collections {', '.join(f'{k} ({len(genomes[k])})' for k in cols)} -> {out}")
        return 0
    except CompareRefusal as exc:
        # Refusals retain stderr and error severity, including when INFO progress is suppressed.
        refusal_log = _get_logger(__name__ + ".refusal")
        refusal_log.setLevel(logging.ERROR)
        refusal_log.propagate = False
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        refusal_log.addHandler(handler)
        try:
            refusal_log.error("[protein_pcoa_compare] REFUSED: %s", exc)
        finally:
            refusal_log.removeHandler(handler)
            handler.close()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
