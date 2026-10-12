"""Independent tiny protocol fixtures: N bases/X residues, not biological designs.

All outputs are explicitly SYNTHETIC_PROTOCOL_ONLY. No actual CORASON, BLAST,
alignment, tree inference, database, network or private research input is used.
"""
from pathlib import Path
import hashlib
import json
import os
import sys
import zipfile
from tests._python_fixture_launcher import write_python_fixture


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_record(path):
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')
    return path


def region(contig='CP000001.1', start=0, region_number=1, compound=False, stop=False):
    # Valid fixed-column LOCUS, simple geometry, deliberately uninformative payload.
    feature = 'join(1..3,7..12)' if compound else '1..12'
    return (f'LOCUS       {contig:<16}{120:>12} bp    DNA     linear   UNK 01-JAN-1980\n'
        f'DEFINITION  synthetic protocol fixture.\nACCESSION   {contig.split(".")[0]}\nVERSION     {contig}\n'
        'KEYWORDS    .\nSOURCE      synthetic construct\n  ORGANISM  synthetic construct\n            .\n'
        'COMMENT     ##antiSMASH-Data-START##\n'
        f'            Orig. start :: {start}\n            Orig. end :: {start+120}\n'
        '            ##antiSMASH-Data-END##\n'
        'FEATURES             Location/Qualifiers\n'
        '     source          1..120\n                     /organism="synthetic construct"\n'
        f'     region          1..120\n                     /region_number="{region_number}"\n'
        f'     CDS             {feature}\n                     /locus_tag="g1"\n'
        f'                     /translation="XXXX{"*" if stop else ""}"\n'
        '     CDS             complement(13..24)\n                     /locus_tag="g2"\n                     /translation="XX"\n'
        '     CDS             25..36\n                     /locus_tag="g3"\n                     /translation="XXX"\n'
        'ORIGIN\n        1 ' + 'n'*60 + '\n       61 ' + 'n'*60 + '\n//\n').encode()


CONVERTER = r'''import pathlib,json,sys,os
w=pathlib.Path.cwd(); rows=json.loads((w/'STAGED_SOURCE.json').read_text())
(w/'GENOMES').mkdir()
ids=[]
# Reverse allocation deliberately prevents deriving IDs from the input sequence.
for i,row in enumerate(reversed(rows),100001):
 org=str(i); ids.append(org+'\t666666.'+org+'\t'+row['token']+'.gbk')
 genes=row['genes']
 if os.environ.get('FIXTURE_MODE')=='CONVERT_DROP': genes=genes[:-1]
 faa=[]; txt=['\t'.join(['contig_id','feature_id','type','location','start','stop','strand','function','locus_tag','figfam','species','nucleotide_sequence','amino_acid','sequence_accession'])]
 for g in genes:
  fid='fig|666666.'+org+'.peg.'+str(g['ordinal'])
  aa=g['translation']; faa.append('>'+fid+'\n'+aa+'\n')
  a,b=(g['start']+1,g['end']) if g['strand']==1 else (g['end'],g['start']+1)
  txt.append('\t'.join([row['full_contig'],fid,'type','location',str(a),str(b),'+' if g['strand']==1 else '-','unspecified',row['full_contig'].split('.')[0],'figfam','.','nuc',aa,g['locus_tag']]))
 (w/'GENOMES'/f'{org}.faa').write_text(''.join(faa)); (w/'GENOMES'/f'{org}.txt').write_text('\n'.join(txt)+'\n')
(w/'Corason_Rast.IDs').write_text('\n'.join(ids)+'\n')
'''

FILTER = r'''import pathlib,sys,os
root=pathlib.Path(sys.argv[1]); names=sorted(p.stem for p in root.glob('*.input'))
if os.environ.get('FIXTURE_MODE')=='FILTER':
 for name in names[-1:]:
  (root/(name+'.input')).unlink(); (root/(name+'.input2')).unlink()
 names=names[:-1]
if os.environ.get('FIXTURE_MODE')=='FILTER_FAIL': sys.exit(7)
sys.stdout.write(str(len(names))+'\t'+','.join(names))
'''

ENTRY = r'''import pathlib,json,os,sys,subprocess
if '--help' in sys.argv:
 print('queryfile special_org rast_ids gbk conda'); sys.exit(0)
w=pathlib.Path.cwd(); mode=os.environ.get('FIXTURE_MODE','MULTILOCUS_CORE')
rows=json.loads((w/'STAGED_SOURCE.json').read_text())
bytoken={x['token']:x for x in rows}
ids=[x.split('\t') for x in (w/'Corason_Rast.IDs').read_text().splitlines()]
root=w/'query.faa-output';root.mkdir(); blast=[]; neighborhoods={}
for org,nid,filename in ids:
 row=bytoken[filename[:-4]]
 if mode=='NO_HIT' and org==ids[-1][0]: continue
 for anchor in ([1,2] if mode=='MULTIPLE_HITS' and org==ids[0][0] else [1]):
  name=org+'_'+str(anchor); cells=[]
  for g in row['genes']:
   fid='fig|666666.'+org+'.peg.'+str(g['ordinal'])
   cells.append('\t'.join([str(g['start']+1),str(g['end']),'+',str(g['ordinal']),row['token']+'.gbk','unspecified',fid,'100','none']))
  # Context's first row is the actual anchor, not always ordinal1.
  cells=cells[anchor-1:anchor]+cells[:anchor-1]+cells[anchor:]
  (root/(name+'.input')).write_text('\n'.join(cells)+'\n')
  aa=row['genes'][anchor-1]['translation']
  (root/(name+'.input2')).write_text('>peg_'+str(anchor)+'_org'+org+'\n'+aa+'\n')
  neighborhoods[name]=(org,str(anchor),row)
  blast.append('\t'.join(['QUERY','fig|666666.'+org+'.peg.'+str(anchor)+'|'+org,'100','4','0','0','1','4','1','4','1e-20','100']))
(root/'query.faa.BLAST.pre').write_text('\n'.join(blast)+'\n')
if mode=='NO_CAPTURE': pass
else: subprocess.run([str(w/'CORASON'/'ReadingInputs.pl'),str(root),'CORASON'],check=False)
active={p.stem for p in root.glob('*.input')}
neighborhoods={k:v for k,v in neighborhoods.items() if k in active}
tips={row['token']+'_gbk_peg_'+peg+'_org_'+org:name for name,(org,peg,row) in neighborhoods.items()}
(root/'query.faa.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Synthetic protocol only</text></svg>')
if mode=='SVG_ONLY': sys.exit(0)
core=[]
for ordinal in ([2,3] if mode not in ('QUERY_ONLY_SHAVED','QUERY_ONLY_UNSHAVED','BLAST_ORDER') else [1]):
 core.append('\t'.join('fig|666666.'+org+'.peg.'+str(ordinal)+'|'+name for name,(org,peg,row) in neighborhoods.items()))
(root/'Core').write_text('\n'.join(core)+'\n')
if len(core)>1:
 (root/'query.faa_Report').write_text('There is a core composed by 2 orhtolog on this cluster\n')
 raw=root/'CORASON'/'FASTAINTER'; raw.mkdir(parents=True)
 cat=root/'CORASON'/'CONCATENADOS';cat.mkdir()
 for i,ordinal in enumerate([2,3],1):
  rawrows=[]; part=[]
  for name,(org,peg,row) in neighborhoods.items():
   rawrows.append('>fig|666666.'+org+'.peg.'+str(ordinal)+'|'+name+'\n'+row['genes'][ordinal-1]['translation']+'\n')
   part.append('>org'+org+'_'+peg+'\n'+('XX' if i==1 else 'X-X')+'\n')
  (raw/(str(i)+'.interFastatodos')).write_text(''.join(rawrows));(cat/str(i)).write_text(''.join(part))
 # Reverse native partition order, independently specified expected bytes.
 alignment={tip:'X-XXX' for tip in tips}
 tree=root/'query.faa_BGC.tre';order=root/'query.faa_BGC_TREE.order';ali=root/'RightNames.txt'
elif mode=='QUERY_ONLY_SHAVED':
 (root/'query.faa_Report').write_text('I will draw with the single hits order\n')
 alignment={tip:'XX' for tip in tips};tree=root/'query.faa_PrincipalHits.tre';order=root/'PrincipalHits.order';ali=root/'RightNamesPrincipalHits.txt'
elif mode=='QUERY_ONLY_UNSHAVED':
 (root/'query.faa_Report').write_text('I will draw with the single hits order\n')
 alignment={tip:'XXXX' for tip in tips};tree=root/'query.faa_Unshaved.tre';order=root/'PrincipalHitsUnshaved.order';ali=root/'RightNamesPrincipalHits_Unshaved.txt'
else:
 (root/'query.faa_Report').write_text('I will sort draws with the single hits blast order\n');sys.exit(0)
if mode=='WRONG_CORE':
 (root/'Core').write_text('fig|666666.999999.peg.1|999999_1\n')
if mode=='FOREIGN_LEAF': alignment['FOREIGN']=next(iter(alignment.values()))
if mode=='BAD_CONCAT': alignment={tip:'XXXXX' for tip in tips}
ali.write_text(''.join('>'+tip+'\n'+aa+'\n' for tip,aa in alignment.items()))
tree.write_text('('+','.join(tip+':0.01' for tip in alignment)+');\n');order.write_text('\n'.join(alignment)+'\n')
if mode=='MISSING_TREE': tree.unlink()
'''


def make_case(root, adapter, mode='MULTILOCUS_CORE', strains=('Foo','foo'), contigs=('CP000001.1','CP000002.1'), compound=False, stop=False):
    root = Path(root)
    records=[]; exact=[]
    for i,(strain,contig) in enumerate(zip(strains,contigs),1):
        pkg=root/f'package{i}';pkg.mkdir();archive=root/f'source{i}.zip'
        member=contig+'.region001.gbk'
        with zipfile.ZipFile(archive,'w') as z: z.writestr(member,region(contig,compound=compound,stop=stop))
        az=file_record(archive)
        manifest={'strain_id':strain,'input_zip':str(archive),'input_zip_sha256':az['sha256'],
            'bgcs':[{'contig':contig,'node_id':contig,'antismash_region':'region001','region_number':1,'bgc_id':'BGC001','start':0,'end':120,'source_gbk':member}]}
        write_json(pkg/'manifest.json',manifest)
        # Independent package-tree digest using the documented actual binding grammar.
        ms=sha((pkg/'manifest.json').read_bytes())
        tree=sha(('manifest.json\t'+ms+'\n').encode())
        evidence=root/f'validate{i}.log';evidence.write_text('SYNTHETIC validation evidence, not actual Mamey validation\n')
        validation=write_json(root/f'validation{i}.json',{'schema':'corason.package-validation-review.v1','state':'VALIDATED',
            'package_tree_sha256':tree,'evidence_path':str(evidence),'evidence_sha256':sha(evidence.read_bytes()),'scope':'SYNTHETIC_PROTOCOL_TEST'})
        public=write_json(root/f'public{i}.json',{'schema':'corason.public-source-review.v1','state':'REVIEWED_PUBLIC_SOURCE_BINDING',
            'source_zip_sha256':az['sha256'],'accession_versions':[contig],
            'primary_sources':[{'url':'https://example.invalid/synthetic-only','accession_version':contig,'metadata_sha256':'1'*64}],
            'scope':'SYNTHETIC_PROTOCOL_TEST_NOT_PUBLIC_BIOLOGY'})
        records.append({'package':str(pkg),'package_manifest_sha256':ms,'source_zip':str(archive),'source_zip_sha256':az['sha256'],
            'source_bytes':az['bytes'],'public_receipt':file_record(public),'validation_receipt':file_record(validation)})
        exact.append(strain+' / '+contig+' / region001 / BGC001')
    intake=write_json(root/'intake.json',{'schema':'corason.public-intake.v1','records':records})
    selection=write_json(root/'selection.json',{'schema':'corason.selection.v1','loci':exact,
        'query':{'exact_locus':exact[0],'locus_tag':'g1','translation_sha256':sha(('XXXX*' if stop else 'XXXX').encode())}})
    helpers={}
    for name,body in [('gbkIndex.pl',CONVERTER),('corason.pl',ENTRY),('ReadingInputs.pl',FILTER)]:
        p=root/name;p.write_text(body);helpers[name]=file_record(p)
    launcher=root/'python'
    write_python_fixture(launcher, 'import os,sys\nos.execv(' + repr(sys.executable) + ', [' + repr(sys.executable) + ', *sys.argv[1:]])\n')
    exe=file_record(launcher)
    helpers['fixture_launcher.py']=file_record(launcher.with_name(launcher.name+'.fixture.py'))
    identity={'commit':adapter.COMMIT,'prefilter_observer':'ReadingInputs-before-deletion-v1',
        'interpreter':exe,'observer_python':exe,'helpers':helpers,'entry':helpers['corason.pl'],'tools':{},
        'resources':{'source_reviewed':True,'parallel_runs':1,'cpu_total':1,'prefilter_stage_reviewed':True},
        'environment':{'PATH':'/usr/bin:/bin','FIXTURE_MODE':mode, 'PYTHONDONTWRITEBYTECODE':'1',
            **{k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','OMP_THREAD_LIMIT')}}}
    review=write_json(root/'runtime_review.json',{'schema':'corason.runtime-review.v1','intent':'SYNTHETIC_PROTOCOL_TEST','state':'REVIEWED',
        'identity_sha256':sha(json.dumps(identity,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()),
        'observer_sha256':sha(adapter.observer_source().encode()),'scope':'FAKE_CHILD_PROTOCOL_NOT_NATIVE_ADMISSION'})
    runtime=write_json(root/'runtime.json',{'schema':'corason.runtime.v1','profile':adapter.PROFILE,'kind':'SYNTHETIC_PROTOCOL_TEST',
        'identity':identity,'review_receipt':file_record(review)})
    workroot=root/'native_work';workroot.mkdir()
    return {'root':root,'intake':intake,'selection':selection,'runtime':runtime,'workroot':workroot,'identities':exact}
