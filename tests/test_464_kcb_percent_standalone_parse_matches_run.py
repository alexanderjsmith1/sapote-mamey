"""A standalone parse reads the same KCB percent as the run path, in every JSON mode.

The percent rides the record pass that TIGRFAM requests. A standalone parse that skipped that
pass left every percent unread in off mode, so architecture grades differed from `run`.
"""
import io
import json
import zipfile

import pytest

pytest.importorskip("Bio")
from Bio import SeqIO  # noqa: E402
from Bio.Seq import Seq  # noqa: E402
from Bio.SeqFeature import SeqFeature, SimpleLocation  # noqa: E402
from Bio.SeqRecord import SeqRecord  # noqa: E402

from mamey.antismash_evidence import apply_evidence_to_bgcs
from mamey.parsers import parse_antismash_evidence_status, parse_bgcs_from_zip

CONTIG = "NODE_1_length_613749_cov_47.990239"


def _zip(path):
    rec = SeqRecord(Seq("ACGT" * 3000), id=CONTIG, name="NODE_1", description="synthetic")
    rec.annotations["molecule_type"] = "DNA"
    rec.features = [SeqFeature(SimpleLocation(0, 12000), type="region",
                               qualifiers={"region_number": ["1"], "product": ["ectoine"]})]
    gbk = io.StringIO(); SeqIO.write(rec, gbk, "genbank")
    ranking = [[{"accession": "BGC0000853.3", "proteins": []}, {"similarity": 80, "hits": 4}]]
    record = {"id": CONTIG, "name": CONTIG, "modules": {"antismash.modules.clusterblast": {
        "knowncluster": {"results": [{"region_number": 1, "total_hits": 1, "ranking": ranking}]}}}}
    txt = ("ClusterBlast scores for x\n\nSignificant hits: \n1. BGC0000853.3\tectoine\n\n\nDetails:\n\n>>\n"
           "1. BGC0000853.3\nSource: ectoine\nType: other:other\n"
           "Number of proteins with BLAST hits to this cluster: 4\nCumulative BLAST score: 1211.0\n\n")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(f"{CONTIG}.region001.gbk", gbk.getvalue())
        zf.writestr("genome.json", json.dumps({"records": [record]}))
        zf.writestr(f"knownclusterblast/{CONTIG}_c1.txt", txt)
    return path


@pytest.mark.parametrize("mode", ["off", "bounded"])
def test_standalone_parse_reads_the_percent_like_run(tmp_path, mode):
    path = _zip(tmp_path / "in.zip")
    standalone = parse_bgcs_from_zip(path, json_mode=mode)
    evidence = parse_antismash_evidence_status(path, json_mode=mode)
    run_path = parse_bgcs_from_zip(path, json_mode=mode, evidence=evidence)
    apply_evidence_to_bgcs(run_path, evidence)
    assert len(standalone) == len(run_path) == 1
    assert (standalone[0].kcb_similarity_pct, standalone[0].kcb_similarity_state) == (80.0, "PCT_OBSERVED")
    assert standalone[0].kcb_similarity_pct == run_path[0].kcb_similarity_pct
    assert standalone[0].architecture_confidence == run_path[0].architecture_confidence
