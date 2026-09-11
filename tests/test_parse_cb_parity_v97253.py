"""RV-1 (v9.7.253 Review v2): pin the SHARED contract of the duplicated `parse_cb`.

`mamey/diagnostic_rescue.py` and `tools/build_reconstruction.py` each carry their own `parse_cb`.
`diagnostic_rescue`'s docstring calls it a "faithful port ... do not let them drift." On inspection
the block/accession/source/type/cum_score parsing IS identical, but the two have ALREADY diverged at
the hit-record schema:
    diagnostic_rescue -> hit = {"query", "subject", "blast_score": int}
    build_reconstruction -> hit = {"query", "subject", "pid": str, "score": str}
That divergence is plausibly intentional (each consumer needs different hit fields), so this test does
NOT assert full identity — that would falsely fail. It pins the genuinely-shared contract (accessions,
source/type/cum_score, and the SET of hit queries per accession) so drift in the shared skeleton is
caught, while the per-consumer hit fields are free to differ.

If you'd rather fully unify them: extract the shared block parser into one primitive both call, each
adding its own hit projection — then this test can be tightened to full identity.
"""
import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


def _load(mod_name: str, rel: str):
    p = _REPO / rel
    sys.path.insert(0, str(p.parent))          # let build_reconstruction find _wbio, etc.
    sys.path.insert(0, str(_REPO))
    spec = importlib.util.spec_from_file_location(mod_name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_dr = _load("diagnostic_rescue_ut", "mamey/diagnostic_rescue.py")
_br = _load("build_reconstruction_ut", "tools/build_reconstruction.py")

# Minimal synthetic clusterblast region txt exercising 2 reference blocks + hit tables.
_FIXTURE = (
    ">>\n"
    "1. NZ_TEST00000001\n"
    "Source: Streptomyces testicus\n"
    "Type: t1pks\n"
    "Cumulative BLAST score: 1234.0\n"
    "Table of Blast hits (query gene, subject gene, %identity, blast score, ...)\n"
    "ctg1_10\tSUBJ_A\t72\t410\n"
    "ctg1_11\tSUBJ_B\t65\t388\n"
    "\n"
    ">>\n"
    "2. NZ_TEST00000002\n"
    "Source: Kitasatospora example\n"
    "Type: nrps\n"
    "Cumulative BLAST score: 88.5\n"
    "Table of Blast hits (query gene, subject gene, %identity, blast score, ...)\n"
    "GT350_26620\tSUBJ_C\t55\t210\n"
)


def _write(tmp_path) -> str:
    f = tmp_path / "region_cb.txt"
    f.write_text(_FIXTURE, encoding="utf-8")
    return str(f)


def test_shared_accession_and_score_contract_matches(tmp_path):
    p = _write(tmp_path)
    a = _dr.parse_cb(p)
    b = _br.parse_cb(p)
    assert set(a) == set(b), "accession sets diverged between the two parse_cb copies"
    for acc in a:
        assert a[acc]["source"] == b[acc]["source"], f"{acc}: source diverged"
        assert a[acc]["type"] == b[acc]["type"], f"{acc}: type diverged"
        assert a[acc]["cum_score"] == b[acc]["cum_score"], f"{acc}: cum_score diverged"


def test_shared_hit_query_set_matches(tmp_path):
    p = _write(tmp_path)
    a = _dr.parse_cb(p)
    b = _br.parse_cb(p)
    for acc in a:
        qa = {h["query"] for h in a[acc]["hits"]}
        qb = {h["query"] for h in b[acc]["hits"]}
        assert qa == qb, f"{acc}: hit-query set diverged (skeleton drift)"


def test_hit_schema_divergence_is_the_known_documented_one(tmp_path):
    # Documents (does not bless) the current per-consumer hit-field divergence, so a NEW/unexpected
    # change to either hit schema is visible here rather than silent.
    p = _write(tmp_path)
    a = _dr.parse_cb(p)
    b = _br.parse_cb(p)
    dr_hit = a["NZ_TEST00000001"]["hits"][0]
    br_hit = b["NZ_TEST00000001"]["hits"][0]
    assert set(dr_hit) == {"query", "subject", "blast_score"}
    assert isinstance(dr_hit["blast_score"], int)
    assert set(br_hit) == {"query", "subject", "pid", "score"}
