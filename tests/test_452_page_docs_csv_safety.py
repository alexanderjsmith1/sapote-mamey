"""Page table output preserves ordinary names and escapes spreadsheet formulas."""
import csv
import json
from tools.protein_pcoa_page_docs import write_page_docs


def page_inputs(out):
    rec = dict(set="SYN", panel="P", prefix="SYN_PAGE", page=["pcoa"],
               title="Synthetic page", legend={"iso_low": "query, low"},
               cohort_genomes={"SYN-970": 2}, genome_numbers={"SYN-970": 1},
               n_cohort_points=2, n_low=1, n_mid=1, n_ref_centroids=1, n_ref=2,
               n_reference_genomes=1, n_mibig_centroids=0, n_mibig=0,
               label_below=50, mid_below=80, labels={}, min_text={"print_width": 7.2},
               label_rule="synthetic", placement="synthetic", leader_max_in=.5, final_draws={})
    (out / "LABELS_SYN_P_PAGE.tsv").write_text("drawn\tstrain\n")
    (out / "SYN_PAGE_min_text_check.json").write_text(json.dumps(dict(status="FIXTURE", text_runs=1, smallest_pt=8)))
    meta = [{"strain": "SYN-971", "source": "reference"}, {"strain": "SYN-971", "source": "reference"}]
    return rec, {"args": {}}, meta


def test_page_docs_guards_display_names_and_keeps_table_shape(tmp_path):
    rec, render, meta = page_inputs(tmp_path)
    outputs = write_page_docs(tmp_path, rec, render, meta, {"SYN-970": "=1+1"}, None, "2000-01-01")
    with outputs["genomes"].open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert rows == [
        {"genome": "SYN-970", "role": "cohort", "genome_number": "1", "display_name": "'=1+1", "proteins_in_set": "2"},
        {"genome": "SYN-971", "role": "reference (reference)", "genome_number": "", "display_name": "", "proteins_in_set": "2"}]
    assert b"\r\n" not in outputs["genomes"].read_bytes()


def test_page_docs_preserves_quoted_unicode_name(tmp_path):
    rec, render, meta = page_inputs(tmp_path)
    name = 'Synthetic "quoted" café\tname'
    outputs = write_page_docs(tmp_path, rec, render, meta, {"SYN-970": name}, None, "2000-01-01")
    with outputs["genomes"].open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    assert rows[0]["display_name"] == name
    assert outputs["genomes"].read_bytes().endswith(b"SYN-971\treference (reference)\t\t\t2\n")
