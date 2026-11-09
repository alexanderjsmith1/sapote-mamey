"""Locus maps: an unknown strand is not drawn forward, and a comparator needs real hit evidence."""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOCUS_R = ROOT / "tools" / "sapote_locus_map.R"


def _package(root: Path, strands: list[str], mibig: str | None = None) -> Path:
    pkg = root / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "Example_sp"}) + "\n")
    (pkg / "X_4_triage_board.csv").write_text(
        "BGC_ID,Contig,antiSMASH_Region\nBGC001,CONTIG_1.1,region001\n")
    rows = ["bgc_id,locus_tag,cds_start,cds_end,strand,aa_length,gene_function_inference"]
    for index, strand in enumerate(strands, 1):
        start = 1000 * index
        rows.append(f"BGC001,g{index},{start},{start + 700},{strand},233,context protein")
    (pkg / "X_gene_by_gene_all_bgcs.csv").write_text("\n".join(rows) + "\n")
    if mibig is not None:
        (pkg / "X_3_mibig_per_gene.csv").write_text(mibig)
    return pkg


def test_unknown_or_missing_strand_is_not_forward(tmp_path: Path) -> None:
    from mamey.locus_map_v8 import load_genes

    pkg = _package(tmp_path, ["+", "-1", "?", "", "1", "-"])
    genes, _ = load_genes(pkg, "BGC001")
    assert [g.strand for g in genes] == [1, -1, 0, 0, 1, -1]


def test_render_writes_blank_strand_and_lists_unknown_loci(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    from mamey.locus_map_v8 import render_bgc_v8

    pkg = _package(tmp_path, ["+", "?", "-"])
    receipt = render_bgc_v8(pkg, "BGC001", out_dir=tmp_path / "maps")
    with (tmp_path / "maps" / "BGC001_locus_map_data.csv").open(newline="") as handle:
        strands = [row["strand"] for row in csv.DictReader(handle)]
    assert strands == ["+", "", "-"]
    assert receipt["strand_unknown_loci"] == ["g2"]


def test_comparator_ignores_rows_without_subject_or_identity(tmp_path: Path) -> None:
    from mamey.locus_map_v8 import choose_comparator

    mibig = (
        "bgc_id,query_gene,subject_gene,mibig_accession,mibig_compound,pct_identity,pct_coverage,blast_score,evalue,reference_rank\n"
        # Three query genes but no subject or identity: not a supported hit.
        "BGC001,g1,,BGC0000009,blank ref,,,,,1\n"
        "BGC001,g2,,BGC0000009,blank ref,,,,,1\n"
        "BGC001,g3,NA,BGC0000009,blank ref,NA,,,,1\n"
        # One real hit.
        "BGC001,g1,REF_1,BGC0000001,real ref,55.0,90.0,120.0,1e-30,2\n"
    )
    pkg = _package(tmp_path, ["+", "+", "+"], mibig)
    comparator, _ = choose_comparator(pkg, "BGC001")
    assert comparator.accession == "BGC0000001"
    assert set(comparator.genes) == {"g1"}
    assert comparator.unresolved_rows == 3


def test_comparator_with_only_unsupported_rows_is_empty(tmp_path: Path) -> None:
    from mamey.locus_map_v8 import choose_comparator

    mibig = (
        "bgc_id,query_gene,subject_gene,mibig_accession,mibig_compound,pct_identity\n"
        "BGC001,g1,,BGC0000009,blank ref,\n"
    )
    pkg = _package(tmp_path, ["+"], mibig)
    comparator, _ = choose_comparator(pkg, "BGC001")
    assert comparator.accession == ""
    assert comparator.genes == {}
    assert comparator.unresolved_rows == 1


def _rscript() -> str:
    path = shutil.which("Rscript")
    if path is None:
        pytest.skip("Rscript not installed")
    return path


def test_r_strand_direction_keeps_reverse_and_unknown() -> None:
    rscript = _rscript()
    expr = (
        f"exprs <- parse({str(LOCUS_R)!r}); "
        "for (e in exprs) if (is.call(e) && identical(e[[1]], as.name('<-')) && "
        "identical(e[[2]], as.name('strand_direction'))) eval(e); "
        "cat(strand_direction(c('+', '1', '-', '-1', '?', '', NA)), sep=',')"
    )
    out = subprocess.run([rscript, "-e", expr], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "1,1,-1,-1,0,0,0"


def test_r_refuses_an_empty_bgc_alias(tmp_path: Path) -> None:
    rscript = _rscript()
    data = tmp_path / "sidecar.csv"
    data.write_text(
        "panel,locus_tag,order,start,end,strand,role,label_displayed\n"
        "Example_sp / CONTIG_1.1 / region001 / ,g1,1,100,1100,+,other,YES\n")
    out = subprocess.run([rscript, str(LOCUS_R), str(data), str(tmp_path / "out")],
                         capture_output=True, text=True)
    assert out.returncode != 0
    assert "not a full strain / node / region / BGC identity" in out.stderr
    assert not (tmp_path / "out.svg").exists()
