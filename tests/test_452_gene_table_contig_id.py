"""Card attine_452_gene_table_contig_id: gap_rescue_gene_table.genome_cds names contigs as the engine does.

Biopython's rec.id is the VERSION line, which drops a 0 right after the point of a SPAdes coverage (cov_28.095673 reads
cov_28.95673). The gap-rescue run records the engine's name (mamey.parsers._record_contig_id), so the window table
refused with "no matched gene on the core contig". genome_cds now uses the engine's name. Synthetic data only.
"""
import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

Bio = pytest.importorskip("Bio")
from Bio import SeqIO  # noqa: E402
from Bio.Seq import Seq  # noqa: E402
from Bio.SeqFeature import FeatureLocation, SeqFeature  # noqa: E402
from Bio.SeqRecord import SeqRecord  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
spec = importlib.util.spec_from_file_location("grgt_452c", HERE / "tools" / "gap_rescue_gene_table.py")
gt = importlib.util.module_from_spec(spec); spec.loader.exec_module(gt)
NODE = "NODE_2_length_9000_cov_28.095673"


def test_a_coverage_with_a_zero_after_the_point_keeps_its_name(tmp_path):
    rec = SeqRecord(Seq("A" * 9000), id=NODE, name=NODE, description=NODE, annotations={"molecule_type": "DNA"})
    rec.features.append(SeqFeature(FeatureLocation(100, 1000, strand=1), type="CDS",
                                   qualifiers={"locus_tag": ["ctg2_1"], "translation": ["M" * 300]}))
    rec.features.append(SeqFeature(FeatureLocation(50, 5000), type="region",
                                   qualifiers={"region_number": ["1"], "product": ["NRPS"]}))
    gbk = tmp_path / "SYN-970.gbk"
    SeqIO.write([rec], gbk, "genbank")
    assert next(SeqIO.parse(str(gbk), "genbank")).id != NODE          # the Biopython reading this card works around
    zp = tmp_path / "SYN-970.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.write(gbk, "SYN-970.gbk")
    cds, products = gt.genome_cds(zp)
    assert cds["ctg2_1"]["contig"] == NODE and products[(NODE, 1)] == "NRPS"
