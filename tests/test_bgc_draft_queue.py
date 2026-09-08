from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from mamey.bgc_draft_queue import build_queue, write_queue


INVENTORY_FIELDS = [
    "BGC_ID",
    "Contig",
    "antiSMASH_Region",
    "Length_kb",
    "Boundary",
    "Products",
]


def write_inventory(path: Path, rows: list[dict[str, str]], fields=INVENTORY_FIELDS):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_routing(path: Path, rows: list[dict[str, str]]):
    fields = [
        "strain",
        "source_scoped_bgc_alias",
        "activity_route",
        "prior_activity_routing_score",
        "prior_route_rank",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def row(alias: str, length: str) -> dict[str, str]:
    return {
        "BGC_ID": alias,
        "Contig": f"NODE_{alias[-1]}_length_1000_cov_20.0",
        "antiSMASH_Region": "region001",
        "Length_kb": length,
        "Boundary": "Interior",
        "Products": "NRPS",
    }


class DraftQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_routed_rows_precede_larger_unrouted_rows(self):
        inv = self.root / "a.csv"
        route = self.root / "route.tsv"
        write_inventory(inv, [row("BGC001", "10"), row("BGC002", "100")])
        write_routing(
            route,
            [{
                "strain": "STRAIN-A",
                "source_scoped_bgc_alias": "BGC001",
                "activity_route": "ANTIFUNGAL_ROUTING",
                "prior_activity_routing_score": "40",
                "prior_route_rank": "2",
            }],
        )
        queue = build_queue(
            inventories={"STRAIN-A": inv},
            allocations={"STRAIN-A": 2},
            routing_paths=[route],
        )
        self.assertEqual([r["source_scoped_bgc_alias"] for r in queue], ["BGC001", "BGC002"])
        self.assertEqual(queue[0]["selection_lane"], "ANTIMICROBIAL_ROUTING")

    def test_unrouted_completion_is_length_descending(self):
        inv = self.root / "a.csv"
        write_inventory(inv, [row("BGC001", "10"), row("BGC002", "100")])
        queue = build_queue(
            inventories={"STRAIN-A": inv}, allocations={"STRAIN-A": 2}
        )
        self.assertEqual([r["source_scoped_bgc_alias"] for r in queue], ["BGC002", "BGC001"])

    def test_alias_collision_across_strains_stays_separate(self):
        a, b = self.root / "a.csv", self.root / "b.csv"
        write_inventory(a, [row("BGC001", "10")])
        write_inventory(b, [row("BGC001", "20")])
        queue = build_queue(
            inventories={"STRAIN-A": a, "STRAIN-B": b},
            allocations={"STRAIN-A": 1, "STRAIN-B": 1},
        )
        self.assertEqual([(r["strain"], r["source_scoped_bgc_alias"]) for r in queue], [("STRAIN-A", "BGC001"), ("STRAIN-B", "BGC001")])

    def test_overallocation_fails_closed(self):
        inv = self.root / "a.csv"
        write_inventory(inv, [row("BGC001", "10")])
        with self.assertRaisesRegex(ValueError, "exceeds"):
            build_queue(inventories={"STRAIN-A": inv}, allocations={"STRAIN-A": 2})

    def test_missing_inventory_column_fails_closed(self):
        inv = self.root / "a.csv"
        fields = [field for field in INVENTORY_FIELDS if field != "Contig"]
        write_inventory(inv, [{key: value for key, value in row("BGC001", "10").items() if key in fields}], fields=fields)
        with self.assertRaisesRegex(ValueError, "missing columns"):
            build_queue(inventories={"STRAIN-A": inv}, allocations={"STRAIN-A": 1})

    def test_output_is_deterministic_and_has_no_source_path_column(self):
        inv = self.root / "a.csv"
        write_inventory(inv, [row("BGC001", "10")])
        queue = build_queue(inventories={"STRAIN-A": inv}, allocations={"STRAIN-A": 1})
        first, second = self.root / "first.tsv", self.root / "second.tsv"
        write_queue(queue, first)
        write_queue(queue, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertNotIn("source_path", first.read_text().splitlines()[0])

    def test_source_locator_draft_does_not_claim_exact_assembly(self):
        inv = self.root / "a.csv"
        write_inventory(inv, [row("BGC001", "10")])
        queue = build_queue(inventories={"STRAIN-A": inv}, allocations={"STRAIN-A": 1})
        self.assertEqual(
            queue[0]["identity_state"],
            "SOURCE_LOCATOR_BOUND_EXACT_ASSEMBLY_ADMISSION_PENDING",
        )
        self.assertEqual(queue[0]["draft_target_level"], "L0_SOURCE_BOUND_VERIFIABLE_DRAFT")


if __name__ == "__main__":
    unittest.main()
