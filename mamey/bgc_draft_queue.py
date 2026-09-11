"""Build a deterministic, source-bound queue for high-throughput BGC drafts.

The queue deliberately separates an L0 source-bound draft from an L1 exact-current
locus report.  A source-scoped inventory row may therefore enter the drafting queue
without pretending that its assembly identity or current BLASTP query receipt has
already been admitted.
"""

from __future__ import annotations

import argparse
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


INVENTORY_REQUIRED = {
    "BGC_ID",
    "Contig",
    "antiSMASH_Region",
    "Length_kb",
    "Boundary",
    "Products",
}
ROUTING_REQUIRED = {
    "strain",
    "source_scoped_bgc_alias",
    "activity_route",
    "prior_activity_routing_score",
    "prior_route_rank",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle, delimiter="\t")
        ]


def _read_csv(path: Path) -> tuple[list[dict[str, str]], set[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]
    return rows, fields


def parse_assignment(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError(f"expected NAME=VALUE assignment, got: {value}")
    name, raw = value.split("=", 1)
    if not name.strip() or not raw.strip():
        raise ValueError(f"blank NAME or VALUE in assignment: {value}")
    return name.strip(), raw.strip()


def parse_inventory_specs(values: Iterable[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        strain, raw_path = parse_assignment(value)
        if strain in result:
            raise ValueError(f"duplicate inventory strain: {strain}")
        result[strain] = Path(raw_path).expanduser().resolve(strict=True)
    if not result:
        raise ValueError("at least one --inventory STRAIN=PATH is required")
    return result


def parse_allocations(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        strain, raw_count = parse_assignment(value)
        try:
            count = int(raw_count)
        except ValueError as exc:
            raise ValueError(f"allocation is not an integer: {value}") from exc
        if count <= 0:
            raise ValueError(f"allocation must be positive: {value}")
        if strain in result:
            raise ValueError(f"duplicate allocation strain: {strain}")
        result[strain] = count
    return result


def _number(value: str, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"non-numeric {field}: {value!r}") from exc


def _alias_number(alias: str) -> int:
    digits = "".join(ch for ch in alias if ch.isdigit())
    return int(digits) if digits else 10**9


def load_routing(paths: Iterable[Path]) -> dict[tuple[str, str], dict[str, str]]:
    selected: dict[tuple[str, str], dict[str, str]] = {}
    for path in paths:
        rows = _read_tsv(path)
        fields = set(rows[0]) if rows else set()
        missing = ROUTING_REQUIRED - fields
        if missing:
            raise ValueError(f"routing ledger {path} missing columns: {sorted(missing)}")
        for row in rows:
            key = (row["strain"], row["source_scoped_bgc_alias"])
            score = _number(row["prior_activity_routing_score"], field="routing score")
            rank = _number(row["prior_route_rank"], field="route rank")
            candidate = dict(row)
            candidate["_score"] = str(score)
            candidate["_rank"] = str(rank)
            previous = selected.get(key)
            if previous is None or (-score, rank, row["activity_route"]) < (
                -float(previous["_score"]),
                float(previous["_rank"]),
                previous["activity_route"],
            ):
                selected[key] = candidate
    return selected


def load_modeb_census(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    rows = _read_tsv(path)
    required = {"strain", "sha256", "mode_b_card_count"}
    fields = set(rows[0]) if rows else set()
    missing = required - fields
    if missing:
        raise ValueError(f"Mode B census missing columns: {sorted(missing)}")
    return {row["strain"]: row for row in rows}


def build_queue(
    *,
    inventories: dict[str, Path],
    allocations: dict[str, int],
    routing_paths: Iterable[Path] = (),
    modeb_census_path: Path | None = None,
) -> list[dict[str, str]]:
    if set(inventories) != set(allocations):
        raise ValueError("inventory strains and allocation strains must match exactly")

    routing = load_routing(routing_paths)
    modeb = load_modeb_census(modeb_census_path)
    queue: list[dict[str, str]] = []

    for strain, inventory_path in inventories.items():
        rows, fields = _read_csv(inventory_path)
        missing = INVENTORY_REQUIRED - fields
        if missing:
            raise ValueError(
                f"inventory for {strain} missing columns: {sorted(missing)}"
            )
        seen: set[str] = set()
        candidates = []
        inventory_sha = sha256_file(inventory_path)
        for row in rows:
            alias = row["BGC_ID"]
            if not alias or alias in seen:
                raise ValueError(f"blank or duplicate BGC_ID for {strain}: {alias!r}")
            seen.add(alias)
            length_kb = _number(row["Length_kb"], field="Length_kb")
            route = routing.get((strain, alias))
            primary_locator = f"{row['Contig']} / {row['antiSMASH_Region']}"
            selection_lane = "ANTIMICROBIAL_ROUTING" if route else "SIZE_COMPLETION"
            route_score = float(route["_score"]) if route else -1.0
            route_rank = float(route["_rank"]) if route else 10**9
            candidates.append(
                {
                    "strain": strain,
                    "primary_user_locator": primary_locator,
                    "source_scoped_bgc_alias": alias,
                    "products": row["Products"],
                    "length_kb": f"{length_kb:.2f}",
                    "boundary": row["Boundary"],
                    "selection_lane": selection_lane,
                    "activity_route": route["activity_route"] if route else "NOT_ROUTED",
                    "prior_activity_routing_score": (
                        route["prior_activity_routing_score"] if route else ""
                    ),
                    "prior_route_rank": route["prior_route_rank"] if route else "",
                    "inventory_source_sha256": inventory_sha,
                    "modeb_source_sha256": modeb.get(strain, {}).get("sha256", ""),
                    "modeb_card_count": modeb.get(strain, {}).get(
                        "mode_b_card_count", ""
                    ),
                    "draft_target_level": "L0_SOURCE_BOUND_VERIFIABLE_DRAFT",
                    "identity_state": "SOURCE_LOCATOR_BOUND_EXACT_ASSEMBLY_ADMISSION_PENDING",
                    "blastp_state": "CHANNEL_OVERLAY_OPTIONAL_OBSERVED_IS_NOT_ADMITTED",
                    "draft_state": "NOT_STARTED",
                    "_sort": (
                        0 if route else 1,
                        -route_score,
                        route_rank,
                        -length_kb,
                        _alias_number(alias),
                    ),
                }
            )

        allocation = allocations[strain]
        if allocation > len(candidates):
            raise ValueError(
                f"allocation {allocation} exceeds {len(candidates)} inventory rows for {strain}"
            )
        candidates.sort(key=lambda row: row["_sort"])
        for strain_rank, row in enumerate(candidates[:allocation], start=1):
            row = {key: value for key, value in row.items() if key != "_sort"}
            row["strain_queue_rank"] = str(strain_rank)
            queue.append(row)

    for global_rank, row in enumerate(queue, start=1):
        row["global_queue_rank"] = str(global_rank)
    return queue


OUTPUT_FIELDS = [
    "global_queue_rank",
    "strain_queue_rank",
    "strain",
    "primary_user_locator",
    "source_scoped_bgc_alias",
    "products",
    "length_kb",
    "boundary",
    "selection_lane",
    "activity_route",
    "prior_activity_routing_score",
    "prior_route_rank",
    "inventory_source_sha256",
    "modeb_source_sha256",
    "modeb_card_count",
    "draft_target_level",
    "identity_state",
    "blastp_state",
    "draft_state",
]


def write_queue(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=OUTPUT_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="append", default=[], metavar="STRAIN=PATH")
    parser.add_argument("--allocation", action="append", default=[], metavar="STRAIN=COUNT")
    parser.add_argument("--routing-ledger", action="append", default=[], type=Path)
    parser.add_argument("--modeb-census", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    rows = build_queue(
        inventories=parse_inventory_specs(args.inventory),
        allocations=parse_allocations(args.allocation),
        routing_paths=[path.resolve(strict=True) for path in args.routing_ledger],
        modeb_census_path=(args.modeb_census.resolve(strict=True) if args.modeb_census else None),
    )
    write_queue(rows, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
