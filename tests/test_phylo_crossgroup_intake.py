import importlib.util
import hashlib
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import warnings

spec = importlib.util.spec_from_file_location('intake', Path(__file__).resolve().parents[1] / 'tools/phylo_crossgroup_intake.py')
intake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intake)

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        p = self.root / 'data'
        p.write_text('synthetic input')
        self.p = str(p)
        self.sha = hashlib.sha256(p.read_bytes()).hexdigest()
        self.m = {'schema':'cross-group-phylo-intake-v1', 'group':'algae', 'question':'synthetic', 'lineage':'unresolved', 'tree_scope':'synthetic', 'method_description':'planning only', 'data_kind':'marker', 'marker':'example', 'records':[]}
        for role in ('query','ingroup','outgroup'):
            self.m['records'].append({'id':role, 'role':role, 'taxon_label':role, 'source':'synthetic', 'accession':role, 'kind':'marker', 'path':self.p, 'sha256':self.sha})
    def run_check(self):
        p = self.root / 'manifest.json'; p.write_text(json.dumps(self.m)); return intake.check(p, [self.root])
    def test_valid_is_hold_not_scientific_pass(self):
        r = self.run_check(); self.assertEqual(r['status'], 'HOLD'); self.assertFalse(r['errors']); self.assertTrue(r['holds'])
    def test_io_estimate_counts_repeated_paths_without_reading_inputs(self):
        self.m['records'][1].update(file_scope='archive',source_format='zip')
        manifest=self.root/'estimate.json';manifest.write_text(json.dumps(self.m))
        original=Path.open
        def forbid_input_read(path,*args,**kwargs):
            if path == Path(self.p):
                raise AssertionError('estimator opened the input data')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',forbid_input_read):
            result=intake.estimate_io(manifest,[self.root])
        self.assertEqual(result['status'],'ESTIMATE_ONLY')
        size=Path(self.p).stat().st_size
        self.assertEqual([r['planned_full_file_scans'] for r in result['records']],[1,3,1])
        self.assertEqual(result['planned_full_scan_bytes'],5*size)
        self.assertTrue(result['records'][1]['additional_member_decompression'])
    def test_io_estimate_rejects_missing_and_out_of_root(self):
        manifest=self.root/'estimate.json';self.m['records'][0]['path']=str(self.root/'missing');manifest.write_text(json.dumps(self.m))
        self.assertEqual(intake.estimate_io(manifest,[self.root])['status'],'ERROR')
        self.assertEqual(intake.estimate_io(manifest,[])['status'],'ERROR')

    def test_missing_data_and_wrong_hash_are_errors(self):
        self.m['records'][0]['sha256'] = 'a'*64
        self.m['records'][1]['path'] = str(self.root/'missing')
        self.assertEqual(len(self.run_check()['errors']), 2)
    def test_duplicate_and_kind_and_missing_role(self):
        self.m['records'][1].update(id='query', kind='genome', role='query')
        errors = ' '.join(self.run_check()['errors'])
        self.assertIn('duplicate id', errors); self.assertIn('kind does not match', errors); self.assertIn('missing ingroup', errors)
    def test_registry_banned_and_scope_hold(self):
        registry = self.root/'registry.tsv'
        registry.write_text('# comment\ntree_scope\tingroup_taxon\tmarker_accession\tstatus\nBANNED\t-\toutgroup\tBANNED\n')
        self.m.update(group='fungi', fungal_registry={'path':str(registry), 'sha256':hashlib.sha256(registry.read_bytes()).hexdigest()})
        r = self.run_check(); self.assertIn('BANNED accession', ' '.join(r['errors']))
        self.assertIn('textual-name comparison unavailable', ' '.join(r['holds']))
        self.m['fungal_registry']['sha256'] = '0'*64
        self.assertIn('SHA-256 mismatch', ' '.join(self.run_check()['errors']))
    def test_fungal_registry_selection_binds_one_exact_row_and_outgroup(self):
        registry=self.root/'registry.tsv'
        registry.write_text('tree_scope\tingroup_taxon\tmarker_accession\tstatus\nfamily\tExampleaceae\tNG_123456.1\tCONFIRM\n')
        selection={'tree_scope':'family','ingroup_taxon':'Exampleaceae','accession':'ng_123456.1'}
        self.m.update(group='fungi',fungal_registry={'path':str(registry),'sha256':hashlib.sha256(registry.read_bytes()).hexdigest(),'selection':selection})
        self.m['records'][2]['accession']='NG_123456.1'
        result=self.run_check();self.assertEqual(result['status'],'HOLD');self.assertIn('selected row bound', ' '.join(result['observations']))
        selection['ingroup_taxon']='Otheraceae';self.assertIn('matches 0 rows',' '.join(self.run_check()['errors']))
        selection['ingroup_taxon']='Exampleaceae';self.m['records'][2]['accession']='NG_123456.2'
        self.assertIn('not a declared outgroup',' '.join(self.run_check()['errors']))
        self.m['records'][2]['accession']='NG_123456.1'
        registry.write_text(registry.read_text()+'family\tExampleaceae\tNG_123456.1\tCONFIRM\n')
        self.m['fungal_registry']['sha256']=hashlib.sha256(registry.read_bytes()).hexdigest()
        self.assertIn('matches 2 rows',' '.join(self.run_check()['errors']))
    def test_fungal_selection_rejects_banned_and_incomplete(self):
        registry=self.root/'registry.tsv'
        registry.write_text('tree_scope\tingroup_taxon\tmarker_accession\tstatus\nfamily\tExampleaceae\tNG_123456.1\tBANNED\n')
        self.m.update(group='fungi',fungal_registry={'path':str(registry),'sha256':hashlib.sha256(registry.read_bytes()).hexdigest(),'selection':{'tree_scope':'family','ingroup_taxon':'Exampleaceae','accession':'NG_123456.1'}})
        self.m['records'][2]['accession']='NG_123456.1'
        self.assertIn('selected row is BANNED',' '.join(self.run_check()['errors']))
        self.m['fungal_registry']['selection']={'tree_scope':'family'}
        self.assertIn('selection requires',' '.join(self.run_check()['errors']))

    def test_registry_possible_exclusions_are_holds_not_identity_claims(self):
        registry = self.root/'registry.tsv'
        registry.write_text('tree_scope\tingroup_taxon\tmarker_accession\tstatus\toutgroup_species_strain\nBANNED\t-\tGCF_123456789.1\tBANNED\t[Example] species STRAIN\n')
        self.m.update(group='fungi', fungal_registry={'path':str(registry), 'sha256':hashlib.sha256(registry.read_bytes()).hexdigest()})
        self.m['data_kind'] = 'genome'
        for rec in self.m['records']: rec['kind'] = 'genome'
        self.m['records'][1].update(accession='GCF_123456789.2', taxon_label='Example species STRAIN')
        r = self.run_check()
        self.assertEqual(r['status'], 'HOLD')
        self.assertIn('possible BANNED accession version', ' '.join(r['holds']))
        self.assertIn('possible BANNED textual-name', ' '.join(r['holds']))
        self.assertFalse(r['errors'])
    def test_versioned_ncbi_accession_case_cannot_bypass_ban_or_roles(self):
        registry=self.root/'registry.tsv'
        registry.write_text('tree_scope\tingroup_taxon\tmarker_accession\tstatus\nBANNED\t-\tGCF_123456789.1\tBANNED\n')
        self.m.update(group='fungi', data_kind='genome', fungal_registry={'path':str(registry), 'sha256':hashlib.sha256(registry.read_bytes()).hexdigest()})
        for rec in self.m['records']: rec['kind']='genome'
        self.m['records'][1]['accession']='gcf_123456789.1'
        self.m['records'][2]['accession']='GCF_123456789.1'
        errors=' '.join(self.run_check()['errors'])
        self.assertIn('BANNED accession',errors)
        self.assertIn('conflicting outgroup',errors)
        self.m['data_kind']='marker'
        for rec in self.m['records']: rec['kind']='marker'
        self.assertIn('assembly accession', ' '.join(self.run_check()['errors']))
        self.assertNotEqual(intake.accession_key('CustomID'),intake.accession_key('customid'))

    def test_no_version_equivalence_for_unversioned_accessions(self):
        self.assertIsNone(intake.accession_stem('GCF_123456789'))
        self.assertNotEqual(intake.accession_stem('GCF_123456789.1'), intake.accession_stem('GCA_123456789.1'))
    def test_sequence_extent_distinguishes_chromosome_from_assembly(self):
        self.m['group']='cyanobacteria';self.m['data_kind']='genome'
        for rec in self.m['records']: rec.update(kind='genome',sequence_extent='whole_assembly')
        self.m['records'][0]['sequence_extent']='chromosome'
        result=self.run_check();self.assertEqual(result['status'],'HOLD')
        self.assertIn('do not assume a complete multi-replicon assembly',' '.join(result['holds']))
        self.assertIn('declared sequence extent whole_assembly; not verified',' '.join(result['observations']))
        self.m['records'][0]['sequence_extent']='unknown'
        self.assertIn('sequence extent is unknown',' '.join(self.run_check()['holds']))
        self.m['records'][0]['sequence_extent']='invented'
        self.assertIn('invalid sequence_extent',' '.join(self.run_check()['errors']))
    def test_marker_genome_extent_conflicts_are_review_holds(self):
        self.m['records'][0]['sequence_extent']='whole_assembly'
        self.assertIn('marker comparison with non-marker sequence extent',' '.join(self.run_check()['holds']))
        self.m['data_kind']='genome'
        for rec in self.m['records']: rec['kind']='genome'
        self.m['records'][0]['sequence_extent']='single_marker'
        self.assertIn('single marker declared for genome comparison',' '.join(self.run_check()['holds']))

    def test_cyanobacteria_are_distinct_and_held(self):
        self.m['group'] = 'cyanobacteria'
        result = self.run_check()
        self.assertEqual(result['status'], 'HOLD')
        self.assertIn('Cyanobacteria are bacteria', ' '.join(result['holds']))
    def test_conflicting_roles_and_marker_genome_accession(self):
        self.m['records'][2]['accession'] = 'query'
        self.m['records'][1]['accession'] = 'GCF_123456789.1'
        errors = ' '.join(self.run_check()['errors'])
        self.assertIn('conflicting outgroup', errors)
        self.assertIn('assembly accession', errors)
    def test_identical_bytes_in_opposing_roles_are_reviewed(self):
        for rec in self.m['records']:
            rec['file_scope'] = 'single_record'
        result = self.run_check()
        self.assertEqual(result['status'], 'HOLD')
        self.assertIn('identical source bytes span outgroup', ' '.join(result['holds']))
        self.m['records'][2]['sha256'] = 'a' * 64
        result = self.run_check()
        self.assertEqual(result['status'], 'ERROR')
        self.assertNotIn('identical source bytes span outgroup', ' '.join(result['holds']))

    def test_distinct_locators_in_same_multirecord_source_do_not_imply_conflict(self):
        for rec, token in zip(self.m['records'], ('q', 'i', 'o')):
            rec.update(file_scope='multi_record', record_locator=token)
        self.assertNotIn('identical source bytes span outgroup', ' '.join(self.run_check()['holds']))
        self.m['records'][2]['record_locator'] = 'q'
        self.assertIn('identical source bytes span outgroup', ' '.join(self.run_check()['holds']))

    def test_zip_member_hash_and_exact_path(self):
        archive=self.root/'source.zip'
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('a/record.gbk',b'first')
            z.writestr('b/record.gbk',b'second')
        rec=self.m['records'][1]
        rec.update(path=str(archive), sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                   file_scope='archive', source_format='zip', record_locator='a/record.gbk',
                   member_sha256=hashlib.sha256(b'first').hexdigest())
        result=self.run_check()
        self.assertEqual(result['status'],'HOLD')
        self.assertIn('exact ZIP member bytes match', ' '.join(result['observations']))
        self.assertIn('archive locator supplied', ' '.join(result['holds']))
        rec['record_locator']='b/record.gbk'
        self.assertIn('member SHA-256 mismatch', ' '.join(self.run_check()['errors']))
        rec['record_locator']='record.gbk'
        self.assertIn('occurs 0 times', ' '.join(self.run_check()['errors']))
        rec['record_locator']='a/record.gbk';rec['sha256']='0'*64
        self.assertIn('SHA-256 mismatch', ' '.join(self.run_check()['errors']))

    def test_zip_fasta_record_locator_is_counted_in_verified_member(self):
        archive=self.root/'source.zip'
        content=b'>ABC.1 details\nACGT\n>XYZ.1\nTT\n'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('input/genome.fna',content)
        rec=self.m['records'][1]
        rec.update(path=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                   file_scope='archive',source_format='zip',record_locator='input/genome.fna',
                   member_sha256=hashlib.sha256(content).hexdigest(),member_format='fasta',member_record_locator='ABC.1')
        result=self.run_check();self.assertEqual(result['status'],'HOLD')
        self.assertIn('declared ZIP FASTA header token occurs exactly once',' '.join(result['observations']))
        rec['member_record_locator']='missing'
        self.assertIn('occurs 0 times',' '.join(self.run_check()['errors']))
        rec['member_record_locator']='ABC.1';rec['member_sha256']='0'*64
        result=self.run_check();self.assertEqual(result['status'],'ERROR')
        self.assertNotIn('declared ZIP FASTA header token occurs',' '.join(result['observations']))
        rec['member_sha256']=hashlib.sha256(content).hexdigest();rec['member_format']='gbk'
        self.assertIn('requires member_format fasta',' '.join(self.run_check()['errors']))
        rec.update(file_scope='single_record',source_format='unknown')
        self.assertIn('requires ZIP archive scope',' '.join(self.run_check()['errors']))
    def test_zip_fasta_duplicate_locator_is_refused(self):
        archive=self.root/'source.zip';content=b'>ABC.1\nA\n>ABC.1\nT\n'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('genome.fna',content)
        self.m['records'][1].update(path=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            file_scope='archive',source_format='zip',record_locator='genome.fna',
            member_sha256=hashlib.sha256(content).hexdigest(),member_format='fasta',member_record_locator='ABC.1')
        self.assertIn('occurs 2 times',' '.join(self.run_check()['errors']))

    def test_same_verified_member_across_archives_and_roles_is_held(self):
        content=b'same member bytes'
        for number in (0, 2):
            archive=self.root/f'source{number}.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr(f'member{number}.gbk', content)
                z.writestr('distinguishing-content',str(number))
            self.m['records'][number].update(path=str(archive), sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                file_scope='archive', source_format='zip', record_locator=f'member{number}.gbk',
                member_sha256=hashlib.sha256(content).hexdigest())
        result=self.run_check()
        self.assertIn('identical verified ZIP member bytes span outgroup', ' '.join(result['holds']))
        self.m['records'][2]['member_sha256']='0'*64
        result=self.run_check()
        self.assertEqual(result['status'],'ERROR')
        self.assertNotIn('identical verified ZIP member bytes span outgroup', ' '.join(result['holds']))

    def test_zip_duplicate_member_and_size_limit_are_refused(self):
        archive=self.root/'source.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('same',b'one');z.writestr('same',b'two')
        rec=self.m['records'][1]
        rec.update(path=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                   file_scope='archive',source_format='zip',record_locator='same',member_sha256=hashlib.sha256(b'one').hexdigest())
        self.assertIn('occurs 2 times', ' '.join(self.run_check()['errors']))
        with zipfile.ZipFile(archive,'w') as z:z.writestr('same',b'one')
        rec['sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
        previous=intake.MAX_ZIP_MEMBER_BYTES
        try:
            intake.MAX_ZIP_MEMBER_BYTES=2
            self.assertIn('read limit', ' '.join(self.run_check()['errors']))
        finally: intake.MAX_ZIP_MEMBER_BYTES=previous

    def test_compartments_separate_known_unknown_and_conflict(self):
        for rec in self.m['records']: rec['compartment'] = 'nuclear'
        result = self.run_check()
        self.assertNotIn('biological compartment', ' '.join(result['holds']))
        self.m['records'][1]['compartment'] = 'plastid'
        self.assertIn('differing biological compartments', ' '.join(self.run_check()['holds']))
        self.m['records'][2]['compartment'] = 'unknown'
        self.assertIn('compartment is not established', ' '.join(self.run_check()['holds']))
        self.m['records'][2]['compartment'] = 'mixed'
        self.assertIn('mixed compartments', ' '.join(self.run_check()['holds']))
    def test_group_compartment_conflicts_remain_holds(self):
        self.m['group'] = 'cyanobacteria'
        for rec in self.m['records']: rec['compartment'] = 'plastid'
        self.assertIn('Eukaryotic compartments declared', ' '.join(self.run_check()['holds']))
        self.m['group'] = 'algae'
        for rec in self.m['records']: rec['compartment'] = 'bacterial'
        self.assertIn('Bacterial compartment declared', ' '.join(self.run_check()['holds']))
    def test_file_scope_records_explicit_member_holds(self):
        self.m['records'][0]['file_scope'] = 'multi_record'
        self.assertIn('record_locator required', ' '.join(self.run_check()['errors']))
        self.m['records'][0]['record_locator'] = 'ID.1'
        self.assertIn('does not verify the member or record identity', ' '.join(self.run_check()['holds']))
        self.m['records'][0]['file_scope'] = 'archive'
        self.assertIn('archive locator supplied', ' '.join(self.run_check()['holds']))
        self.m['records'][0]['file_scope'] = []
        self.assertIn('invalid file_scope', ' '.join(self.run_check()['errors']))
    def test_fasta_header_locator_is_counted_in_hashed_bytes(self):
        p=self.root/'multiple.fa'; p.write_text('>ABC.1 first\nACGT\n>DEF.1 second\nACGT\n')
        rec=self.m['records'][1];rec.update(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),file_scope='multi_record',source_format='fasta',record_locator='ABC.1')
        result=self.run_check()
        self.assertIn('header token occurs exactly once', ' '.join(result['observations']))
        self.assertIn('biological identity unverified', ' '.join(result['observations']))
        rec['record_locator']='MISSING'
        self.assertIn('occurs 0 times', ' '.join(self.run_check()['errors']))
        p.write_text('>ABC.1\nAC\n>ABC.1 second\nGT\n');rec.update(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),record_locator='ABC.1')
        self.assertIn('occurs 2 times', ' '.join(self.run_check()['errors']))
    def test_fasta_streams_long_sequence_and_chunk_boundary_headers(self):
        p=self.root/'large.fa'
        data=b'>other\n'+b'A'*(1024*1024-8)+b'\n>ABC.1 description\r\n'+b'C'*(2*1024*1024)+b'\n>ABC.1 final'
        p.write_bytes(data)
        digest, count=intake.fasta_digest_and_count(p,'ABC.1')
        self.assertEqual(digest,hashlib.sha256(data).hexdigest())
        self.assertEqual(count,2)
    def test_fasta_refuses_overlong_header(self):
        p=self.root/'header.fa';p.write_bytes(b'>'+b'A'*(intake.MAX_FASTA_HEADER_BYTES+1)+b'\n')
        with self.assertRaisesRegex(ValueError,'header exceeds'):
            intake.fasta_digest_and_count(p,'A')

    def test_gzip_fasta_locator_and_resource_estimate(self):
        source=self.root/'source.fna.gz';raw=b'>ABC.1 description\nACGT\n>XYZ.1\nTT\n';source.write_bytes(gzip.compress(raw))
        rec=self.m['records'][1];rec.update(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            file_scope='multi_record',source_format='fasta_gzip',record_locator='ABC.1')
        result=self.run_check();self.assertEqual(result['status'],'HOLD')
        self.assertIn('gzip FASTA header token occurs exactly once',' '.join(result['observations']))
        manifest=self.root/'estimate.json';manifest.write_text(json.dumps(self.m))
        estimate=intake.estimate_io(manifest,[self.root]);self.assertEqual(estimate['records'][1]['planned_full_file_scans'],3)
        self.assertTrue(estimate['records'][1]['additional_gzip_decompression'])
        rec['record_locator']='missing';self.assertIn('occurs 0 times',' '.join(self.run_check()['errors']))
        rec['record_locator']='ABC.1';rec['sha256']='0'*64
        self.assertNotIn('gzip FASTA header token occurs',' '.join(self.run_check()['observations']))
        rec['file_scope']='single_record';self.assertIn('fasta_gzip requires multi_record',' '.join(self.run_check()['errors']))
    def test_gzip_fasta_duplicate_corruption_and_size_limit(self):
        source=self.root/'source.fna.gz';raw=b'>ABC.1\nA\n>ABC.1\nT\n';source.write_bytes(gzip.compress(raw));rec=self.m['records'][1]
        rec.update(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),file_scope='multi_record',source_format='fasta_gzip',record_locator='ABC.1')
        self.assertIn('occurs 2 times',' '.join(self.run_check()['errors']))
        damaged=bytearray(source.read_bytes());damaged[-5] ^= 1;source.write_bytes(damaged);rec['sha256']=hashlib.sha256(damaged).hexdigest()
        result=self.run_check();self.assertEqual(result['status'],'ERROR')
        self.assertNotIn('gzip FASTA header token occurs',' '.join(result['observations']))
        source.write_bytes(gzip.compress(raw));rec['sha256']=hashlib.sha256(source.read_bytes()).hexdigest();previous=intake.MAX_GZIP_FASTA_BYTES
        try:
            intake.MAX_GZIP_FASTA_BYTES=3
            self.assertIn('64 MiB decompressed read limit',' '.join(self.run_check()['errors']))
        finally:intake.MAX_GZIP_FASTA_BYTES=previous

    def test_fasta_observation_never_given_for_wrong_hash(self):
        p=self.root/'one.fa';p.write_text('>A\nAC\n')
        self.m['records'][1].update(path=str(p),sha256='0'*64,file_scope='multi_record',source_format='fasta',record_locator='A')
        result=self.run_check()
        self.assertIn('SHA-256 mismatch', ' '.join(result['errors']))
        self.assertNotIn('header token occurs', ' '.join(result['observations']))
    def test_invalid_compartment_declaration_refused(self):
        self.m['records'][0]['compartment'] = ['nuclear']
        self.assertIn('invalid compartment declaration', ' '.join(self.run_check()['errors']))
    def test_invalid_json_types_do_not_crash(self):
        self.m['data_kind'] = []
        self.m['records'][0]['role'] = {}
        result = self.run_check()
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('invalid role', ' '.join(result['errors']))
    def test_malformed_registry_row_does_not_pass(self):
        registry = self.root/'registry.tsv'
        registry.write_text('tree_scope\tingroup_taxon\tmarker_accession\tstatus\ngenome\tA\tB\n')
        self.m.update(group='fungi', fungal_registry={'path':str(registry), 'sha256':hashlib.sha256(registry.read_bytes()).hexdigest()})
        self.assertIn('malformed or incomplete', ' '.join(self.run_check()['errors']))
    def test_duplicate_ids_with_whitespace_rejected(self):
        self.m['records'][1]['id'] = ' query '
        self.assertIn('duplicate id', ' '.join(self.run_check()['errors']))
    def test_outside_root_and_symlink_escape_refused(self):
        with tempfile.TemporaryDirectory() as other:
            external = Path(other)/'external'; external.write_text('outside')
            self.m['records'][0]['path'] = str(external)
            self.assertIn('outside permitted roots', ' '.join(self.run_check()['errors']))
            link = self.root/'escape'; link.symlink_to(external)
            self.m['records'][0]['path'] = str(link)
            self.assertIn('outside permitted roots', ' '.join(self.run_check()['errors']))
    def test_external_registry_is_refused_without_exception(self):
        with tempfile.TemporaryDirectory() as other:
            registry=Path(other)/'registry.tsv'; registry.write_text('synthetic')
            self.m.update(group='fungi', fungal_registry={'path':str(registry), 'sha256':hashlib.sha256(registry.read_bytes()).hexdigest()})
            self.assertIn('outside permitted roots', ' '.join(self.run_check()['errors']))
    def test_manifest_and_roots_must_be_authorized(self):
        p=self.root/'manifest.json'; p.write_text(json.dumps(self.m))
        self.assertEqual(intake.check(p, [])['status'], 'ERROR')
        self.assertEqual(intake.check(p, ['/not/an/existing/root'])['status'], 'ERROR')
        with tempfile.TemporaryDirectory() as other:
            self.assertIn('outside permitted roots', ' '.join(intake.check(p, [other])['errors']))
    def test_duplicate_manifest_keys_refused(self):
        p=self.root/'bad.json';p.write_text('{"schema":"a","schema":"b"}')
        self.assertIn('duplicate JSON key', ' '.join(intake.check(p, [self.root])['errors']))
    def test_duplicate_registry_columns_refused(self):
        registry=self.root/'registry.tsv'
        registry.write_text('tree_scope\tingroup_taxon\tmarker_accession\tstatus\tstatus\nBANNED\t-\toutgroup\tBANNED\tLOCKED\n')
        self.m.update(group='fungi', fungal_registry={'path':str(registry),'sha256':hashlib.sha256(registry.read_bytes()).hexdigest()})
        self.assertIn('duplicate columns', ' '.join(self.run_check()['errors']))
    def test_malformed_manifest(self):
        p=self.root/'bad'; p.write_text('{')
        self.assertEqual(intake.check(p, [self.root])['status'], 'ERROR')

if __name__ == '__main__': unittest.main()
