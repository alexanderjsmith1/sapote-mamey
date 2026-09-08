"""Tests for the dual-pass claims-ledger tooling (roadmap #8). Freeze-safe reconciliation tooling."""
import csv

try:
    from mamey import dualpass_ledger as dl
except ImportError:
    import dualpass_ledger as dl


def test_vocab_loads_and_has_the_four_axes():
    v = dl.load_vocab()
    for a in ("ripp_subclass", "genuine_vs_housekeeping", "lead_flag", "nr_split"):
        assert a in v


def test_lanthipeptide_class_enum():
    v = dl.load_vocab()
    assert dl.normalize_value("ripp_subclass", "Class-I lanthipeptide", v) == "lanthipeptide_i"
    assert dl.normalize_value("ripp_subclass", "class iii lanthipeptide", v) == "lanthipeptide_iii"
    assert dl.normalize_value("ripp_subclass", "lanthipeptide (unspecified)", v) == "lanthipeptide_unspec"


def test_thiopeptide_azole_compound_rule():
    v = dl.load_vocab()
    assert dl.normalize_value("ripp_subclass", "azol-containing RiPP", v) == "thiopeptide_azole"
    assert dl.normalize_value("ripp_subclass", "LAP", v) == "thiopeptide_azole"


def test_lead_negation_guard():
    v = dl.load_vocab()
    assert dl.normalize_value("lead_flag", "RiPP lead", v) == "lead"
    assert dl.normalize_value("lead_flag", "not a lead", v) == "not_lead"


def test_nr_split_and_housekeeping_enum():
    v = dl.load_vocab()
    assert dl.normalize_value("nr_split", "genus-conserved (98% WP_)", v) == "genus_conserved"
    assert dl.normalize_value("nr_split", "divergent core", v) == "divergent"
    assert dl.normalize_value("genuine_vs_housekeeping", "cofactor/redox miscall", v) == "housekeeping"


def _ledger(path, rows):
    cols = ["claim_id", "task", "strain", "bgc_id", "locus_tag", "assertion_type", "value",
            "evidence", "confidence", "engine"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in rows:
            d = {c: "" for c in cols}
            d.update(r)
            w.writerow(d)


def test_normalize_turns_lexical_noise_into_agreement(tmp_path):
    cl = tmp_path / "claude.tsv"
    cx = tmp_path / "codex.tsv"
    _ledger(cl, [{"task": "ripp", "strain": "AS-1", "bgc_id": "BGC1", "locus_tag": "ctg1_1",
                  "assertion_type": "ripp_subclass", "value": "Class-I lanthipeptide"}])
    _ledger(cx, [{"task": "ripp", "strain": "AS-1", "bgc_id": "BGC1", "locus_tag": "ctg1_1",
                  "assertion_type": "ripp_subclass", "value": "class i lanthipeptide (LanBC)"}])
    raw = dl.merge(str(cl), str(cx), out_dir=str(tmp_path / "raw"), normalize=False)
    norm = dl.merge(str(cl), str(cx), out_dir=str(tmp_path / "norm"), normalize=True)
    assert raw["AGREE"] == 0
    assert norm["AGREE"] == 1  # canonicalised -> real agreement


def test_excluded_strain_auto_voids(tmp_path):
    cl = tmp_path / "c.tsv"
    cx = tmp_path / "x.tsv"
    row = {"task": "t", "strain": "AS-920", "bgc_id": "BGC1", "locus_tag": "ctg1_1",
           "assertion_type": "ripp_subclass", "value": "lasso"}
    _ledger(cl, [row])
    _ledger(cx, [row])
    res = dl.merge(str(cl), str(cx), out_dir=str(tmp_path), normalize=True)
    assert res["auto_resolved"] == 1  # VOID:excluded-strain fired


def test_claim_ceiling_rejects_identity_assertions(tmp_path):
    cl = tmp_path / "c2.tsv"
    cx = tmp_path / "x2.tsv"
    row = {"task": "t", "strain": "AS-1", "bgc_id": "BGC1", "locus_tag": "ctg1_1",
           "assertion_type": "product_identity", "value": "vancomycin"}
    _ledger(cl, [row])
    _ledger(cx, [row])
    res = dl.merge(str(cl), str(cx), out_dir=str(tmp_path), normalize=True)
    assert res["auto_resolved"] == 1  # REJECT:claim-ceiling fired

