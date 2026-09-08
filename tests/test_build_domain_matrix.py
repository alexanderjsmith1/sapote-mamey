"""v9.7.221: cross-strain domain census — vocab single-sourced from MAMEY_MARKERS, density-normalised,
core/accessory/private split. Hermetic: synthetic 2-strain cohort."""
import csv, json, os, tempfile, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import build_domain_matrix as B

def _pkg(root, sid, gbp, domain_rows):
    d = os.path.join(root, sid, "package"); os.makedirs(d)
    json.dump({"strain_id": sid, "assembly": {"genome_bp": gbp, "assembly_tier": "GOOD"}},
              open(os.path.join(d, "manifest.json"), "w"))
    with open(os.path.join(d, f"{sid}_gene_by_gene_all_bgcs.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["locus_tag", "sec_met_domains"])
        for r in domain_rows:
            w.writerow(["g", r])
    return d

def test_matrix_split_density_and_vocab():
    with tempfile.TemporaryDirectory() as root:
        # AS-A: PKS_KS + halogenase (shared KS, private halogenase); AS-B: PKS_KS only
        _pkg(root, "AS-A", 5_000_000, ["PKS_KS;AMP-binding", "halogenase"])
        _pkg(root, "AS-B", 10_000_000, ["PKS_KS"])
        vocab = B._vocab()
        assert vocab, "vocab must be single-sourced from MAMEY_MARKERS"
        strains, all_domains, split = B.build([root], vocab)
        assert len(strains) == 2
        # PKS_KS present in both -> core; halogenase in one -> private
        assert "PKS_KS" in split["core"], split
        assert "halogenase" in split["private"], split
        # function mapping came from MAMEY_MARKERS
        assert B._categorize("halogenase", vocab) == "halogenation"
        assert B._categorize("PKS_KS", vocab) == "PKS"
        # density normalises for genome size: AS-B has 1 KS over 10 Mbp = 0.1/Mbp
        with tempfile.TemporaryDirectory() as out:
            B.write_outputs(strains, all_domains, split, vocab, out)
            rows = {r["domain"]: r for r in csv.DictReader(open(os.path.join(out, "domain_matrix_density_per_mbp.csv")))}
            assert abs(float(rows["PKS_KS"]["AS-B"]) - 0.1) < 1e-6, rows["PKS_KS"]
