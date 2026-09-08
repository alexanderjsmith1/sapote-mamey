"""v9.7.115: systemic substring-containment fixes (the recurring false-positive bug class).

Two confirmed instances found by the systemic grep and fixed:
  1. gene_topology.classify — 'p450' bare substring matched 'comp450X'.
  2. evidence_conservation_audit.check_nrps_substrates — a short NRPS substrate token ('pip')
     bare-substring-matched inside unrelated package words ('equipped'), FALSELY reporting a
     dropped substrate as conserved in a WIRED safety gate.
"""
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


# ---- gene_topology p450 boundary ----

def test_gene_topology_p450_not_substring():
    import gene_topology as G
    assert G.classify(["comp450X_domain"]) != ("additional", "P450")  # false positive closed
    assert G.classify(["Cytochrome_p450"]) == ("additional", "P450")  # real token still matches
    assert G.classify(["cyp_p450_1"]) == ("additional", "P450")        # _-bounded still matches


# ---- evidence_conservation_audit false-conservation ----

def test_evidence_gate_catches_dropped_short_substrate():
    import evidence_conservation_audit as E
    raw = {"records": [{"modules": {"antismash.modules.nrps_pks":
                                    {"consensus": {"ctg1_A1": "pip"}}}}]}
    # 'pip' dropped from the package, but 'equipped' coincidentally contains the substring
    blob = json.dumps({"note": "the run was well equipped", "bgcs": []})
    name, seen, dropped = E.check_nrps_substrates(raw, blob)
    assert seen == 1
    assert dropped, "dropped short substrate falsely reported conserved (substring false-positive)"


def test_evidence_gate_conserves_present_substrate():
    import evidence_conservation_audit as E
    raw = {"records": [{"modules": {"antismash.modules.nrps_pks":
                                    {"consensus": {"ctg1_A1": "pip"}}}}]}
    blob = json.dumps({"consensus": {"ctg1_A1": "pip"}})   # genuinely present
    name, seen, dropped = E.check_nrps_substrates(raw, blob)
    assert seen == 1 and not dropped


def test_token_in_blob_boundary():
    import evidence_conservation_audit as E
    blob = json.dumps({"x": "equipped pipeline", "y": "Hpg"})
    assert not E._token_in_blob("pip", blob)   # inside equipped/pipeline -> not a real hit
    assert E._token_in_blob("Hpg", blob)       # real bounded value -> hit
