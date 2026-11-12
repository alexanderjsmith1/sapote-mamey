#!/usr/bin/env python3
"""Three-collection sharing diagram for sequence-similarity groups (layout after Bragina et al. 2015, Fig. 4).

Input: a group-membership TSV with columns genus, threshold, floor, group_id, isolate, source_group and
no_eligible_comparison (True/False), one row per isolate per genus/threshold/floor. A collection map
(--collection-map, required) assigns each recorded source group to one of exactly three collections; the
tool holds no study's group names. For one genus, threshold and floor the tool counts, for each of the seven exclusive regions,
the groups whose members come from exactly that combination of collections and the isolates in those
groups, then draws three translucent circles with both counts in each region.

Isolates flagged no_eligible_comparison are excluded and listed, never counted as absent. A zero region is
drawn in grey and means no group of that kind among the isolates compared.

Outputs in --outdir: <stem>.png/.svg (bundle theme, manuscript profile), <stem>_plot_only.png, <stem>.pdf,
<stem>_CAPTION.md, <stem>_plotted.tsv (counts and group IDs per region) and <stem>_receipt.json (input and
output SHA-256). --check-table compares the counts with an existing table and stops on any difference.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

try:
    from mamey.figure_theme import PALETTE, apply_theme, save_figure_pair
except ImportError:  # run from tools/ without the package on the path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mamey.figure_theme import PALETTE, apply_theme, save_figure_pair

R = 1.6
CENTRES = [(-1.0, 0.6), (1.0, 0.6), (0.0, -1.1)]
FILL = ["teal", "gold", "coral"]
# label anchor for each region, keyed by which circles (0, 1, 2) contain it
ANCHORS = {(0,): (-1.85, 1.0), (1,): (1.85, 1.0), (2,): (0.0, -1.95), (0, 1): (0.0, 1.35),
           (0, 2): (-1.15, -0.6), (1, 2): (1.15, -0.6), (0, 1, 2): (0.0, 0.1)}
SET_LABELS = [(-2.75, 2.45, "right"), (2.75, 2.45, "left"), (0.0, -3.05, "center")]


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _inside(pt, centre) -> bool:
    return (pt[0] - centre[0]) ** 2 + (pt[1] - centre[1]) ** 2 < R ** 2


def anchors_ok() -> bool:
    """Each label anchor lies inside exactly the circles of its region."""
    return all(all(_inside(pt, CENTRES[i]) == (i in key) for i in range(3)) for key, pt in ANCHORS.items())


def read_table(data: bytes, required: tuple[str, ...], label: str) -> list[dict]:
    """Parse the same immutable bytes used for provenance, with unambiguous TSV keys."""
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), delimiter="\t", strict=True)
        fields = reader.fieldnames
        if not fields or any(not f or f != f.strip() for f in fields):
            raise SystemExit(f"{label}: missing or invalid column names")
        if len(fields) != len(set(fields)):
            raise SystemExit(f"{label}: duplicate column keys")
        if not set(required).issubset(fields):
            raise SystemExit(f"{label}: required columns missing: {sorted(set(required) - set(fields))}")
        rows = []
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise SystemExit(f"{label}: row {reader.line_num} has the wrong number of fields")
            rows.append(row)
        return rows
    except (UnicodeError, csv.Error) as exc:
        raise SystemExit(f"{label}: invalid UTF-8 TSV: {exc}") from exc


def load_map(path: Path, *, data: bytes | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in read_table(path.read_bytes() if data is None else data,
                        ("source_group", "collection"), "collection map"):
        k, v = r["source_group"].strip(), r["collection"].strip()
        if not k or not v:
            raise SystemExit(f"collection map has a blank source_group or collection: {r}")
        if any(c in k + v for c in "\r\n\t") or "|" in v:
            raise SystemExit("collection map contains a delimiter in a source_group or collection")
        if k in out:
            raise SystemExit(f"collection map lists source_group {k!r} more than once")
        out[k] = v
    return out


def collections_in_order(mapping: dict[str, str]) -> list[str]:
    seen: list[str] = []
    for c in mapping.values():
        if c not in seen:
            seen.append(c)
    if len(seen) != 3:
        raise SystemExit(f"the collection map must name exactly 3 collections; it names {len(seen)}: {seen}")
    return seen


def count_regions(rows: list[dict], mapping: dict[str, str]) -> dict:
    cols = collections_in_order(mapping)
    for r in rows:
        for field in ("isolate", "group_id"):
            value = r.get(field)
            if not isinstance(value, str) or not value.strip():
                raise SystemExit(f"blank isolate or group_id in membership row: {r}")
            if value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value) or (field == "group_id" and ";" in value):
                raise SystemExit(f"invalid {field}: surrounding whitespace, control character or list delimiter")
    unmapped = sorted({r["source_group"] for r in rows if r["source_group"] not in mapping})
    if unmapped:
        raise SystemExit(f"source groups with no collection: {unmapped}")
    seen = collections.Counter(r["isolate"] for r in rows)
    dups = sorted(i for i, n in seen.items() if n > 1)
    if dups:
        raise SystemExit(f"isolates listed more than once for this case: {dups}")
    for r in rows:
        if r["no_eligible_comparison"] not in ("True", "False"):
            raise SystemExit(f"no_eligible_comparison must be exactly True or False; got {r['no_eligible_comparison']!r} for {r.get('isolate')!r}")
        if not (r.get("isolate") or "").strip() or not (r.get("group_id") or "").strip():
            raise SystemExit(f"blank isolate or group_id in membership row: {r}")
    excluded = sorted(r["isolate"] for r in rows if r["no_eligible_comparison"] == "True")
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        if r["no_eligible_comparison"] == "False":
            groups[r["group_id"]].append(r)
    regions = {k: {"groups": 0, "isolates": 0, "group_ids": []} for k in ANCHORS}
    per_collection = collections.Counter({c: 0 for c in cols})
    for gid in sorted(groups):
        members = groups[gid]
        present = {mapping[m["source_group"]] for m in members}
        key = tuple(i for i, c in enumerate(cols) if c in present)
        regions[key]["groups"] += 1
        regions[key]["isolates"] += len(members)
        regions[key]["group_ids"].append(gid)
        for m in members:
            per_collection[mapping[m["source_group"]]] += 1
    return {"collections": cols, "regions": regions, "per_collection": dict(per_collection),
            "excluded": excluded, "groups": len(groups), "isolates": sum(len(m) for m in groups.values())}


def italic(name: str) -> str:
    """A genus name in italics for matplotlib text (mathtext; spaces kept)."""
    return "$\\it{" + name.replace(" ", "\\ ") + "}$"


def reading_key(genus: str, threshold: str, linkage: str) -> str:
    """The reading key drawn under the circles: what a circle, a group and a number mean. No interpretation."""
    return ("How to read it\n"
            "Each circle is one collection. Where circles overlap, a group has members from each of those collections.\n"
            "A group is a set of " + italic(genus) + f" isolates whose 16S rRNA genes are at least {threshold}% identical ({linkage} linkage).\n"
            "Each region gives the number of groups found in exactly those collections, and the isolates in them.\n"
            "A gray 0 means no group of that kind. Groups are not species.")


def draw(result: dict, stem: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    if not anchors_ok():
        raise SystemExit("internal layout error: a label anchor is outside its region")
    apply_theme(plt, "manuscript")
    fig, ax = plt.subplots(figsize=(9.2, 9.0))  # tight crop leaves about 7.2 in wide, so 300 dpi holds at print width; the extra height holds the reading key
    for i, centre in enumerate(CENTRES):
        ax.add_patch(Circle(centre, R, facecolor=PALETTE[FILL[i]], alpha=0.30,
                            edgecolor=PALETTE["navy"], linewidth=1.0))
    for key, (x, y) in ANCHORS.items():
        g, n = result["regions"][key]["groups"], result["regions"][key]["isolates"]
        ax.text(x, y, f"{g} group{'' if g == 1 else 's'}\n{n} isolate{'' if n == 1 else 's'}", ha="center",
                va="center", fontsize=9, linespacing=1.25, color=PALETTE["ink"] if g else PALETTE["muted"])
    for i, name in enumerate(result["collections"]):
        x, y, ha = SET_LABELS[i]
        ax.text(x, y, f"{name}\n{result['per_collection'][name]} isolates", ha=ha, va="center", fontsize=10,
                fontweight="bold", linespacing=1.3, color=PALETTE["navy"])
    reading = result.get("reading_key", "")   # set by main(); a caller without it gets no key box
    if reading:
        ax.text(-4.4, -3.75, reading, ha="left", va="top", fontsize=8.5, linespacing=1.45, color=PALETTE["ink"],
                bbox=dict(boxstyle="round,pad=0.5", facecolor=PALETTE["white"], edgecolor=PALETTE["grid"], linewidth=0.8))
    ax.set_xlim(-4.6, 4.6)
    ax.set_ylim(-5.0, 3.0)
    ax.set_aspect("equal")
    ax.axis("off")
    png, svg = save_figure_pair(fig, stem, profile="manuscript")
    pdf = stem.with_suffix(".pdf")
    fig.savefig(pdf, bbox_inches="tight", metadata={"Creator": "Sapote-Mamey governed figure theme"})
    plot_only = stem.parent / f"{stem.name}_plot_only.png"
    shutil.copyfile(png, plot_only)  # the figure carries no caption band, so the plot-only image is the figure
    plt.close(fig)
    return [png, svg, pdf, plot_only]


def caption(result: dict, genus: str, threshold: str, floor: str, linkage: str) -> str:
    c = result["collections"]
    parts = ", ".join(f"{name} {result['per_collection'][name]}" for name in c)
    exc = result["excluded"]
    exc_text = (f" {len(exc)} further isolate{'' if len(exc) == 1 else 's'} ({', '.join(exc)}) had no comparison "
                f"passing the overlap floor and {'is' if len(exc) == 1 else 'are'} not counted." if exc else "")
    return (f"Which {genus} 16S rRNA gene similarity groups occur in one collection only, and which are shared between "
            f"collections. Cultured isolates from three recorded source collections were grouped within the genus by {linkage} linkage at {threshold}% identity over at "
            f"least {floor} compared alignment columns. Each circle is one collection ({', '.join(c)}). Each region gives "
            f"the number of groups whose members come from exactly that combination of collections, and the number of "
            f"isolates in those groups; isolates in a shared region are counted in full, not as cross-collection pairs. "
            f"Totals: {result['groups']} groups and {result['isolates']} comparable isolates ({parts}).{exc_text} A zero "
            f"means no group of that kind among the isolates compared. Groups are sequence-similarity groups, "
            f"not species. Layout after Bragina, Berg and Berg (2015, Fig. 4; doi:10.1111/mec.13342).\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--membership", required=True, type=Path)
    ap.add_argument("--membership-sha256", help="stop unless the membership file has this SHA-256")
    ap.add_argument("--genus", required=True)
    ap.add_argument("--threshold", required=True)
    ap.add_argument("--floor", required=True)
    ap.add_argument("--linkage", default="complete", help="grouping rule named in the caption")
    ap.add_argument("--collection-map", type=Path, required=True, help="TSV with source_group and collection (3 collections)")
    ap.add_argument("--check-table", type=Path, help="TSV with combination, sequence_groups, isolates_in_those_groups")
    ap.add_argument("--outdir", required=True, type=Path)
    a = ap.parse_args(argv)
    # Read each source exactly once. Hash and parse these snapshots, never reopen a
    # changing path to claim provenance for bytes different from those consumed.
    membership_bytes = a.membership.read_bytes()
    map_bytes = a.collection_map.read_bytes()
    check_bytes = a.check_table.read_bytes() if a.check_table else None
    membership_sha = hashlib.sha256(membership_bytes).hexdigest()
    if a.membership_sha256 and membership_sha != a.membership_sha256:
        raise SystemExit("membership SHA-256 differs from --membership-sha256; stopping")
    map_sha = hashlib.sha256(map_bytes).hexdigest()
    check_sha = hashlib.sha256(check_bytes).hexdigest() if check_bytes is not None else None
    rows = [r for r in read_table(membership_bytes,
             ("genus", "threshold", "floor", "group_id", "isolate", "source_group", "no_eligible_comparison"), "membership")
            if r["genus"] == a.genus and r["threshold"] == a.threshold and r["floor"] == a.floor]
    if not rows:
        raise SystemExit(f"no membership rows for {a.genus} at {a.threshold}% and floor {a.floor}")
    mapping = load_map(a.collection_map, data=map_bytes)
    result = count_regions(rows, mapping)
    if result["isolates"] == 0:
        raise SystemExit("no comparable isolates for this case; nothing to draw (this is not a biological zero)")
    if a.check_table:
        cols = result["collections"]
        bad, seen = [], set()
        for r in read_table(check_bytes, ("combination", "sequence_groups", "isolates_in_those_groups"), "check table"):
            names = [x.strip() for x in r["combination"].split("|")]
            if any(n not in cols for n in names):
                raise SystemExit(f"check table names an unknown collection: {r['combination']!r}")
            if len(names) != len(set(names)):
                raise SystemExit(f"check table repeats a collection within a combination: {r['combination']!r}")
            key = tuple(sorted(cols.index(n) for n in names))
            if key in seen:
                raise SystemExit(f"check table lists {r['combination']!r} more than once")
            seen.add(key)
            got = result["regions"][key]
            try:
                counts = (int(r["sequence_groups"]), int(r["isolates_in_those_groups"]))
            except ValueError as exc:
                raise SystemExit("check table counts must be nonnegative integers") from exc
            if any(n < 0 for n in counts):
                raise SystemExit("check table counts must be nonnegative integers")
            if counts != (got["groups"], got["isolates"]):
                bad.append(r["combination"])
        if seen != set(ANCHORS):
            raise SystemExit(f"check table must list all seven regions exactly once; it lists {len(seen)}")
        if bad:
            raise SystemExit(f"counts differ from {a.check_table}: {bad}")
    def safe(value):
        if not value or value in (".", "..") or any(c in value for c in "/\\") or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise SystemExit("filename parameters must be nonempty single path components")
        return value.replace(".", "p")
    stem = a.outdir / f"{safe(a.genus)}_16S_sharing_{safe(a.threshold)}pct_{safe(a.linkage)}_linkage_floor{safe(a.floor)}"
    planned = [Path(f"{stem}{s}") for s in (".png", ".svg", ".pdf", "_plot_only.png", "_CAPTION.md", "_plotted.tsv", "_receipt.json")]
    inputs = {p.resolve() for p in (a.membership, a.collection_map, a.check_table) if p}
    clash = [str(p) for p in planned if p.resolve() in inputs
             or (p.exists() and any(p.samefile(source) for source in inputs))]
    if clash:
        raise SystemExit(f"an output path is also an input; refusing to overwrite it: {clash}")
    existing = [str(p) for p in planned if p.exists() or p.is_symlink()]
    if existing:
        raise SystemExit(f"outputs already exist; choose a new --outdir (no overwrite): {existing}")
    a.outdir.mkdir(parents=True, exist_ok=True)
    with open(f"{stem}_plotted.tsv", "w") as f:
        f.write("region\tgroups\tisolates_in_those_groups\tgroup_ids\n")
        for key in ANCHORS:
            reg = result["regions"][key]
            name = " + ".join(result["collections"][i] for i in key)
            f.write(f"{name} only\t{reg['groups']}\t{reg['isolates']}\t{';'.join(reg['group_ids'])}\n")
    result["reading_key"] = reading_key(a.genus, a.threshold, a.linkage)
    outputs = draw(result, stem)
    cap = Path(f"{stem}_CAPTION.md")
    cap.write_text(caption(result, a.genus, a.threshold, a.floor, a.linkage))
    outputs += [Path(f"{stem}_plotted.tsv"), cap]
    receipt = {"tool": "tools/sequence_group_sharing_venn.py", "tool_sha256": sha(Path(__file__)),
               "theme": "mamey.figure_theme manuscript profile", "genus": a.genus, "threshold": a.threshold,
               "floor": a.floor, "linkage": a.linkage, "membership": str(a.membership),
               "membership_sha256": membership_sha,
               "collection_map": str(a.collection_map), "collection_map_sha256": map_sha,
               "check_table_sha256": check_sha,
               "collection_mapping": mapping,
               "groups": result["groups"], "comparable_isolates": result["isolates"],
               "isolates_per_collection": result["per_collection"], "excluded_no_eligible_comparison": result["excluded"],
               "outputs": {p.name: sha(p) for p in outputs}}
    Path(f"{stem}_receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    sys.stdout.write(json.dumps({k: receipt[k] for k in ("groups", "comparable_isolates", "isolates_per_collection",
                                                          "excluded_no_eligible_comparison")}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
