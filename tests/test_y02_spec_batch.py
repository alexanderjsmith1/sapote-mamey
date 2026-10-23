"""Synthetic end-to-end SPEC route; no DIAMOND or real-data figure."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_y02_multi_reference_gecco import mrc


def test_spec_synthetic_end_to_end_no_external_compute(tmp_path,monkeypatch):
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature,FeatureLocation
    from Bio import SeqIO
    regions=tmp_path/'regions';regions.mkdir()
    for name,organism in [('query','Genus synthetic'),('matched','Genus alpha'),('unplaced','Genus beta')]:
        record=SeqRecord(Seq('ATG'*1000),id=name,description=organism,
                         annotations={'molecule_type':'DNA','organism':organism})
        record.features=[SeqFeature(FeatureLocation(i*1000,i*1000+900,strand=1),type='CDS',
                         qualifiers={'translation':['M'*300],'locus_tag':[f't{i}'],'gene_kind':['biosynthetic']}) for i in range(2)]
        SeqIO.write(record,regions/f'{name}.gbk','genbank')
    spec=tmp_path/'SPEC.tsv'
    rows=['region_file\tlabel\taccession\trole\tidentity\tsha256']
    for name,role in [('query','query'),('matched','public'),('unplaced','public')]:
        identity='SYN-1 / synthetic_contig / region001 / BGC001' if role=='query' else name
        rows.append(f'{name}.gbk\tGenus {name}\t{name}\t{role}\t{identity}\t{mrc.rlc.sha_file(regions/(name+".gbk"))}')
    spec.write_text('\n'.join(rows)+'\n')
    monkeypatch.setattr(mrc,'region_db',lambda directory,temporary:Path(temporary)/'synthetic.dmnd')
    monkeypatch.setattr(mrc.rc,'search_mibig',lambda *args,**kwargs:{'ok':True,'hits':[
        {'qseqid':str(i),'sseqid':f'matched|{i}','pident':'90','qcovhsp':'100','bitscore':'500'} for i in (1,2)]})
    mrc.main(['--spec',str(spec),'--out',str(tmp_path/'output'),'--width-in','9.6'])
    receipt=json.loads((tmp_path/'output/query/receipt.json').read_text())
    assert len(receipt['reference_states'])==2
    assert receipt['reference_states'][1]['pairs']==0
    assert receipt['reference_states'][1]['not_placed_reason']=='below discovery admission threshold'
    assert (tmp_path/'output/query/comparison.png').exists()
