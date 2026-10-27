from pathlib import Path
from types import SimpleNamespace
import importlib.util,subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('failed',[True,False])
def test_deposited_subject_search_failure_is_not_a_blank_result(tmp_path,monkeypatch,failed):
    spec=importlib.util.spec_from_file_location('subject_check',ROOT/'tools/sixteen_s_similarity_check.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    helper=SimpleNamespace(refseq_16s_blastdb=lambda p:p,blastdb_sequence_count=lambda *a:1,
                           ALL_RECORDS_FALLBACK=1,blastdb_receipt=lambda *a:{'synthetic':True})
    monkeypatch.setattr(m,'_shared_phylo16s',lambda:helper)
    monkeypatch.setattr(m.shutil,'which',lambda x:x)
    calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        if cmd[0]=='blastdbcmd':
            return subprocess.CompletedProcess(cmd,0,stdout='SYNTH_ACCESSION\tSyntheticGenus species reference\n',stderr='')
        return subprocess.CompletedProcess(cmd,2 if failed and '-subject' in cmd else 0,
                                           stdout='',stderr='synthetic subject search failure')
    monkeypatch.setattr(m.subprocess,'run',run)
    fasta=tmp_path/'query.fa';fasta.write_text('>SYNTHETIC_Q\nACGT\n')
    table=tmp_path/'table.tsv';table.write_text('strain\tgenus_16s\tclosest_type_strain\tsimilarity_percent\nSYNTHETIC_Q\tSyntheticGenus sp.\tSyntheticGenus species\t100\n')
    out=tmp_path/'result.tsv';args=['--fasta',str(fasta),'--table',str(table),'--db','synthetic_db','--out',str(out)]
    if failed:
        with pytest.raises(RuntimeError,match='blastn failed'):m.main(args)
        assert not out.exists() and not Path(str(out)+'.receipt.json').exists()
    else:assert m.main(args)==0 and out.exists()
    assert any('-subject' in call for call in calls)
