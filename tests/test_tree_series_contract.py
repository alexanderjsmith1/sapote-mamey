import csv,hashlib,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from tree_series_contract import validate,digest

def fixture(tmp_path,panel='type_plus_selected_non_type',status='non_type'):
 seq='ACGTACGT';rows=[dict(tip=t,role=role,type_status=st,accession=t+'.1',sequence_sha256=hashlib.sha256(seq.encode()).hexdigest(),evidence='retained source record',admission='admitted') for t,role,st in [('Q','query','not_applicable'),('T','reference','type'),('N','reference',status),('O','outgroup','type')]]
 p=tmp_path/'roster.tsv'
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
 tree=tmp_path/'tree.nwk';tree.write_text('((Q:0.1,T:0.1):0.1,(N:0.1,O:0.1):0.1);')
 fa=tmp_path/'seq.fasta';fa.write_text(''.join('>'+x['tip']+'\n'+seq+'\n' for x in rows))
 bind={'path':p.name,'sha256':digest(p),'tree':{'path':tree.name,'sha256':digest(tree)},'sequences':{'path':fa.name,'sha256':digest(fa)}}
 tree={'id':'generic','reference_panel':panel,'reference_manifest':bind}
 data={'series_requirements':{'taxonomic_scopes':['Genus'],'reference_panels':[panel],'reference_ratios':[1,2,3],'views':['publication','publication-noloc']},'trees':[tree]}
 jobs=[dict(taxonomic_scope='Genus',reference_panel=panel,reference_ratio=r,view=v) for r in [1,2,3] for v in ['publication','publication-noloc']]
 return data,jobs

def test_complete_series(tmp_path):
 data,jobs=fixture(tmp_path);assert validate(data,jobs,tmp_path)['expected_variants']==6

def test_missing_and_duplicate_views_fail(tmp_path):
 data,jobs=fixture(tmp_path)
 with pytest.raises(ValueError,match='MATRIX_MISMATCH'):validate(data,jobs[:-1],tmp_path)
 with pytest.raises(ValueError,match='DUPLICATE_VARIANT'):validate(data,jobs+[jobs[0]],tmp_path)

def test_unknown_cannot_be_promoted_to_non_type(tmp_path):
 data,jobs=fixture(tmp_path,status='unverified')
 with pytest.raises(ValueError,match='MIXED_PANEL_NOT_ESTABLISHED'):validate(data,jobs,tmp_path)

def test_provisional_panel_explicitly_distinct(tmp_path):
 data,jobs=fixture(tmp_path,panel='type_plus_selected_additional',status='unverified');assert validate(data,jobs,tmp_path)

def test_type_only_mislabel_fails(tmp_path):
 data,jobs=fixture(tmp_path,panel='type_only')
 with pytest.raises(ValueError,match='TYPE_ONLY_CONTRADICTION'):validate(data,jobs,tmp_path)

def test_tampered_manifest_fails(tmp_path):
 data,jobs=fixture(tmp_path);(tmp_path/'roster.tsv').write_text('changed')
 with pytest.raises(ValueError,match='MANIFEST_HASH'):validate(data,jobs,tmp_path)

def test_actual_tree_identity_must_match(tmp_path):
 data,jobs=fixture(tmp_path);p=tmp_path/'tree.nwk';p.write_text('((X:0.1,T:0.1):0.1,N:0.2);');data['trees'][0]['reference_manifest']['tree']['sha256']=digest(p)
 with pytest.raises(ValueError,match='ROSTER_MISMATCH'):validate(data,jobs,tmp_path)

def test_sequence_substitution_fails(tmp_path):
 data,jobs=fixture(tmp_path);p=tmp_path/'seq.fasta';p.write_text(p.read_text().replace('ACGTACGT','ACGTACGA'));data['trees'][0]['reference_manifest']['sequences']['sha256']=digest(p)
 with pytest.raises(ValueError,match='SEQUENCE_MISMATCH'):validate(data,jobs,tmp_path)

def test_requirements_cannot_be_omitted(tmp_path):
 with pytest.raises(ValueError,match='REQUIREMENTS_MISSING'):validate({},[],tmp_path)

def test_requested_broader_panel_cannot_be_omitted(tmp_path):
 data,jobs=fixture(tmp_path);data['series_requirements']['reference_panels']+=['type_only']
 with pytest.raises(ValueError,match='MATRIX_MISMATCH'):validate(data,jobs,tmp_path)

def test_retained_accession_is_not_excluded(tmp_path):
 from tree_series_contract import read_display_exclusions
 p=tmp_path/'exclusions.tsv';p.write_text('tip\taccession\tretained_accession\nold_tip\tOLD.1\tKEEP.1\n')
 assert read_display_exclusions(p)=={'old_tip','OLD.1'}

def test_subprocess_success_without_artifacts_is_not_completion(tmp_path):
 from tree_series_contract import validate_delivery
 data,jobs=fixture(tmp_path)
 with pytest.raises(ValueError,match='OUTPUT_MISSING'):validate_delivery(data,{'job_id':'x'},tmp_path,tmp_path)

def test_full_density_must_retain_backbone_and_queries(tmp_path):
 from tree_series_contract import validate_delivery
 data,jobs=fixture(tmp_path);out=tmp_path/'output';out.mkdir()
 (out/'tree.nwk').write_text('((Q:0.1,T:0.1):0.1,O:0.1);');(out/'metadata.tsv').write_text('tip\nQ\nT\nO\n')
 (out/'a.pdf').write_bytes(b'fixture');(out/'a.png').write_bytes(b'fixture')
 job={'job_id':'x','tree_id':'generic','reference_ratio':'all','output_layout':{'tree':'tree.nwk','metadata':'metadata.tsv','pdf':'a.pdf','png':'a.png'}}
 with pytest.raises(ValueError,match='FULL_CONTEXT_INCOMPLETE'):validate_delivery(data,job,out,tmp_path)
 (out/'tree.nwk').write_text('(N:0.1,T:0.1);');(out/'metadata.tsv').write_text('tip\nN\nT\n')
 with pytest.raises(ValueError,match='QUERY_OR_OUTGROUP_LOST'):validate_delivery(data,job,out,tmp_path)

def test_full_backbone_catalog_support(tmp_path):
 import tree_catalog
 run=tmp_path/'run';run.mkdir();host=tmp_path/'host.tsv';host.write_text('fixture');db=tmp_path/'refs.sqlite';db.write_text('fixture')
 data={'schema':tree_catalog.SCHEMA,'trees':[{'id':'generic','run_dir':str(run),'group':'Genus','taxonomic_scope':'Genus','cohort_scope':['cohort'],'reference_panel':'type_only','host_table':str(host),'ref_source_db':str(db),'reference_ratios':[1,2,3,4,'all'],'views':['publication']}]}
 p=tmp_path/'catalog.json';p.write_text(json.dumps(data));_,_,jobs=tree_catalog.load_catalog(p)
 assert [x['reference_ratio'] for x in jobs]==[1,2,3,4,'all']
 with pytest.raises(ValueError,match='REQUIREMENTS_MISSING'):tree_catalog.render(p,tmp_path/'results')
 assert not (tmp_path/'results').exists()

def prepared_config(tmp_path):
 data,jobs=fixture(tmp_path);data['series_requirements']['reference_ratios']=['all'];data['series_requirements']['views']=['publication']
 folder=tmp_path/'prepared';folder.mkdir();(folder/'tree.newick').write_bytes((tmp_path/'tree.nwk').read_bytes())
 rows=[]
 for t,role,status,taxon,source,raw_source,geo,raw_geo in [
  ('Q','query','not_applicable','Genus sp. Query-1','bumblebee','Bombus specimen','US','USA: documented locality'),
  ('T','reference','type','Genus species Type-Strain','soil/rock/sediment','soil','Canada','Canada: documented locality'),
  ('N','reference','non_type','Genus sp. Strain-N','plant-associated','plant root','Asia','China: documented locality'),
  ('O','outgroup','type','Outgroupus species Type-Strain','aquatic','marine water','Pacific Ocean','Pacific Ocean')]:
  type_marker=' (Type)' if status=='type' else ''
  concise=f'{taxon}{type_marker} [{source}; {geo}]'
  experiment='Experiment-1' if role=='query' else '';sample='Sample-1' if role=='query' else ''
  rows.append(dict(tip=t,role=role,type_status=status,taxon_display=taxon,label_concise=concise,
   label_experiment=concise+(f' {{{experiment}; {sample}}}' if experiment else ''),raw_source=raw_source,
   source_category=source,raw_geography=raw_geo,geography=geo,
   candida_state='positive' if role=='query' else '',mrsa_state='missing' if role=='query' else '',
   assay_provenance='generic owner assay fixture' if role=='query' else '',experiment_id=experiment,
   sample_id=sample,accession=t+'.1'))
 with (folder/'metadata.tsv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
 provenance=[]
 for row in rows:
  for field in ['raw_source','raw_geography']+(['candida_state','mrsa_state'] if row['role']=='query' else []):
   provenance.append(dict(tip=row['tip'],field=field,raw_value=row[field],source='generic fixture',evidence_sha256='a'*64,status='bound'))
 with (folder/'provenance.tsv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(provenance[0]),delimiter='\t');w.writeheader();w.writerows(provenance)
 (folder/'palette.tsv').write_text('field\tvalue\tcolor\nsource\tbumblebee\t#0072B2\nsource\tsoil/rock/sediment\t#8C510A\nsource\tplant-associated\t#228833\nsource\taquatic\t#88CCEE\ngeography\tUS\t#009E73\ngeography\tCanada\t#0072B2\ngeography\tAsia\t#CC79A7\ngeography\tPacific Ocean\t#4477AA\n')
 (folder/'settings.tsv').write_text('key\tvalue\nview\tpublication\ntitle\tGeneric series fixture\nlayout_profile\tfull_genus_single_line_v1\ntree_fraction\t0.39\noutgroup_tip\tO\ninference_program\tIQ-TREE fixture\nmodel\tTEST+MODEL\nsupport_type\tUFBoot\nsupport_replicates\t1000\nsupport_cutoff\t70\nrooting\tRooted once on declared outgroup O\n')
 (folder/'caption.txt').write_text('Generic mechanical validation fixture. No biological claim.\n')
 from render_tree_reference_series import INPUTS
 job=dict(jobs[0],tree_id='generic',job_id='generic_all',series_index=1,output_stem='Genus_N01_QUERY-001_2types_1nontype_sample-ID',reference_ratio='all',input_dir='prepared',input_hashes={n:digest(folder/n) for n in INPUTS})
 data['display_jobs']=[job];path=tmp_path/'config.json';path.write_text(json.dumps(data));return path,data

def test_real_portable_series_render_and_hash_bindings(tmp_path):
 import shutil
 from render_tree_reference_series import render
 if not shutil.which('Rscript'):pytest.skip('Rscript unavailable; integration unverified')
 config,data=prepared_config(tmp_path);result=render(config,tmp_path/'result',workers=1)
 assert result['status']=='COMPLETE_MECHANICAL_REVIEW_ONLY',result
 assert result['passed']==1 and result['results'][0]['renderers']
 stem='01_Genus_N01_QUERY-001_2types_1nontype_sample-ID'
 folder=tmp_path/'result/generic_all'
 for suffix in ['.pdf','.png','.newick','.metadata.tsv','.provenance.tsv','.palette.tsv','.settings.tsv','.caption.txt','.layout_audit.tsv','.methods.txt','.render.log','.render_receipt.json','.R_SESSION.txt','.source_category_actual_cells.tsv','.geography_actual_cells.tsv']:
  assert (folder/f'{stem}{suffix}').is_file()
 assert not (folder/'tree.pdf').exists() and not (folder/'tree.png').exists()
 with pytest.raises(ValueError,match='OUTPUT_EXISTS'):render(config,tmp_path/'result')

def test_numbering_and_descriptive_stems_are_required(tmp_path):
 from render_tree_reference_series import preflight
 for i,(field,value,code) in enumerate([('series_index',2,'INDEX_SEQUENCE'),('series_index','1','INDEX_SEQUENCE'),('output_stem','tree','OUTPUT_STEM'),('output_stem','bad name','OUTPUT_STEM')]):
  case=tmp_path/str(i);case.mkdir();config,data=prepared_config(case)
  changed=json.loads(config.read_text());changed['display_jobs'][0][field]=value;config.write_text(json.dumps(changed))
  with pytest.raises(ValueError,match=code):preflight(config)
 config,data=prepared_config(tmp_path);data['series_requirements']['views']=['publication','internal'];duplicate=dict(data['display_jobs'][0]);duplicate.update(job_id='generic_all_2',series_index=2,view='internal')
 data['display_jobs'].append(duplicate);config.write_text(json.dumps(data))
 with pytest.raises(ValueError,match='OUTPUT_STEM_DUPLICATE'):preflight(config)

def test_shared_palette_rejects_category_drift_and_color_reuse():
 from render_tree_reference_series import admit_palette
 mapping,colors=admit_palette([{'field':'source','value':'Bumblebee','color':'#00A6D6'}])
 with pytest.raises(ValueError,match='PALETTE_CONTRADICTION'):
  admit_palette([{'field':'source','value':'Bumblebee','color':'#FF0000'}],mapping,colors)
 with pytest.raises(ValueError,match='PALETTE_COLOR_REUSED'):
  admit_palette([{'field':'source','value':'Honeybee','color':'#00A6D6'}],mapping,colors)

def test_preflight_rejects_unresolved_display_metadata_for_every_role(tmp_path):
 from render_tree_reference_series import preflight
 for role,field,value in [('query','source_category','Not recorded'),('reference','geography','unknown'),('outgroup','geography','')]:
  case=tmp_path/(role+'_'+field);case.mkdir();config,data=prepared_config(case)
  path=case/'prepared/metadata.tsv';rows=list(csv.DictReader(path.open(),delimiter='\t'))
  target=next(row for row in rows if row['role']==role);target[field]=value
  with path.open('w') as handle:
   writer=csv.DictWriter(handle,fieldnames=list(rows[0]),delimiter='\t');writer.writeheader();writer.writerows(rows)
  data['display_jobs'][0]['input_hashes']['metadata.tsv']=digest(path);config.write_text(json.dumps(data))
  with pytest.raises(ValueError,match='DISPLAY_FIELD_UNBOUND'):preflight(config)

def test_palette_rejects_missingness_categories():
 from render_tree_reference_series import admit_palette
 for value in ['Not recorded','Unknown','Unresolved source','N/A']:
  with pytest.raises(ValueError,match='PALETTE_VALUE'):
   admit_palette([{'field':'geography','value':value,'color':'#DDDDDD'}])

def test_renderer_and_receipt_bind_focal_colour_knob(tmp_path,monkeypatch):
 from render_tree_reference_series import preflight
 monkeypatch.delenv('GG_FOCAL_COLOUR',raising=False)
 config,data=prepared_config(tmp_path);_,_,receipt=preflight(config)
 assert receipt['query_label_color']=='#000000'
 assert receipt['display_metadata_contract']['jobs']['generic_all']['all_tips_complete'] is True
 script=(Path(__file__).resolve().parents[1]/'tools/tree_reference_series.R').read_text()
 assert "Sys.getenv('GG_FOCAL_COLOUR','#000000')" in script
 monkeypatch.setenv('GG_FOCAL_COLOUR','#bb0000')
 _,_,receipt2=preflight(config)
 assert receipt2['query_label_color']=='#bb0000'

def test_prepared_metadata_cannot_change_after_binding(tmp_path):
 from render_tree_reference_series import preflight
 config,data=prepared_config(tmp_path);p=tmp_path/'prepared/metadata.tsv';p.write_text(p.read_text()+'\n')
 with pytest.raises(ValueError,match='INPUT_HASH_CHANGED'):preflight(config)

def test_bee_category_cannot_be_inherited_by_soil_reference(tmp_path):
 from render_tree_reference_series import preflight
 config,data=prepared_config(tmp_path);p=tmp_path/'prepared/metadata.tsv';rows=list(csv.DictReader(p.open(),delimiter='\t'));next(x for x in rows if x['tip']=='T')['source_category']='bumblebee'
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
 data['display_jobs'][0]['input_hashes']['metadata.tsv']=digest(p);config.write_text(json.dumps(data))
 with pytest.raises(ValueError,match='SOURCE_CATEGORY_CONTRADICTION'):preflight(config)


def test_profile_specific_tree_allocation_rejects_round3_regression():
 from phylo_display_contract import validate_layout_profile
 assert validate_layout_profile('full_genus_single_line_v1',0.39)['tree_fraction']==0.39
 with pytest.raises(ValueError,match='TREE_AREA_REGRESSION'):
  validate_layout_profile('full_genus_single_line_v1',0.25)


def test_metadata_row_order_does_not_change_palette_or_contract(tmp_path):
 from render_tree_reference_series import preflight
 config,data=prepared_config(tmp_path);_,_,first=preflight(config)
 path=tmp_path/'prepared/metadata.tsv';rows=list(csv.DictReader(path.open(),delimiter='\t'));rows.reverse()
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
 data['display_jobs'][0]['input_hashes']['metadata.tsv']=digest(path);config.write_text(json.dumps(data));_,_,second=preflight(config)
 assert first['palette_contract']==second['palette_contract']
 assert first['display_metadata_contract']['jobs']['generic_all']==second['display_metadata_contract']['jobs']['generic_all']


def test_assay_states_are_distinct_and_reference_cells_blank(tmp_path):
 from phylo_display_contract import ASSAY_SYMBOL
 assert ASSAY_SYMBOL=={'positive':'+','negative':'-','not_tested':'n.t.','missing':'?'}
 config,data=prepared_config(tmp_path);path=tmp_path/'prepared/metadata.tsv';rows=list(csv.DictReader(path.open(),delimiter='\t'))
 next(x for x in rows if x['role']=='reference')['candida_state']='not_tested'
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
 data['display_jobs'][0]['input_hashes']['metadata.tsv']=digest(path);config.write_text(json.dumps(data))
 from render_tree_reference_series import preflight
 with pytest.raises(ValueError,match='REFERENCE_ASSAY_NOT_BLANK'):preflight(config)


def test_no_species_name_fallback_or_country_to_state_inference(tmp_path):
 from render_tree_reference_series import preflight
 config,data=prepared_config(tmp_path);_,_,receipt=preflight(config)
 assert receipt['display_metadata_contract']['jobs']['generic_all']['status']=='PHYLO_DISPLAY_CONTRACT_PASS'
 source=(Path(__file__).resolve().parents[1]/'tools/phylo_display_contract.py').read_text()
 assert 'species name' not in source.lower()
 assert 'New Jersey' not in source and 'Ontario' not in source
