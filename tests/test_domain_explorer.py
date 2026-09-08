"""Generic controls; fixture labels are not scientific observations."""
import importlib.util,json,pathlib,sqlite3,tempfile,unittest
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from build_domain_explorer import arrangements,identity,build,sha,parent_matches

class Rules(unittest.TestCase):
    def test_reverse_order(self):
        fs=[dict(start=1,end=3,domain='X'),dict(start=5,end=7,domain='Y')]
        self.assertEqual(arrangements(fs,-1)[1],['Y','X'])
    def test_duplicates(self):
        f=dict(start=1,end=3,domain='X');self.assertEqual(arrangements([f,f],1)[3],1)
    def test_overlapping_order_held(self):
        fs=[dict(start=1,end=4,domain='X'),dict(start=4,end=7,domain='Y')]
        self.assertTrue(arrangements(fs,1)[2]);self.assertEqual(arrangements(fs,1)[0],['X','Y'])
    def test_unknown_strand_held(self):self.assertTrue(arrangements([dict(start=1,end=3,domain='X')],None)[2])
    def test_missing_identity(self):
        with self.assertRaises(ValueError):identity(dict(strain='Fixture',full_node='',region='region001',bgc_alias='cluster001',exact_identity=''))
    def test_conflicting_identity(self):
        with self.assertRaises(ValueError):identity(dict(strain='Fixture',full_node='contig',region='region001',bgc_alias='cluster001',exact_identity='wrong'))
    def test_multiplicity(self):
        fs=[dict(start=1,end=3,domain='X'),dict(start=5,end=7,domain='X')]
        sets,ordered,_,_=arrangements(fs,1);self.assertEqual(sets,['X']);self.assertEqual(ordered,['X','X'])
    def test_population_rejected_before_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);(p/'RELEASE_MANIFEST.json').write_text(json.dumps({'binding':{'census_sha256':'population-A'}}))
            with self.assertRaisesRegex(ValueError,'POPULATION_BINDING_HOLD'):build(p/'source.sqlite',p/'reader.py',p/'out',p/'view.html',expected_census='population-B')
    def test_changed_reader_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);(p/'reader.py').write_text('tampered');(p/'RELEASE_MANIFEST.json').write_text(json.dumps({'binding':{'census_sha256':'a'},'reader_sha256':'wrong'}))
            with self.assertRaisesRegex(ValueError,'READER_MANIFEST_HOLD'):build(p/'source.sqlite',p/'reader.py',p/'out',p/'view.html',expected_census='a')
    def test_wrong_assembly_protein_strand(self):
        f=dict(strain='Fixture',contig='contig_full',strand=1)
        p=dict(locus_tag='gene1',protein_sha256='a'*64,cds_start=1,cds_end=300,strand=1)
        g=dict(strain='Fixture',contig='contig_full',tag='gene1',protein_sha256='a'*64,start=1,end=300,strand=1)
        self.assertTrue(parent_matches(f,p,g))
        for key,value in [('contig','wrong_assembly'),('protein_sha256','b'*64),('strand',-1)]:
            wrong={**g,key:value};self.assertFalse(parent_matches(f,p,wrong))

class ProjectionFixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.tmp.name)
        self.reader=self.p/'reader.py'
        self.reader.write_text("import hashlib,json\nfrom pathlib import Path\ndef read(p,limit=1):\n m=json.loads((Path(p).parent/'RELEASE_MANIFEST.json').read_text())\n if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=m['database_sha256']:raise ValueError('DATABASE_MANIFEST_HOLD')\n return {'rows':[]}\n")
        db=self.p/'source.sqlite';c=sqlite3.connect(db)
        c.executescript('''CREATE TABLE locus(locus_key,strain,full_node,region,bgc_alias,exact_identity,start,end,source_member,source_member_sha256,products_json);
CREATE TABLE gene(locus_key,membership,locus_tag,start,end,strand,protein_sha256);
CREATE TABLE feature(strain,feature_order,contig,start,end,strand,feature_type,locus_tag,domain,database_name,bitscore,evalue_raw,source_member,source_member_sha256,source_feature_indices_json,source_location,qualifiers_sha256,frame,binding_json);
CREATE TABLE source(strain,source_locator,source_sha256,model_input_sha256);
CREATE TABLE section_profile(profile_sha256,bundle_version,member,contract_text);
CREATE TABLE section_relevance(section_number,profile_sha256,requirement,relation);''')
        for n in (1,2):
            parts=['Fixture','contig_full','region00'+str(n),'cluster00'+str(n)]
            c.execute('insert into locus values(?,?,?,?,?,?,?,?,?,?,?)',(str(n),*parts,' / '.join(parts),1,300,'source.gbk','c'*64,'["fixture-class"]'))
            c.execute('insert into gene values(?,?,?,?,?,?,?)',(str(n),'EXACT_REGION','gene1',1,300,1,'a'*64))
        c.execute('insert into gene values(?,?,?,?,?,?,?)',('1','OVERLAPPING_BOUNDARY_CONTEXT','boundary',1,300,1,'b'*64))
        parent=dict(aa_length=100,cds_start=1,cds_end=300,locus_tag='gene1',protein_sha256='a'*64,strand=1)
        binding=json.dumps(dict(state='SOURCE_PROTEIN_AND_GEOMETRY_BOUND',holds=[],parents=[parent]))
        for n,label in enumerate(('X','Y'),1):c.execute('insert into feature values('+','.join('?'*19)+')',('Fixture',n,'contig_full',n*20,n*20+9,1,'aSDomain','gene1',label,'fixture-v1',10,'1e-3','whole.gbk','c'*64,'[1]','source interval','d'*64,'WHOLE_RECORD_1_BASED_INCLUSIVE',binding))
        text='Requirement 24; Requirement 32; Requirement 44; Requirement 50'
        import hashlib
        ph=hashlib.sha256(text.encode()).hexdigest();c.execute('insert into section_profile values(?,?,?,?)',(ph,'fixture','contract.md',text))
        for n in (24,32,44,50):c.execute('insert into section_relevance values(?,?,?,?)',(n,ph,'Requirement '+str(n),'PARTIAL'))
        c.commit();c.close();self.db=db
        self.manifest=self.p/'RELEASE_MANIFEST.json';self.seal()
        self.template=self.p/'view.html';self.template.write_text('<script>const D=__DATA__</script>')
    def seal(self):self.manifest.write_text(json.dumps(dict(binding={'census_sha256':'fixture-population'},reader_sha256=sha(self.reader),database_sha256=sha(self.db),status='FIXTURE')))
    def run_build(self):return build(self.db,self.reader,self.p/'out',self.template,population='fixture only',expected_census='fixture-population')
    def tearDown(self):self.tmp.cleanup()
    def test_overlap_memberships_and_boundary_exclusion(self):
        d=self.run_build();self.assertEqual(d['counts']['physical_genes'],1);self.assertEqual(d['counts']['gene_occurrences'],2);self.assertEqual(d['counts']['exclusions']['boundary_context_gene_occurrences'],1)
        self.assertEqual(d['patterns'][0]['evidence'],[0]);self.assertEqual(d['evidence'][0]['loci'],[0,1])
    def test_source_tamper(self):
        with self.db.open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(ValueError,'DATABASE_MANIFEST_HOLD'):self.run_build()
    def test_resume_and_output_tamper(self):
        d=self.run_build();self.assertEqual(d,self.run_build());(self.p/'out/index.html').write_text('changed')
        with self.assertRaisesRegex(ValueError,'RESUME_OUTPUT_TAMPER'):self.run_build()
    def test_orphan_gene(self):
        c=sqlite3.connect(self.db);c.execute("insert into gene values('missing','EXACT_REGION','gene2',1,300,1,'hash')");c.commit();c.close();self.seal()
        with self.assertRaisesRegex(ValueError,'ORPHAN_GENE_HOLD'):self.run_build()

if __name__=='__main__':unittest.main()
