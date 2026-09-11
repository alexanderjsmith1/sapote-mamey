import pathlib, re
TSV=pathlib.Path(__file__).resolve().parent.parent/"mamey"/"data"/"outgroup_registry.tsv"
def _rows():
    return [l.split("\t") for l in TSV.read_text().splitlines() if l.strip() and not l.startswith("#") and not l.startswith("tree_scope")]
def test_real_accessions():
    for r in _rows():
        acc, status = r[5], r[6]
        if acc == "PROVISIONAL_16S_only":
            # 16S-only outgroup (per-genus 16S placement; genome accession TBD by design). Exempt from
            # the genome-accession rule, but a 16S-only row must be PROVISIONAL — never LOCKED.
            assert status == "PROVISIONAL", f"16S-only row must be PROVISIONAL, got {status!r}"
            continue
        assert re.fullmatch(r"GC[AF]_\d+\.\d+",acc), f"bad acc {acc}"
def test_outgroup_not_ingroup():
    for r in _rows(): assert r[3]!=r[1], f"outgroup==ingroup {r[1]}"
def test_scope_valid():
    for r in _rows(): assert r[0] in ("genus","family")


def test_reverified_accession_organism_names_are_consistent():
    expected = {
        "GCF_039528075.1": ("Catellatospora", "Catellatospora coxensis JCM 12951"),
        "GCA_018139085.1": ("Actinosynnema", "Actinosynnema pretiosum subsp. pretiosum"),
    }
    for row in _rows():
        if row[5] in expected:
            assert (row[3], row[4]) == expected[row[5]]
