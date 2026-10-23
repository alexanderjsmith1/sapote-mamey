import pytest
from tools.region_identity_dotplot import prepare

def files(tmp_path,focus='yes'):
    m=tmp_path/'map.tsv';m.write_text('genome_id\tassembly_key\tfocus\nSYN_A\tassembly_1\tyes\nSYN_B\tassembly_1\t'+focus+'\n')
    g=tmp_path/'genes.tsv';g.write_text('query_id\tlabel\tbest_streptomyces_identity\nSYN_query\tSynthetic protein\t42\n')
    h=tmp_path/'hits.tsv';h.write_text('SYN_query\tSYN_A|p\t60\nSYN_query\tSYN_B|p\t80\n')
    return m,g,h

def test_one_best_hit_per_reviewed_assembly_group(tmp_path):
    genes,best,states=prepare(*files(tmp_path))
    assert best['SYN_query']=={'assembly_1':80} and states['assembly_1']=='yes'
    assert genes[0]['best_streptomyces_identity']=='42'

def test_conflicting_focus_memberships_refuse(tmp_path):
    with pytest.raises(ValueError):prepare(*files(tmp_path,'no'))

def test_unknown_genome_is_not_silently_dropped(tmp_path):
    m,g,h=files(tmp_path);h.write_text('SYN_query\tSYN_MISSING|p\t80\n')
    with pytest.raises(ValueError):prepare(m,g,h)
