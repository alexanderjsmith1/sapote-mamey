"""Engine tests for mamey/tailoring_extract.py + mamey/data/tailoring_families.json (VGP-400).

IN-TREE: imports the INSTALLED module and reads the INSTALLED registry, so these assert the behavior
of the tree they ship in. Synthetic GBK fixtures only (no cohort strain IDs).

Proves the design-critical mechanism separation: tailoring enzymes are WHOLE-CDS `sec_met_domain`
tags, NOT aSDomains — an aSDomain-only feature must not satisfy a family, and matching is EXACT
(substring matching would replicate the documented ks_phylogeny "pks" bug).

Claim-safety: family membership = CAPACITY context, never a modification/identity claim.
"""
import json
from pathlib import Path

import pytest

from mamey import tailoring_extract as T

_Q = " " * 21
_F = " " * 5
HALO_SEQ = "M" + "AKLVWEG" * 60     # 421 aa — inside the halogenase window

GBK = (
    f"{_F}CDS             1..1266\n"
    f'{_Q}/locus_tag="ctg1_10"\n'
    f'{_Q}/sec_met_domain="Trp_halogenase (E-value: 1.1e-100, bitscore: 300)"\n'
    f'{_Q}/translation="{HALO_SEQ}"\n'
    f"{_F}CDS             2000..2500\n"
    f'{_Q}/locus_tag="ctg1_11"\n'
    f'{_Q}/sec_met_domain="Glycos_transf_2 (E-value: 2e-30)"\n'
    f'{_Q}/translation="{"M" + "GSTQRPW" * 50}"\n'
    # an aSDomain feature naming a tailoring family must NOT be extracted (mechanism separation)
    f"{_F}aSDomain        3000..3300\n"
    f'{_Q}/aSDomain="Trp_halogenase"\n'
    f'{_Q}/locus_tag="ctg1_12"\n'
    f'{_Q}/translation="{"M" + "AAAAAAA" * 50}"\n'
    # substring trap: a tag CONTAINING a registry tag must not match
    f"{_F}CDS             4000..4400\n"
    f'{_Q}/locus_tag="ctg1_13"\n'
    f'{_Q}/sec_met_domain="XTrp_halogenaseY (E-value: 1e-5)"\n'
    f'{_Q}/translation="{"M" + "CDEFGHI" * 50}"\n'
)


def _gbk_dir(tmp_path, name="AS-1_NODE_1_region001.gbk"):
    d = tmp_path / "gbks"
    d.mkdir(exist_ok=True)
    (d / name).write_text(GBK)
    return d


def test_installed_registry_loads_and_every_tag_carries_survey_provenance():
    reg = T.load_registry()
    assert "halogenase" in reg and "Trp_halogenase" in reg["halogenase"]["tags"]
    for fam, ent in reg.items():
        assert ent["tags"], f"{fam} has no tags"
        lo, hi = ent["length_window"]
        assert lo < hi, f"{fam} malformed length_window"
        for tag in ent["tags"]:
            assert ent.get("_seen", {}).get(tag, 0) > 0, \
                f"{fam}:{tag} lacks an on-disk survey receipt (_seen) — no invented tags"


def test_malformed_registry_is_refused(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"x": {"tags": [], "length_window": [1, 2]}}')
    with pytest.raises(T.TailoringExtractError, match="REGISTRY_INVALID"):
        T.load_registry(bad)
    bad.write_text('{"x": {"tags": ["t"], "length_window": [5, 2]}}')
    with pytest.raises(T.TailoringExtractError, match="length_window"):
        T.load_registry(bad)


def test_unknown_family_refusal_names_the_known_set(tmp_path):
    with pytest.raises(T.TailoringExtractError, match="UNKNOWN_FAMILY.*halogenase"):
        T.extract_tailoring_enzymes(_gbk_dir(tmp_path), families=("not_a_family",))


def test_exact_tag_extraction_with_receipts_and_mechanism_separation(tmp_path):
    res = T.extract_tailoring_enzymes(_gbk_dir(tmp_path),
                                      families=("halogenase", "glycosyltransferase"))
    assert sorted(e["family"] for e in res["enzymes"]) == ["glycosyltransferase", "halogenase"]
    halo = next(e for e in res["enzymes"] if e["family"] == "halogenase")
    # gene-level-guard receipt: locus, exact tag, E-value
    assert (halo["locus_tag"], halo["matched_tag"], halo["evalue"]) == \
           ("ctg1_10", "Trp_halogenase", "1.1e-100")
    assert halo["translation"] == HALO_SEQ
    loci = {e["locus_tag"] for e in res["enzymes"]}
    assert "ctg1_12" not in loci, "an aSDomain feature must NOT satisfy a whole-CDS tailoring family"
    assert "ctg1_13" not in loci, "substring tag match must NOT fire (the 'pks'-bug guard)"
    assert res["family_counts"] == {"halogenase": 1, "glycosyltransferase": 1}


def test_strain_internal_gate_fails_closed(tmp_path):
    d = _gbk_dir(tmp_path)
    (d / "AS-2_NODE_9_region001.gbk").write_text(GBK)
    with pytest.raises(T.TailoringExtractError, match="STRAIN-INTERNAL ONLY.*multiple"):
        T.extract_tailoring_enzymes(d, families=("halogenase",))
    (d / "AS-2_NODE_9_region001.gbk").unlink()
    (d / "mystery.gbk").write_text(GBK)          # unparseable strain id -> fail closed
    with pytest.raises(T.TailoringExtractError, match="STRAIN-INTERNAL ONLY.*mystery"):
        T.extract_tailoring_enzymes(d, families=("halogenase",))


def test_registry_file_ships_in_tree_and_is_valid_json():
    p = Path(T.__file__).resolve().parent / "data" / "tailoring_families.json"
    assert p.exists(), "mamey/data/tailoring_families.json must ship with the module"
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert "_comment" in raw and len([k for k in raw if k != "_comment"]) >= 7
