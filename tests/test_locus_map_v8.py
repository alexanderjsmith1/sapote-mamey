"""Generic regression tests for the evidence-dense locus-map v8 renderer."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _fixture(root: Path, *, with_comparator: bool = True, gene_count: int = 47) -> Path:
    pkg = root / "STRAIN-TEST" / "package"
    pkg.mkdir(parents=True)
    _write(pkg / "manifest.json", json.dumps({"strain_id": "STRAIN-TEST"}) + "\n")
    _write(
        pkg / "STRAIN-TEST_4_triage_board.csv",
        "BGC_ID,Node_ID,Contig,antiSMASH_Region,Products,Corrected_rank\n"
        "BGC001,NODE_1,NODE_1_length_500000_cov_40.0,region001,NRPS-like,1\n",
    )
    gene_rows = [
        "bgc_id,locus_tag,cds_start,cds_end,strand,sec_met_domains,aa_length,gene_function_inference"
    ]
    for index in range(1, gene_count + 1):
        start = 1000 + (index - 1) * 900
        end = start + 700
        strand = "+" if index % 3 else "-"
        domain = "Condensation_LCL;AMP-binding" if index in {4, 5, 6} else ""
        function = "ABC transporter" if index == 2 else ("regulator" if index == 46 else "context protein")
        gene_rows.append(
            f"BGC001,ctg1_{index},{start},{end},{strand},{domain},233,{function}"
        )
    _write(pkg / "STRAIN-TEST_gene_by_gene_all_bgcs.csv", "\n".join(gene_rows) + "\n")

    if with_comparator:
        mibig = [
            "bgc_id,query_gene,subject_gene,mibig_accession,mibig_compound,pct_identity,pct_coverage,blast_score,evalue,reference_rank"
        ]
        for index in range(1, 26):
            mibig.append(
                f"BGC001,ctg1_{index},REF_{index},BGC0000001,reference alpha,{45 + index / 10:.1f},"
                f"{80 + index / 10:.1f},{100 + index:.1f},1e-{index + 10},2"
            )
        # Higher median identity but fewer exact query genes: must not win.
        for index in range(1, 13):
            mibig.append(
                f"BGC001,ctg1_{index},ALT_{index},BGC0000002,reference beta,91.0,99.0,500.0,1e-80,1"
            )
        _write(pkg / "STRAIN-TEST_3_mibig_per_gene.csv", "\n".join(mibig) + "\n")

    _write(
        pkg / "STRAIN-TEST_3_antismash_hmm.csv",
        "bgc_id,locus_tag,domain_name\nBGC001,ctg1_4,AMP-binding\n",
    )
    _write(
        pkg / "STRAIN-TEST_3_antismash_modules.csv",
        "bgc_id,locus_tag,domain\nBGC001,ctg1_4,Condensation_LCL\n",
    )
    _write(
        pkg / "STRAIN-TEST_3_antismash_motifs.csv",
        "bgc_id,locus_tag,motif\nBGC001,ctg1_4,core_motif\n",
    )
    return pkg


class LocusMapV8Tests(unittest.TestCase):
    def test_current_run_cds_table_is_used_before_all_bgc_table_exists(self) -> None:
        from mamey.locus_map_v8 import load_genes, render_bgc_v8

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp), with_comparator=False)
            (pkg / "STRAIN-TEST_gene_by_gene_all_bgcs.csv").unlink()
            _write(
                pkg / "STRAIN-TEST_cds_table.csv",
                "bgc_id,contig,locus_tag,order,start,end,strand,length_bp,length_aa,product,sec_met_domains,gene_functions,tta_codons\n"
                "BGC001,NODE_1,ctg1_early,1,1000,1800,1,801,266,core peptide synthase,AMP-binding,biosynthetic,0\n",
            )

            genes, source = load_genes(pkg, "BGC001")
            self.assertEqual([gene.locus_tag for gene in genes], ["ctg1_early"])
            self.assertEqual(source, pkg / "STRAIN-TEST_cds_table.csv")

            receipt = render_bgc_v8(pkg, "BGC001", out_dir=Path(tmp) / "rendered")
            self.assertEqual(receipt["status"], "READY")
            self.assertEqual(receipt["gene_count"], 1)

    def test_comparator_tie_breaks_by_accession_after_all_other_criteria(self) -> None:
        from mamey.locus_map_v8 import choose_comparator

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp), with_comparator=False)
            _write(
                pkg / "STRAIN-TEST_3_mibig_per_gene.csv",
                "bgc_id,query_gene,subject_gene,mibig_accession,mibig_compound,pct_identity,pct_coverage,blast_score,evalue,reference_rank\n"
                "BGC001,ctg1_1,REF_Z1,BGC0000002,reference zeta,70,90,100,1e-20,1\n"
                "BGC001,ctg1_2,REF_Z2,BGC0000002,reference zeta,50,90,100,1e-20,1\n"
                "BGC001,ctg1_1,REF_A1,BGC0000001,reference alpha,70,90,100,1e-20,1\n"
                "BGC001,ctg1_2,REF_A2,BGC0000001,reference alpha,50,90,100,1e-20,1\n",
            )
            comparator, _source = choose_comparator(pkg, "BGC001")
            self.assertEqual(comparator.accession, "BGC0000001")
            self.assertEqual(set(comparator.genes), {"ctg1_1", "ctg1_2"})

    def test_comparator_with_zero_supported_query_genes_is_not_selected(self) -> None:
        from mamey.locus_map_v8 import choose_comparator

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp), with_comparator=False)
            _write(
                pkg / "STRAIN-TEST_3_mibig_per_gene.csv",
                "bgc_id,query_gene,subject_gene,mibig_accession,mibig_compound,pct_identity,pct_coverage,blast_score,evalue,reference_rank\n"
                "BGC001,,REF_0,BGC0000999,unsupported reference,99,99,500,1e-50,1\n",
            )
            comparator, _source = choose_comparator(pkg, "BGC001")
            self.assertEqual(comparator.accession, "")
            self.assertEqual(comparator.genes, {})

    def test_coverage_over_100_is_preserved_and_explicitly_labelled(self) -> None:
        from mamey.locus_map_v8 import _format_coverage, render_bgc_v8

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp))
            mibig_path = pkg / "STRAIN-TEST_3_mibig_per_gene.csv"
            text = mibig_path.read_text(encoding="utf-8").replace(",80.1,", ",103.0,", 1)
            mibig_path.write_text(text, encoding="utf-8")
            out = Path(tmp) / "rendered"
            receipt = render_bgc_v8(pkg, "BGC001", out_dir=out)

            self.assertEqual(_format_coverage(103.0), "103% cov*")
            self.assertEqual(receipt["coverage_values_over_100"], 1)
            self.assertIn("RAW_UNCAPPED_SOURCE_REPORTED", receipt["coverage_display_policy"])
            with (out / "BGC001_locus_map_data.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["pct_coverage"], "103.000")

    def test_47_gene_label_rail_assigns_one_unique_slot_per_gene(self) -> None:
        from mamey.locus_map_v8 import _draw_label_rail, load_genes
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp), with_comparator=False)
            genes, _source = load_genes(pkg, "BGC001")
            minx, maxx = min(g.start for g in genes), max(g.end for g in genes)
            fig, axis = plt.subplots(figsize=(16, 3), dpi=180)
            axis.set_xlim(minx, maxx)
            axis.set_ylim(-1.25, 1.18)
            _draw_label_rail(axis, genes, minx, maxx)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            boxes = [label.get_window_extent(renderer) for label in axis.texts]
            plt.close(fig)

            self.assertEqual(len(boxes), 47)
            self.assertFalse(any(
                left.overlaps(right)
                for index, left in enumerate(boxes)
                for right in boxes[index + 1:]
            ))

    def test_all_exact_labels_and_comparator_layers_survive(self) -> None:
        from mamey.locus_map_v8 import (
            choose_comparator,
            render_bgc_v8,
            validate_v8_gene_roster,
        )

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp))
            comparator, _source = choose_comparator(pkg, "BGC001")
            self.assertEqual(comparator.accession, "BGC0000001")
            self.assertEqual(len(comparator.genes), 25)

            out = Path(tmp) / "rendered"
            receipt = render_bgc_v8(pkg, "BGC001", out_dir=out)
            self.assertEqual(receipt["status"], "READY")
            self.assertEqual(receipt["gene_count"], 47)
            self.assertEqual(receipt["exact_labels_displayed"], 47)
            self.assertEqual(receipt["exact_labels_suppressed"], 0)
            self.assertEqual(receipt["label_layout"]["lane_count"], 1)
            self.assertEqual(
                receipt["exact_locus_identity"]["display"],
                "STRAIN-TEST / NODE_1_length_500000_cov_40.0 / region001 / BGC001",
            )
            self.assertEqual(
                receipt["selected_comparator"]["supporting_exact_genes"], 25
            )
            self.assertEqual(receipt["selected_genes_displayed_in_evidence_panel"], 25)
            self.assertTrue(receipt["full_evidence_preserved_in_csv"])
            csv_path = out / receipt["outputs"]["csv"]
            self.assertEqual(receipt["gene_roster"]["row_count"], 47)
            self.assertEqual(validate_v8_gene_roster(receipt, csv_path), [])

            ET.parse(out / "BGC001_locus_map.svg")
            self.assertTrue((out / "BGC001_locus_map.png").is_file())
            with (out / "BGC001_locus_map_data.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 47)
            self.assertTrue(all(row["label_displayed"] == "YES" for row in rows))
            self.assertEqual(sum(row["selected_comparator"] == "YES" for row in rows), 25)
            gene4 = next(row for row in rows if row["locus_tag"] == "ctg1_4")
            self.assertIn("AMP-binding", gene4["hmm_tokens"])
            self.assertIn("Condensation_LCL", gene4["module_tokens"])
            self.assertIn("core_motif", gene4["motif_tokens"])

            # A post-render row mutation invalidates both file and roster hashes.
            original_csv = csv_path.read_text(encoding="utf-8")
            csv_path.write_text(original_csv.replace("ctg1_1", "ctg1_X", 1), encoding="utf-8")
            issues = validate_v8_gene_roster(receipt, csv_path)
            self.assertIn("V8_CSV_HASH_MISMATCH", issues)
            self.assertIn("V8_GENE_ROSTER_HASH_MISMATCH", issues)
            csv_path.write_text(original_csv, encoding="utf-8")

            svg = (out / "BGC001_locus_map.svg").read_text(encoding="utf-8")
            for index in range(1, 48):
                self.assertIn(f"ctg1_{index}", svg)
            self.assertIn("BGC0000001", svg)

            second = Path(tmp) / "rendered-again"
            render_bgc_v8(pkg, "BGC001", out_dir=second)
            self.assertEqual(
                (out / "BGC001_locus_map.svg").read_bytes(),
                (second / "BGC001_locus_map.svg").read_bytes(),
            )

    def test_compile_adapter_defaults_to_v8_and_honors_top_n(self) -> None:
        from mamey.locus_map import render_for_compile_report

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp))
            result = render_for_compile_report(pkg, top_n=1)
            self.assertEqual(result["renderer"], "v8")
            self.assertEqual(result["rendered"], ["BGC001"])
            receipt = json.loads(
                (pkg / "locus_maps" / "BGC001_locus_map_v8_receipt.json").read_text()
            )
            self.assertEqual(receipt["exact_labels_suppressed"], 0)

    def test_missing_comparator_is_explicit_and_non_blocking(self) -> None:
        from mamey.locus_map_v8 import render_bgc_v8

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp), with_comparator=False)
            out = Path(tmp) / "rendered"
            receipt = render_bgc_v8(pkg, "BGC001", out_dir=out)
            self.assertEqual(receipt["selected_comparator"]["accession"], "")
            self.assertEqual(receipt["selected_genes_displayed_in_evidence_panel"], 0)
            self.assertEqual(receipt["exact_labels_displayed"], 47)
            self.assertEqual(receipt["exact_labels_suppressed"], 0)

    def test_very_dense_locus_uses_multiple_exact_label_lanes(self) -> None:
        from mamey.locus_map_v8 import MAX_LABELS_PER_LANE, render_bgc_v8

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp), with_comparator=False, gene_count=268)
            out = Path(tmp) / "dense-render"
            receipt = render_bgc_v8(pkg, "BGC001", out_dir=out)
            self.assertEqual(receipt["exact_labels_displayed"], 268)
            self.assertEqual(receipt["exact_labels_suppressed"], 0)
            self.assertEqual(receipt["label_layout"]["lane_count"], 4)
            self.assertEqual(receipt["label_layout"]["max_labels_per_lane"], MAX_LABELS_PER_LANE)
            svg = (out / "BGC001_locus_map.svg").read_text(encoding="utf-8")
            self.assertIn("ctg1_1", svg)
            self.assertIn("ctg1_268", svg)

    def test_receipt_consumer_binds_triple_and_refuses_tampering(self) -> None:
        from mamey.locus_map_v8 import (
            FigureReceiptMismatch,
            render_bgc_v8,
            validate_locus_map_v8_receipt,
        )

        with tempfile.TemporaryDirectory() as tmp:
            pkg = _fixture(Path(tmp))
            out = Path(tmp) / "rendered"
            render_bgc_v8(pkg, "BGC001", out_dir=out)
            receipt_path = out / "BGC001_locus_map_v8_receipt.json"

            validated = validate_locus_map_v8_receipt(
                receipt_path, expected_bgc_id="BGC001"
            )
            self.assertEqual(validated["status"], "READY")
            self.assertEqual(set(validated["output_integrity"]), {"png", "svg", "csv"})

            png_path = out / validated["outputs"]["png"]
            original_png = png_path.read_bytes()
            png_path.write_bytes(original_png + b"tampered")
            with self.assertRaises(FigureReceiptMismatch) as caught:
                validate_locus_map_v8_receipt(receipt_path)
            self.assertEqual(caught.exception.code, "FIGURE_RECEIPT_MISMATCH")
            self.assertIn("png_sha256", caught.exception.details)

            png_path.write_bytes(original_png)
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["status"] = "NEEDS_REVIEW"
            receipt_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(FigureReceiptMismatch) as caught:
                validate_locus_map_v8_receipt(receipt_path)
            self.assertIn("status", caught.exception.details)


if __name__ == "__main__":
    unittest.main()
