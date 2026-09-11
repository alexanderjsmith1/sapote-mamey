from pathlib import Path
import csv
import tempfile
import unittest

from tools.audit_modeb_support_card import audit_card


VALID_CARD = """# Quarantine recovery support card — AS-1 BGC001

## Recovery disposition
- **Priority rank:** 200
- **Value tier:** `USEFUL_WITH_LIMITATIONS`
- **QA status:** `PASS`
- **Expected proteins:** 1
- **Direct-hit union:** 1/1
- **No-significant-hit proteins:** 0
- **Unresolved/unavailable direct-query proteins:** 0
- **Claim ceiling:** encoded capacity only; not product identity, production, activity, novelty, or linkage.

## Executive verdict
One-protein fragment with role-level similarity evidence.

## 1. Source lock and locus identity
Current `/mamey_packages/` package and exact `archive.zip::region.gbk`.

## 2. Complete gene-by-gene verdict
| Protein | Verdict |
|---|---|
| `ctg1_1` | direct current-query family-level hit |

Visible URL: https://www.ncbi.nlm.nih.gov/protein/WP_000000001.1

## 3. Homology channels
### NCBI nr
DIRECT_HIT.
### EBI
EBI_UNAVAILABLE.
### Local Swiss-Prot
LOCAL_SWISSPROT_UNAVAILABLE.

## 4. Captured architecture and alternatives
Partial domain architecture; alternatives remain open.

## 5. Cluster-comparison evidence
General ClusterBlast checked. KnownClusterBlast similarity, not identity. SubClusterBlast checked.

## 6. Cohort and cross-contig context
BiG-SCAPE context only. RG-GMCI does not establish physical linkage; NOT_LINKED_ACROSS_CONTIGS.

## 7. Taxonomy, ecology, and activity boundaries
No locus-level taxonomy transfer, ecological function, or activity assignment.

## 8. Value tier and safe use
Useful for a fragmentation example.

## 9. Missing evidence and next decision
Assembly closure remains missing.

## 10. QA receipt
All denominators and channel states checked.
"""


class AuditSupportCardTests(unittest.TestCase):
    def _write(self, root: Path, text: str) -> Path:
        path = root / "card.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_complete_card_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            card = self._write(Path(tmp), VALID_CARD)
            result = audit_card(card, rank_min=169, rank_max=336, check_sources=False)
            self.assertTrue(result.pass_gate, result.findings)

    def test_gene_denominator_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_CARD.replace("**Expected proteins:** 1", "**Expected proteins:** 2")
            card = self._write(Path(tmp), text)
            result = audit_card(card, check_sources=False)
            codes = {finding["code"] for finding in result.findings}
            self.assertIn("GENE_DENOMINATOR_MISMATCH", codes)
            self.assertFalse(result.pass_gate)

    def test_direct_hit_requires_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_CARD.replace(
                "Visible URL: https://www.ncbi.nlm.nih.gov/protein/WP_000000001.1",
                "Visible URL unavailable.",
            )
            card = self._write(Path(tmp), text)
            result = audit_card(card, check_sources=False)
            codes = {finding["code"] for finding in result.findings}
            self.assertIn("VISIBLE_URL_MISSING", codes)

    def test_forbidden_workspace_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = VALID_CARD + "\n`/Users/<user>/<workspace>/example.csv`\n"
            card = self._write(Path(tmp), text)
            result = audit_card(card, check_sources=False)
            codes = {finding["code"] for finding in result.findings}
            self.assertIn("FORBIDDEN_WORKSPACE", codes)

    def test_ledger_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            card = self._write(root, VALID_CARD)
            ledger = root / "ledger.csv"
            fields = [
                "priority_rank",
                "markdown_path",
                "value_tier",
                "qc_status",
                "expected_genes",
                "direct_hit_union",
                "no_significant_hit",
            ]
            with ledger.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "priority_rank": "200",
                        "markdown_path": str(card),
                        "value_tier": "HOLD",
                        "qc_status": "PASS",
                        "expected_genes": "1",
                        "direct_hit_union": "1",
                        "no_significant_hit": "0",
                    }
                )
            result = audit_card(card, ledger=ledger, check_sources=False)
            codes = {finding["code"] for finding in result.findings}
            self.assertIn("LEDGER_MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()

