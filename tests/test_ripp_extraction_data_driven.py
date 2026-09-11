"""RiPP extraction must be data-driven, not a hardcoded 4-family allowlist (investigation v9.7.99).

antiSMASH 8 detects more RiPP families than the original
(lanthipeptides, lassopeptides, sactipeptides, thiopeptides). The previous _ripp_from_rec iterated a
hardcoded tuple, so any other family (ranthipeptides, thioamitides, lipolanthines, …) had its
precursor/core calls silently dropped. _ripp_from_rec now iterates every antismash.modules.<family>
carrying a 'motifs' dict; non-RiPP modules self-exclude (their entries lack a 'core').
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.antismash_evidence import _ripp_from_rec  # noqa: E402


def _rec(modules):
    return {"id": "ctg1", "modules": modules}


def _motif(core):
    return {"core": core, "peptide_class": "test", "leader": "ML", "tail": ""}


def test_known_family_still_extracted():
    out = []
    _ripp_from_rec(_rec({"antismash.modules.lanthipeptides": {"motifs": {"ctg1_5": [_motif("SCAEC")]}}}), "f.gbk", out)
    assert len(out) == 1 and out[0]["ripp_family"] == "lanthipeptides" and out[0]["core"] == "SCAEC"


def test_previously_dropped_family_now_captured():
    """ranthipeptides was NOT in the old hardcoded tuple — it must now be captured."""
    out = []
    _ripp_from_rec(_rec({"antismash.modules.ranthipeptides": {"motifs": {"ctg1_9": [_motif("GGSWA")]}}}), "f.gbk", out)
    assert len(out) == 1, "ranthipeptides core was dropped — data-driven extraction failed"
    assert out[0]["ripp_family"] == "ranthipeptides" and out[0]["core"] == "GGSWA"


def test_multiple_families_in_one_record():
    out = []
    _ripp_from_rec(_rec({
        "antismash.modules.thiopeptides": {"motifs": {"ctg1_2": [_motif("SCTTCV")]}},
        "antismash.modules.lipolanthines": {"motifs": {"ctg1_7": [_motif("MAGKLA")]}},
    }), "f.gbk", out)
    fams = {h["ripp_family"] for h in out}
    assert fams == {"thiopeptides", "lipolanthines"}, fams


def test_non_ripp_modules_excluded():
    """A non-RiPP module (no 'core' in its entries) must contribute nothing."""
    out = []
    _ripp_from_rec(_rec({
        "antismash.modules.nrps_pks": {"motifs": {"ctg1_1": [{"consensus": "ala-val"}]}},  # no core
        "antismash.modules.clusterblast": {"results": []},
    }), "f.gbk", out)
    assert out == []
