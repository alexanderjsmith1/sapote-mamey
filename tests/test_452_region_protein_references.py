"""Card attine_452_region_protein_references: tools/region_protein_references.py builds the B03 input table.

Public genomes are filtered by the bee and moss Fig. 3B rules: reference role only (never isolate or SID rows),
loose runs, at least 10 regions, one copy per genome (same accession base, or same aa and region totals). Frozen
synthetic fixture: tests/fixtures/region_protein_references_classified_SYN.tsv. No study IDs.
"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/region_protein_references.py"
FIXTURE = ROOT / "tests/fixtures/region_protein_references_classified_SYN.tsv"
spec = importlib.util.spec_from_file_location("region_protein_references_t", TOOL)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def run(tmp_path, isolates):
    g, t, out = tmp_path / "genera.tsv", tmp_path / "totals.tsv", tmp_path / "b03.tsv"
    g.write_text("strain\tgenus\n" + "".join(f"{s}\t{x}\n" for s, x, _ in isolates))
    t.write_text("strain\tamino_acids\tmissing_CDS_lengths\n" + "".join(f"{s}\t{a}\t0\n" for s, _, a in isolates))
    assert mod.main(["--classified", str(FIXTURE), "--isolate-genera", str(g), "--isolate-totals", str(t), "--out", str(out)]) == 0
    rows = list(csv.DictReader(out.open(), delimiter="\t"))
    return rows, json.loads((tmp_path / "b03_RUN_INFO.json").read_text()), list(csv.DictReader((tmp_path / "b03_EXCLUDED.tsv").open(), delimiter="\t"))


def test_filters_keep_one_copy_of_each_loose_whole_public_genome(tmp_path):
    rows, info, excluded = run(tmp_path, [("SYN-971", "Synthetica", "170000"), ("SYN-972", "Exemplaria", "310000")])
    refs = [r["strain"] for r in rows if r["role"] == "reference"]
    assert set(refs) == {"Synthetica_alpha_GCF_000000001_1", "Synthetica_beta_SYNB00000000.1", "Exemplaria_zeta_SYNZ00000000.1"}
    reasons = {r["genome_key"]: r["reason"] for r in excluded}
    assert reasons["Synthetica_alpha_copy_GCA_000000001_1"] == "duplicate copy"      # same accession base
    assert reasons["Synthetica_gamma_SYNC00000000.1"] == "duplicate copy"            # same aa and regions
    assert reasons["Synthetica_delta_SYND00000000.1"].startswith("not a whole genome")
    assert reasons["Synthetica_eps_SYNE00000000.1"] == "not loose"
    assert "Synthetic_sid_collection_row" not in refs and "SYN-973" not in refs and "Otheria_eta_SYNH00000000.1" not in refs
    assert info["references_per_genus"] == {"Exemplaria": 1, "Synthetica": 2}
    assert info["classified_sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert info["rules"]["min_regions"] == 10 and info["rules"]["strictness"] == "loose" and info["rules"]["role"] == "reference"


def test_isolates_lead_and_a_genus_without_public_genomes_keeps_its_isolate(tmp_path):
    rows, info, _ = run(tmp_path, [("SYN-971", "Synthetica", "170000"), ("SYN-974", "Fabricaceae", "220000")])
    assert [r["strain"] for r in rows if r["role"] == "isolate"] == ["SYN-971", "SYN-974"]
    assert info["references_per_genus"]["Fabricaceae"] == 0
    assert all(r["missing_CDS_lengths"] == "0" for r in rows)


def test_refusals(tmp_path):
    g, t = tmp_path / "g.tsv", tmp_path / "t.tsv"
    g.write_text("strain\tgenus\nSYN-971\tSynthetica\n")
    t.write_text("strain\tamino_acids\tmissing_CDS_lengths\nSYN-972\t1\t0\n")
    with pytest.raises(ValueError, match="different strains"):
        mod.main(["--classified", str(FIXTURE), "--isolate-genera", str(g), "--isolate-totals", str(t), "--out", str(tmp_path / "o.tsv")])
    (tmp_path / "o2.tsv").write_text("")
    with pytest.raises(FileExistsError):
        mod.main(["--classified", str(FIXTURE), "--isolate-genera", str(g), "--isolate-totals", str(g), "--out", str(tmp_path / "o2.tsv")])
