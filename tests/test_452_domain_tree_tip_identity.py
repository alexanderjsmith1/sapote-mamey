"""Domain-tree staging needs one complete, unique identity per tip before it writes FASTA (P300-072)."""
from pathlib import Path

import pytest

from mamey import domain_tree as DT


def _dom(i, seq, **kw):
    d = {"strain": "SYN-1", "node": f"NODE_{i}", "region": "region001",
         "locus_tag": f"ctg{i}_1", "domain_id": f"d{i}", "translation": seq}
    d.update(kw)
    return d


def _four():
    return [_dom(i, "M" + "ACDEFGH" * (45 + i)) for i in range(1, 5)]


def test_two_sequences_with_one_header_are_refused(tmp_path):
    doms = _four() + [_dom(1, "M" + "PQRSTVW" * 50)]   # same identity as the first, different sequence
    with pytest.raises(DT.DomainTreeError, match="STAGE_DUPLICATE_HEADER"):
        DT.stage_domains(doms, "PKS_KS", tmp_path / "o")
    assert not (tmp_path / "o" / "PKS_KS_staged.fasta").exists()


@pytest.mark.parametrize("damage", ["no_strain", "no_node", "blank_locus", "node_placeholder"])
def test_incomplete_identity_is_refused(tmp_path, damage):
    doms = _four()
    if damage == "no_strain":
        del doms[0]["strain"]
    if damage == "no_node":
        del doms[0]["node"]
    if damage == "blank_locus":
        doms[0]["locus_tag"] = " "
    if damage == "node_placeholder":
        doms[0]["node"] = "NODE_?"
    with pytest.raises(DT.DomainTreeError, match="STAGE_INCOMPLETE_IDENTITY"):
        DT.stage_domains(doms, "PKS_KS", tmp_path / "o")


def test_same_sequence_at_two_loci_is_still_a_dedup_receipt(tmp_path):
    doms = _four()
    doms.append(_dom(9, doms[0]["translation"]))
    out = DT.stage_domains(doms, "PKS_KS", tmp_path / "o")
    assert out["n_staged"] == 4 and out["n_dedup"] == 1
    headers = [line for line in Path(out["fasta"]).read_text().splitlines() if line.startswith(">")]
    assert len(headers) == len(set(headers)) == 4
    assert "DUP_OF:" in Path(out["provenance"]).read_text()


def test_short_excluded_fragment_does_not_block_staging(tmp_path):
    doms = _four() + [{"translation": "MKV"}]   # below the window, so it never becomes a tip
    out = DT.stage_domains(doms, "PKS_KS", tmp_path / "o")
    assert out["n_staged"] == 4 and out["n_short_excluded"] == 1
