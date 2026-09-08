"""Export one exact locus to the existing gene-first evidence-index schema.

BOUND describes recorded domain-source binding only, never accepted function.
No index is ingested automatically. The source-map JSON resolves logical inputs.
"""
import argparse,csv,io,json,re
from pathlib import Path
from urllib.parse import quote
from build_atlas import identity,sha,write
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mamey.csv_safety import SafeDictWriter

def export(data_path,pin,parts,output):
 data_path=Path(data_path)
 if sha(data_path)!=pin:raise ValueError('ATLAS_PIN_CONFLICT')
 if len(parts)!=4 or any(not x or x!=x.strip() for x in parts):raise ValueError('COMPLETE_IDENTITY_REQUIRED')
 data=json.loads(data_path.read_text());display=' / '.join(parts)
 loci=[l for l in data['loci'].values() if identity(l)==display]
 if len(loci)!=1:raise ValueError('LOCUS_UNBOUND_OR_AMBIGUOUS')
 locus=loci[0];rows=[r for r in data['records'] if r['exact_identity']==display]
 fields=['channel','strain','full_node','region','bgc_alias','gene','evidence_state','source_locator','source_sha256','note','protein_sha256']
 buf=io.StringIO();writer=SafeDictWriter(buf,fieldnames=fields,delimiter='\t',lineterminator='\n');writer.writeheader()
 for r in rows:
  if not re.fullmatch('[0-9a-f]{64}',r['protein_sha256']):raise ValueError('PROTEIN_IDENTITY_HOLD')
  bound=all(e['binding_state']=='SOURCE_SEQUENCE_AND_GEOMETRY_BOUND' and not e['holds'] for e in r['evidence'])
  writer.writerow(dict(channel='domain',**{k:locus[k] for k in ('strain','full_node','region','bgc_alias')},gene=r['locus_tag'],evidence_state='BOUND' if bound else 'UNBOUND',source_locator='evidence://domain_db',source_sha256=data['inputs']['domain_db']['sha256'],note='Existing source domain annotations; family grouping only; tailoring role and substrate unknown; feature orders '+','.join(str(e['feature_order']) for e in r['evidence']),protein_sha256=r['protein_sha256']))
 root=Path(output).resolve();root.mkdir(parents=True,exist_ok=True);stem='__'.join(quote(x,safe='._-') for x in parts)
 path=root/(stem+'__evidence_index.tsv');write(path,buf.getvalue(),root)
 write(root/(stem+'__source_map.json'),json.dumps({'exact_identity':display,'atlas_sha256':pin,'evidence://domain_db':data['inputs']['domain_db'],'scientific_admission':'NOT_PERFORMED'},indent=2),root)
 return path
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--sha256',required=True);p.add_argument('--locus',nargs=4,required=True);p.add_argument('--output',required=True);a=p.parse_args();print(export(a.data,a.sha256,a.locus,a.output))
