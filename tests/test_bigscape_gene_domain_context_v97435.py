import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gene_context = load("deliverable_tools/bigscape_gene_domain_context.py", "bigscape_gene_domain_context_test")


def write_tsv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def test_gene_domain_context_uses_complete_identities_and_bound_gbks(tmp_path):
    membership = tmp_path / "membership.tsv"
    rows = []
    gbks = tmp_path / "gbks"
    gbks.mkdir()
    for record_id, strain, node, alias in [
        ("1", "DEMO-A", "contig_alpha", "BGC001"),
        ("2", "DEMO-B", "contig_beta", "BGC002"),
    ]:
        identity = f"{strain} / {node} / region001 / {alias}"
        rows.append({
            "family_id": "12", "record_id": record_id, "strain": strain,
            "full_node_or_contig": node, "region": "region001", "bgc_alias": alias,
            "identity_status": "COMPLETE", "locus_display_with_hold": identity,
            "boundary_state": "INTERIOR", "source_path": "portable.gbk",
        })
        (gbks / f"{strain}_{node}_region001_{alias}.gbk").write_text(
            "LOCUS       FIXTURE                 900 bp    DNA     linear\n"
            "FEATURES             Location/Qualifiers\n"
            "     CDS             1..300\n"
            "                     /locus_tag=\"gene1\"\n"
            "                     /gene_kind=\"biosynthetic\"\n"
            "                     /translation=\"MABCDEFGHIJKLMNPQRSTVWYABCDEFGHIJKLMNPQRSTVWY\"\n"
            "     aSDomain        10..250\n"
            "                     /locus_tag=\"gene1\"\n"
            "                     /aSDomain=\"PKS_KS\"\n"
            "     CDS             350..700\n"
            "                     /locus_tag=\"gene2\"\n"
            "                     /translation=\"MNPQRSTVWYABCDEFGHIJKLMNPQRSTVWYABCDEFGHIJKL\"\n"
            "//\n"
        )
    write_tsv(membership, rows)
    edges = tmp_path / "edges.tsv"
    write_tsv(edges, [{"record_a_id": "1", "record_b_id": "2", "distance": "0.25"}])
    receipt = gene_context.build_context(membership, edges, "12", "DEMO-A", tmp_path / "out", gbks)
    assert receipt["member_count"] == 2
    assert receipt["reciprocal_best_pairs"] == 2
    summary = (tmp_path / "out" / "GCF_LOCUS_COMPARISON_SUMMARY.tsv").read_text()
    assert "DEMO-A / contig_alpha / region001 / BGC001" in summary
    assert "DEMO-B / contig_beta / region001 / BGC002" in summary
    assert all(not Path(item["file"]).is_absolute() for item in receipt["sources"])
