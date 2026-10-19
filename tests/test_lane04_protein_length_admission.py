"""Malformed counts must not weaken the existing one-aa length fallback."""
import pytest
from mamey.protein_binding import bind_one,genome_index,protein_sha256

@pytest.mark.parametrize("value",["inf","-inf","1e309","nan",101.9,99.9,True,0,-1])
def test_malformed_length_is_unbound(value):
    tags,how=bind_one("syn_gene","",value,{}, {"syn_gene":100})
    assert tags==[] and how.startswith("unbound")

@pytest.mark.parametrize("value,accepted",[(99,True),(100,True),(101,True),(98,False),(102,False),("100.0",True)])
def test_existing_integer_slack_unchanged(value,accepted):
    tags,how=bind_one("syn_gene","",value,{}, {"syn_gene":100})
    assert bool(tags)==accepted

def test_sequence_hash_wins_without_falling_back_on_equal_length_decoy():
    seqs={"syn_new_tag":"MAAAA","syn_duplicate":"MAAAA"}
    bysha,length=genome_index(seqs)
    assert bind_one("old_tag",protein_sha256("MAAAA"),None,bysha,length)==(["syn_new_tag","syn_duplicate"],"sha")
    assert bind_one("syn_new_tag",protein_sha256("MKKKK"),5,bysha,length)==([],"unbound_sha_not_in_genome")
