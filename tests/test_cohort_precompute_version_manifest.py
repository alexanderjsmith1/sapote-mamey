"""v9.7.229: cohort-precompute emits VERSION.json + MANIFEST.csv (save-data protocol) so a fresh chat
can validate the store on load."""
import csv, json, os, tempfile, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

def test_emit_version_and_manifest():
    import build_cohort_precompute as B
    with tempfile.TemporaryDirectory() as out:
        counts = {"COHORT_BGC_FULL_TALLY.csv": 3}
        with open(os.path.join(out, "COHORT_BGC_FULL_TALLY.csv"), "w") as f:
            f.write("h\na\nb\nc\n")
        B._emit_version_and_manifest(out, counts, n_strains=2)
        v = json.load(open(os.path.join(out, "VERSION.json")))
        assert v["layer"] == "cohort_precompute" and v["n_strains"] == 2
        assert "assembly_locator" in v["join_key"] and "NOT portable" in v["join_key"]
        m = list(csv.DictReader(open(os.path.join(out, "MANIFEST.csv"))))
        assert m[0]["file"] == "COHORT_BGC_FULL_TALLY.csv" and int(m[0]["rows"]) == 3
