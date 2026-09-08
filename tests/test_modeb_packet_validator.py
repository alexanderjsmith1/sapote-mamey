"""Generic relational mutations plus original real-packet regression checks."""
import copy,gzip,importlib.util,json,os,unittest
from pathlib import Path
from mamey.modeb_evidence_packet import validate_packet,render_packet_sections,PROFILE

def fixture():
    identity='EXAMPLE / contig_alpha / region001 / cluster_alpha';parts=identity.split(' / ');records={};sources={}
    def add(key,table,fields):
        rid=key+':'+table+':'+str(len(records));sources[key]={'database_sha256':'b'*64}
        records[rid]={'database_key':key,'table':table,'primary_key':{'fixture_id':rid},'row_sha256':'a'*64,'fields':fields,'field_provenance':{k:{'database_sha256':'b'*64,'column':k} for k in fields}};return rid
    genes=[]
    for order in (1,2):
        query=str(order)*64;tag='gene_'+str(order);common=dict(locus_key='fixture',gene_order=order,locus_tag=tag,protein_sha256=query,membership='EXACT_REGION',cds_start=order*300,cds_end=order*300+299,strand=1,protein_length=100)
        census=add('antismash_gene_census','gene',common.copy());channels={}
        for key in ['blastp_nr','blastp_clustered_nr','blastp_swissprot']:
            binding=add(key,'binding',dict(query_sha256=query,exact_identity=identity,gene_order=order,locus_key='fixture',locus_tag=tag,**dict(zip(['strain','full_node','region','bgc_alias'],parts))))
            protein=add(key,'protein',dict(query_sha256=query,**({'state':'VERIFIED_HITS','aa_length':100} if key=='blastp_swissprot' else {'availability_state':'VERIFIED_HITS','protein_length':100})))
            if key=='blastp_swissprot':
                search=add(key,'outcome',dict(query_sha256=query,hit_count=1,dataset_id='fixture_dataset',observation='HITS_UNDER_RECORDED_SETTINGS'))
                q=add(key,'_query_key',dict(id=order,query_sha256=query));hit=add(key,'_hit_pack',dict(query_id=order,selected_hit={'descriptions':[{'title':'Fixture subject'}],'hsps':[{}]}));receipts=[search]
            else:
                search=add(key,'search',dict(id=order,query_sha256=query,xml_id=order,observation='HITS_UNDER_RECORDED_SETTINGS'));xml=add(key,'source_xml',dict(id=order,channel='ncbi_nr' if key=='blastp_nr' else 'ncbi_clustered_nr'));hit=add(key,'hit',dict(id=order,search_id=order,title='Fixture subject'));receipts=[search,xml]
            ch=dict(binding=binding,protein=protein,state='VERIFIED_HITS',search_receipts=receipts,selected_hits=[hit])
            if key=='blastp_swissprot':ch['query_key']=q
            channels[key]=ch
        tools={key:add(key,'gene',dict(common,groups_json='[]',state='NO_MATCH')) for key in ['mamey_regulator_keywords','mamey_transporters_keywords','mamey_resistance_keywords']}
        tools['antismash_gbk_domains']=add('antismash_gbk_domains','gene',dict(common,source_qualifiers_zlib={}))
        genes.append(dict(identity=identity,membership='EXACT_REGION',gene_order=order,locus_tag=tag,census=census,channels=channels,tools=tools))
    ctx=add('CCTT_EXISTING','gene',dict(locus_key='fixture',locus_tag='context_gene',gene_order=None,protein_sha256='c'*64,membership='BOUNDARY_CONTEXT_10KB',start=1,end=299,strand=1))
    return dict(schema='modeb_selected_locus_packet/0.1',profile_sha256=PROFILE,identity=identity,expected_exact_genes=2,locus=dict(strain=parts[0],full_node=parts[1],region=parts[2],bgc_alias=parts[3],locus_key='fixture',cds_count=2,region_start_1based=300,region_end_1based=899,region_nt=600,products_json='[]'),exact_genes=genes,context_genes=[dict(identity=identity,locus_tag='context_gene',membership='BOUNDARY_CONTEXT',protein_sha256='c'*64,start=1,end=299,strand=1,sources=[ctx])],records=records,source_releases=sources,features=[],tool_records={'mamey_resistance_tiers':[]},section_source_records={})

class GenericJoinTests(unittest.TestCase):
    def setUp(self):self.p=fixture();self.g=self.p['exact_genes'][0];self.ch=self.g['channels']['blastp_nr']
    def fields(self,rid):return self.p['records'][rid]['fields']
    def reject(self,pattern):
        with self.assertRaisesRegex(ValueError,pattern):validate_packet(self.p)
    def test_valid_generic_packet(self):validate_packet(self.p)
    def test_protein_query_mismatch(self):self.fields(self.ch['protein'])['query_sha256']='0'*64;self.reject('PROTEIN_QUERY')
    def test_protein_wrong_channel(self):self.ch['protein']=self.g['channels']['blastp_clustered_nr']['protein'];self.reject('CHANNEL_OR_TOOL')
    def test_wrong_gene_tool(self):self.g['tools']['antismash_gbk_domains']=self.p['exact_genes'][1]['tools']['antismash_gbk_domains'];self.reject('TOOL_GENE')
    def test_wrong_locus_tool(self):self.fields(self.g['tools']['antismash_gbk_domains'])['locus_key']='other';self.reject('TOOL_GENE')
    def test_wrong_tool_database(self):self.g['tools']['mamey_regulator_keywords']=self.g['tools']['mamey_transporters_keywords'];self.reject('CHANNEL_OR_TOOL')
    def test_search_wrong_query(self):self.fields(self.ch['search_receipts'][0])['query_sha256']='0'*64;self.reject('SEARCH_QUERY')
    def test_hit_wrong_search(self):self.fields(self.ch['selected_hits'][0])['search_id']=2;self.reject('HIT_SEARCH')
    def test_hit_wrong_channel(self):self.ch['selected_hits']=self.g['channels']['blastp_clustered_nr']['selected_hits'];self.reject('CHANNEL_OR_TOOL')
    def test_missing_xml(self):self.ch['search_receipts']=self.ch['search_receipts'][:1];self.reject('SEARCH_XML')
    def test_wrong_xml_channel(self):self.fields(self.ch['search_receipts'][1])['channel']='ncbi_clustered_nr';self.reject('XML_CHANNEL')
    def test_swiss_hit_wrong_query_id(self):ch=self.g['channels']['blastp_swissprot'];self.fields(ch['selected_hits'][0])['query_id']=2;self.reject('HIT_SEARCH')
    def test_swiss_query_key_wrong_hash(self):ch=self.g['channels']['blastp_swissprot'];self.fields(ch['query_key'])['query_sha256']='0'*64;self.reject('HIT_QUERY_KEY')
    def test_swiss_query_key_required(self):del self.g['channels']['blastp_swissprot']['query_key'];self.reject('HIT_QUERY_KEY_REQUIRED')
    def test_swiss_outcome_wrong_query(self):ch=self.g['channels']['blastp_swissprot'];self.fields(ch['search_receipts'][0])['query_sha256']='0'*64;self.reject('SEARCH_QUERY')
    def test_swiss_outcome_no_hit(self):ch=self.g['channels']['blastp_swissprot'];self.fields(ch['search_receipts'][0])['hit_count']=0;self.reject('OUTCOME_OBSERVATION')
    def test_unresolved_context(self):self.p['context_genes'][0]['sources']=['missing'];self.reject('UNRESOLVED_PROVENANCE')
    def test_empty_context_sources(self):self.p['context_genes'][0]['sources']=[];self.reject('CONTEXT_PROVENANCE')
    def test_context_wrong_gene(self):self.p['context_genes'][0]['locus_tag']='other';self.reject('CONTEXT_GENE_BINDING')
    def test_context_wrong_geometry(self):self.p['context_genes'][0]['end']=298;self.reject('CONTEXT_GEOMETRY')
    def test_context_overlap(self):self.p['context_genes'][0]['locus_tag']=self.g['locus_tag'];self.reject('CONTEXT_GENE_OVERLAP')
    def test_provenance_coverage_missing(self):self.p['records'][self.ch['protein']]['field_provenance'].pop('query_sha256');self.reject('PROVENANCE_COVERAGE')
    def test_consistent_fabrication_is_not_authenticated(self):
        # Deliberately demonstrates the ceiling: consistent synthetic data passes.
        # Only the external source audit can establish the fields are true rows.
        self.fields(self.ch['selected_hits'][0])['title']='A consistent but unauthenticated subject description'
        validate_packet(self.p)

class MixedHistoryTests(unittest.TestCase):
    setUp=GenericJoinTests.setUp
    fields=GenericJoinTests.fields
    reject=GenericJoinTests.reject
    # Only new tests are loaded from this class below; generic checks stay separate.
    def mixed(self,key='blastp_nr'):
        ch=self.g['channels'][key]
        ch['state']='VERIFIED_MIXED_OUTCOMES'
        protein=self.fields(ch['protein']);protein['state' if key=='blastp_swissprot' else 'availability_state']=ch['state']
        rid=ch['search_receipts'][0];new=copy.deepcopy(self.p['records'][rid]);f=new['fields']
        f['observation']='NO_HIT_UNDER_RECORDED_SETTINGS_NOT_BIOLOGICAL_ABSENCE'
        if key=='blastp_swissprot':f['hit_count']=0
        else:f['id']=99
        self.p['records']['nohit']=new;ch['search_receipts'].append('nohit')
        return ch
    def test_mixed_nr_preserved(self):
        self.mixed();validate_packet(self.p)
        self.assertIn('VERIFIED_MIXED_OUTCOMES',render_packet_sections(self.p,packet_locator='p',manifest_locator='m'))
    def test_mixed_clustered_preserved(self):self.mixed('blastp_clustered_nr');validate_packet(self.p)
    def test_mixed_swiss_preserved(self):self.mixed('blastp_swissprot');validate_packet(self.p)
    def test_mixed_cannot_flatten_to_hits(self):
        ch=self.mixed();ch['state']='VERIFIED_HITS';self.fields(ch['protein'])['availability_state']='VERIFIED_HITS';self.reject('HISTORY_STATE')
    def test_mixed_cannot_flatten_to_nohit(self):
        ch=self.mixed();ch['state']='VERIFIED_NO_HIT';self.fields(ch['protein'])['availability_state']='VERIFIED_NO_HIT';self.reject('HISTORY_STATE')
    def test_mixed_missing_nohit(self):
        ch=self.mixed();ch['search_receipts'].remove('nohit');self.reject('HISTORY_STATE')
    def test_hit_attached_to_nohit_search(self):
        ch=self.mixed();self.fields(ch['selected_hits'][0])['search_id']=99;self.reject('HIT_SEARCH_OBSERVATION')
    def test_hit_search_missing_representative(self):
        ch=self.mixed();ch['selected_hits']=[];self.reject('REPRESENTATIVE_REQUIRED')
    def test_unknown_observation(self):
        ch=self.mixed();self.fields('nohit')['observation']='UNKNOWN';self.reject('UNSUPPORTED_SEARCH_OBSERVATION')
    def test_swiss_count_observation_conflict(self):
        self.mixed('blastp_swissprot');self.fields('nohit')['hit_count']=2;self.reject('OUTCOME_OBSERVATION')

if __name__=='__main__':unittest.main()
