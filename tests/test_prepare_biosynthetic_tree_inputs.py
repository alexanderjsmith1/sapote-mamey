import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "prepare_biosynthetic_tree_inputs.py"


def write_csv(path, fields, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class BiosyntheticTreeInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def fixture(self):
        inventory = self.root / "inventory.csv"
        write_csv(inventory, ["BGC_ID", "Products"], [
            {"BGC_ID": "BGC001", "Products": "PKS;T1PKS"},
            {"BGC_ID": "BGC002", "Products": "RiPP;lanthipeptide-class-iii"},
        ])
        modules = self.root / "modules.csv"
        rows = []
        for index, subtype in enumerate(["Iterative-KS", "Iterative-KS", "Modular-KS", "Iterative-KS"], 1):
            seq = "ACDEFGHIKLMNPQRSTVWY" * 16 + chr(64 + index)
            rows.append({
                "row_id": f"M{index}", "bgc_id": "BGC001", "mapping_status": "MAPPED",
                "locus_tag": f"ctg1_{index}", "domain": "PKS_KS",
                "detail_json": json.dumps({"domain_subtypes": [subtype], "domain_id": [f"KS.{index}"], "translation": [seq]}),
            })
        rows.append({
            "row_id": "R1", "bgc_id": "BGC002", "mapping_status": "MAPPED",
            "locus_tag": "ctg2_1", "domain": "LANC_like",
            "detail_json": json.dumps({"domain_id": ["LanKC.1"], "translation": ["ACDEFGHIKLMNPQRSTVWY" * 6]}),
        })
        write_csv(modules, ["row_id", "bgc_id", "mapping_status", "locus_tag", "domain", "detail_json"], rows)
        manifest = self.root / "sources.tsv"
        manifest.write_text(f"strain_id\tinventory_csv\tmodules_csv\nAS-T1\t{inventory}\t{modules}\n")
        return manifest

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *map(str, args)], cwd=self.root,
                              text=True, capture_output=True)

    def test_show_options(self):
        result = self.run_tool("--show-options")
        self.assertEqual(result.returncode, 0)
        self.assertIn("pks-ks", result.stdout)
        self.assertIn("ripp-precursor", result.stdout)

    def test_pks_requires_subtype(self):
        manifest = self.fixture()
        result = self.run_tool(manifest, self.root / "out", "--track", "pks-ks")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires one exact --subtype", result.stderr)

    def test_pks_exact_subtype_and_receipt(self):
        manifest = self.fixture()
        output = self.root / "out"
        result = self.run_tool(manifest, output, "--track", "pks-ks", "--subtype", "Iterative-KS")
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((output / "receipt.json").read_text())
        self.assertEqual(receipt["counts"]["eligible_sequences"], 3)
        self.assertEqual(receipt["counts"]["status_counts"]["EXCLUDED"], 1)
        self.assertEqual(receipt["status"], "HOLD_TOO_FEW_ELIGIBLE_SEQUENCES")
        self.assertEqual((output / "sequences.faa").read_text().count(">"), 3)

    def test_ripp_enzyme_requires_family_and_domain(self):
        manifest = self.fixture()
        result = self.run_tool(manifest, self.root / "out", "--track", "ripp-enzyme", "--domain", "LANC_like")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires at least one --domain and a --family", result.stderr)

    def test_ripp_family_filter(self):
        manifest = self.fixture()
        output = self.root / "out"
        result = self.run_tool(manifest, output, "--track", "ripp-enzyme", "--domain", "LANC_like",
                               "--family", "lanthipeptide-class-iii")
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((output / "receipt.json").read_text())
        self.assertEqual(receipt["counts"]["eligible_sequences"], 1)

    def test_ripp_domain_table_uses_exact_full_protein(self):
        inventory = self.root / "inventory.csv"
        write_csv(inventory, ["BGC_ID", "Products"], [
            {"BGC_ID": "BGC002", "Products": "RiPP;lanthipeptide-class-iii"},
        ])
        domains = self.root / "domains.csv"
        write_csv(domains, ["bgc_id", "locus_tag", "domain", "domain_id"], [
            {"bgc_id": "BGC002", "locus_tag": "ctg2_9", "domain": "LANC_like", "domain_id": "PF05147.16"},
        ])
        proteins = self.root / "proteins.faa"
        protein_sequence = "ACDEFGHIKLMNPQRSTVWY" * 8
        proteins.write_text(f">ctg2_9 exact full protein\n{protein_sequence}\n")
        manifest = self.root / "sources.tsv"
        manifest.write_text(
            "strain_id\tinventory_csv\tdomains_csv\tproteins_faa\n"
            f"AS-T2\t{inventory}\t{domains}\t{proteins}\n"
        )
        output = self.root / "out"
        result = self.run_tool(
            manifest, output, "--track", "ripp-enzyme", "--domain", "LANC_like",
            "--family", "lanthipeptide-class-iii",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((output / "receipt.json").read_text())
        self.assertEqual(receipt["counts"]["eligible_sequences"], 1)
        with (output / "sequence_ledger.tsv").open() as handle:
            ledger = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(Path(ledger[0]["source_file"]).resolve(), domains.resolve())
        self.assertEqual(int(ledger[0]["aa_length"]), len(protein_sequence))
        fasta_sequence = "".join((output / "sequences.faa").read_text().splitlines()[1:])
        self.assertEqual(fasta_sequence, protein_sequence)

    def test_existing_output_is_not_overwritten(self):
        manifest = self.fixture()
        output = self.root / "out"
        output.mkdir()
        result = self.run_tool(manifest, output, "--track", "pks-ks", "--subtype", "Iterative-KS")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
