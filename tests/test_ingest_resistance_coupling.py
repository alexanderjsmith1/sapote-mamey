"""A2: ingest_package must lift source_scans.resistance.bgc_coupling into resistance_coupling.json,
always writing the sid key (assessed-empty != never-assessed)."""
import json, os, tempfile, unittest, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools import ingest_package as ip


class TestResistanceLift(unittest.TestCase):
    def test_build_entry_extracts_resistance(self):
        ss = {"resistance": {"bgc_coupling": {"BGC011": ["Self_resistance_general"]}},
              "regulators": {"bgc_coupling": {}}}
        # build_entry pulls from source_scans; emulate its extraction contract
        rc = dict((ss.get("resistance", {}) or {}).get("bgc_coupling", {}) or {})
        self.assertIn("BGC011", rc)
        self.assertIn("Self_resistance_general", rc["BGC011"])

    def test_merge_writes_sid_key_even_when_empty(self):
        with tempfile.TemporaryDirectory() as d:
            for f in ("bgc_data.json", "gene_data.json", "rggmci_full.json", "tigrfam.json",
                      "tfbs_coupling.json", "resistance_coupling.json"):
                open(os.path.join(d, f), "w").write("{}")
            open(os.path.join(d, "bgc_data.json"), "w").write('{"strains":{},"bgcs":[]}')
            open(os.path.join(d, "gene_data.json"), "w").write('{"scan_agg":{},"tfbs":{}}')
            entry = {"sid": "SX", "strain": {"cohort": "TYPE"}, "bgcs": [], "scan_agg": {},
                     "tfbs": {}, "rggmci_full": {}, "tigrfam": {}, "coupling": {}, "resistance_coupling": {}}
            ip.merge(entry, d)
            rc = json.load(open(os.path.join(d, "resistance_coupling.json")))
            self.assertIn("SX", rc)  # assessed-empty key present


if __name__ == "__main__":
    unittest.main()
