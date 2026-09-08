from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mamey.prior_report_corpus import module_consistency_issues, parse_module_source


class PriorReportCorpusTests(unittest.TestCase):
    def test_v7_sections_remain_source_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "atlas.md"
            path.write_text(
                "# Atlas\n\n## Rank 016: AS-705 BGC004 - comparator title\n\nOld interpretation.\n"
                "\n## Rank 271: AS-705 BGC013 - another title\n\nMore old interpretation.\n"
            )
            rows = parse_module_source(path, "V7_RANKED_ATLAS_MARKDOWN", "AS-705")
            self.assertEqual(set(rows), {"BGC004", "BGC013"})
            self.assertEqual(rows["BGC004"]["source_rank"], "016")
            self.assertIn("Old interpretation", rows["BGC004"]["content_markdown"])
            self.assertNotIn("another title", rows["BGC004"]["content_markdown"])

    def test_mode_b_card_retains_prior_locator_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modeb.md"
            path.write_text(
                "# Compilation\n\n## Mode B — BGC001 (NODE_1_length_99_cov_1) — AS-705\n"
                "\n### §1 Identity\n\nPreliminary.\n"
            )
            rows = parse_module_source(
                path, "PRELIMINARY_MODE_B_COMPILATION_MARKDOWN", "AS-705"
            )
            self.assertEqual(rows["BGC001"]["source_locator_text"], "NODE_1_length_99_cov_1")

    def test_mode_b_compact_following_card_is_not_appended(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modeb.md"
            path.write_text(
                "# Compilation\n\n"
                "## Mode B — BGC022 (NODE_32_length_60747_cov_53) — AS-760\n\n"
                "### §1 Identity\n\nPolyene hypothesis.\n\n"
                "<!-- MODE B TEMPLATE | bgc: BGC022 | node: NODE_32_length_60747_cov_53 | strain: AS-760 -->\n"
                "\n### 3.16  BGC023\n\nTerpene hypothesis.\n"
                "<!-- MODE B TEMPLATE | bgc: BGC023 | node: NODE_34_length_60065_cov_57 | strain: AS-760 -->\n"
            )
            rows = parse_module_source(
                path, "PRELIMINARY_MODE_B_COMPILATION_MARKDOWN", "AS-760"
            )
            self.assertIn("Polyene hypothesis", rows["BGC022"]["content_markdown"])
            self.assertNotIn("BGC023", rows["BGC022"]["content_markdown"])
            self.assertNotIn("Terpene hypothesis", rows["BGC022"]["content_markdown"])

    def test_consistency_gate_rejects_foreign_structural_card(self):
        content = (
            "## Mode B — BGC022 (NODE_32) — AS-760\n"
            "### 3.16 BGC023\n"
            "<!-- MODE B TEMPLATE | bgc: BGC023 | node: NODE_34 | strain: AS-760 -->\n"
        )
        issues = module_consistency_issues(
            content,
            expected_alias="BGC022",
            expected_strain="AS-760",
            expected_source_locator="NODE_32",
        )
        self.assertIn("FOREIGN_COMPACT_BGC_CARD_PRESENT", issues)
        self.assertIn("FOREIGN_MODE_B_TEMPLATE_ALIAS", issues)
        self.assertIn("MODE_B_TEMPLATE_LOCATOR_MISMATCH", issues)

    def test_consistency_gate_rejects_foreign_template_strain(self):
        content = (
            "## Mode B — BGC022 (NODE_32) — AS-760\n"
            "<!-- MODE B TEMPLATE | bgc: BGC022 | node: NODE_32 | strain: AS-705 -->\n"
        )
        issues = module_consistency_issues(
            content,
            expected_alias="BGC022",
            expected_strain="AS-760",
            expected_source_locator="NODE_32",
        )
        self.assertEqual(issues, ["FOREIGN_MODE_B_TEMPLATE_STRAIN"])

    def test_strain_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "atlas.md"
            path.write_text("## Rank 001: AS-421 BGC001 - title\n")
            with self.assertRaisesRegex(ValueError, "strain mismatch"):
                parse_module_source(path, "V7_RANKED_ATLAS_MARKDOWN", "AS-705")


if __name__ == "__main__":
    unittest.main()
