"""Batch route: one admitted roster, three record x bait pairs, per-pair lifecycle receipts.

Synthetic declarations and a synthetic shell launcher only; the real RiPPER source,
Perl, Prodigal and BLAST are never run. The launcher exits 0 for one pair and 3 for the
other so each pair's own EXECUTION_TERMINAL.json records its own outcome.
"""
from unittest import mock
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ripper_batch_adapter', ROOT / 'tools/ripper_adapter.py')
a = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(a)
m = a.owned_module('ripper_native_contract')
PROFILE = json.loads((ROOT / 'tools/ripper_source_profile.json').read_text())
try:
    import psutil  # noqa: F401
    from Bio import SeqIO
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False
if HAVE_DEPS:
    # Load the sibling fixture builders by path: tests/ is a package, so a bare import fails under pytest.
    _HSPEC = importlib.util.spec_from_file_location('ripper_batch_real_genome_inputs', ROOT / 'tests/test_ripper_real_genome_inputs.py')
    _h = importlib.util.module_from_spec(_HSPEC); _HSPEC.loader.exec_module(_h)
    build_record, standard_cdses, P_GTG, P_TTG, P_BAD, CONTIG = (
        _h.build_record, _h.standard_cdses, _h.P_GTG, _h.P_TTG, _h.P_BAD, _h.CONTIG)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@unittest.skipUnless(HAVE_DEPS, 'Biopython and psutil required')
class BatchRoute(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ.get('RIPPER_TEST_ROOT', tempfile.gettempdir())); base.mkdir(parents=True, exist_ok=True)
        self.work = Path(tempfile.mkdtemp(prefix=self._testMethodName + '-', dir=base))
        self.run_root = self.work / 'batch_run'
        shared = self.work / 'shared'; shared.mkdir()
        roles = {}
        for role in m.REQUIRED - {'genbank', 'query_fasta', 'queries'}:
            p = shared / role; p.write_text('SYNTHETIC_CONTRACT_ONLY_NOT_A_NATIVE_RESOURCE ' + role + '\n'); roles[role] = p
        launcher = roles['perl_runtime']
        launcher.write_text('#!/bin/sh\ncase "$*" in *pair_b*) exit 3;; esac\nexit 0\n')
        for role in m.TOOLS:
            roles[role].chmod(0o700)
        roles['config'].write_text('prodigalshortbin ' + str(roles['prodigal_short']) + '\nprepeptab ripper\n')
        roles['source_closure'].write_text(json.dumps({'schema': 'lane05-ripper-adapted-source-profile-v1', 'source_revision': PROFILE['revision'],
            'files': [{'role': k, 'sha256': sha(roles[v])} for k, v in {'archived_base': 'archived_base', 'adapted_source': 'upstream_source', 'cumulative_patch': 'source_patch'}.items()]}))
        lib = self.work / 'synthetic_perl_lib'
        for name, role in m.MODULE_ROLES.items():
            p = lib / Path(*name.split('::')).with_suffix('.pm'); p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('SYNTHETIC_NOT_NATIVE_MODULE ' + name + '\n'); roles[role] = p
        runtime = {'schema_version': 'ripper-native-runtime/1', 'state': 'PROBED_NATIVE_RUNTIME_CONTENT_UNATTESTED',
                   'tool_sha256': {k: sha(roles[k]) for k in m.TOOLS}, 'tool_versions': {k: 'SYNTHETIC_TEST_DECLARATION' for k in m.TOOLS},
                   'module_versions': {k: 'SYNTHETIC_TEST_DECLARATION' for k in m.MODULES}, 'perl5lib': [str(lib)],
                   'prodigal_short_validation': 'SHORT_ORF_BEHAVIOR_REVIEWED', 'blast_database_format_validation': 'REVIEWED_FOR_SELECTED_SOURCE',
                   'blast_pairwise_parser_validation': 'REVIEWED_FOR_SELECTED_BIOPERL', 'prodigal_recipe_sha256': sha(roles['prodigal_recipe']),
                   'probed_interpreter_sha256': sha(roles['perl_runtime']), 'tool_probe_exit_codes': {k: 0 for k in m.TOOLS},
                   'module_probe_exit_codes': {k: 0 for k in m.MODULES},
                   'module_sha256': {k: sha(roles[v]) for k, v in m.MODULE_ROLES.items()}, 'module_paths': {k: str(roles[v]) for k, v in m.MODULE_ROLES.items()}}
        roles['runtime_receipt'].write_text(json.dumps(runtime))
        self.roles = roles
        self.adapted = self.work / 'ADAPTED_SOURCE_PROFILE.json'; self.adapted.write_text('{"synthetic": "adapted profile declaration"}\n')
        # Three pairs on one record: two valid baits (GTG and TTG starts) and one invalid bait.
        pairs = self.work / 'pairs'; pairs.mkdir()
        record = build_record(standard_cdses())
        self.pair_files = {}
        rows = []
        for pair_id, tag, protein in (('pair_a', 'TE_GTG', P_GTG), ('pair_b', 'TE_TTG', P_TTG), ('pair_c', 'BAD_CDS', P_BAD)):
            folder = pairs / pair_id; folder.mkdir()
            gbk = folder / (pair_id + '_region001.gbk'); faa = folder / 'bait.faa'
            SeqIO.write(record, gbk, 'genbank'); faa.write_text('>' + tag + '\n' + protein + '\n')
            self.pair_files[pair_id] = {'genbank': gbk, 'query_fasta': faa}
            rows.append({'pair_id': pair_id, 'enzyme_accession': tag, 'strain': 'AS-SYN', 'full_contig': CONTIG,
                         'region': 'region001', 'bgc_alias': 'AS-SYN_' + CONTIG + '.region001'})
        self.roster = self.work / 'roster.json'
        self.roster.write_text(json.dumps({'schema_version': 'ripper-queries/1', 'queries': rows}, indent=1) + '\n')
        self.spec = self.work / 'batch_spec.json'
        self.write_spec()

    def write_spec(self, **changes):
        spec = {'schema_version': 'ripper-lifecycle-batch-spec/1', 'mode': 'adapted_local05', 'profile_id': PROFILE['id'],
                'source_revision': PROFILE['revision'], 'limits': {'wall_seconds': 30, 'rss_bytes': 512 * 1024 ** 2, 'disk_bytes': 16 * 1024 ** 2, 'poll_seconds': 0.02},
                'shared_files': {k: sha(p) for k, p in self.roles.items()}, 'roster_sha256': sha(self.roster),
                'pair_files': {pid: {k: sha(p) for k, p in f.items()} for pid, f in self.pair_files.items()}}
        spec.update(changes); self.spec.write_text(json.dumps(spec, indent=1) + '\n')

    def api(self):
        api = a.binding_api(); owned = api['owned_module']; upstream = sha(self.roles['upstream_source'])
        dispatcher = sha(self.roles['perl_dispatcher']); adapted = sha(self.adapted)

        def modules(name):
            value = owned(name)
            if name == 'ripper_source_admission':
                value.NATIVE_INTERFACES = dict(value.NATIVE_INTERFACES, **{upstream: 'q3'})
                def verify_adapted(api_, path, bound, sources):
                    return {'artifact_sha256': adapted, 'adapted_profile_id': 'local05-synthetic',
                            'profile_status': 'EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY', 'upstream_execution': 'NOT_EXECUTED'}
                # owned_module loads a fresh private module copy on every call (never in sys.modules),
                # so this stub cannot leak to another test.
                setattr(value, 'verify_adapted', verify_adapted)
            if name == 'ripper_native_contract':
                value.DISPATCHER_SHA256 = dispatcher
            return value
        api['owned_module'] = modules
        return api

    def args(self):
        shared = [k + '=' + str(p) for k, p in self.roles.items()]
        paired = [pid + ':' + k + '=' + str(p) for pid, f in self.pair_files.items() for k, p in f.items()]
        return shared, paired

    def preflight(self):
        batch = a.owned_module('ripper_batch'); shared, paired = self.args()
        return batch.batch(self.api(), self.spec, self.roster, shared, paired, str(self.run_root), str(self.adapted))

    def execute(self, admission):
        batch = a.owned_module('ripper_batch'); shared, paired = self.args()
        return batch.batch(self.api(), self.spec, self.roster, shared, paired, str(self.run_root), str(self.adapted), True, str(admission), True)

    def approve(self):
        request = json.loads((self.run_root / 'BATCH_REVIEW_REQUEST.json').read_text())
        admission = dict(request, decision='APPROVED_NATIVE_LOCAL_EXECUTION', local_use_decision='REVIEWED_LOCAL_EXECUTION_ONLY_NO_DISTRIBUTION_CLEARANCE',
                         reviewer_note='synthetic test approval')
        path = self.work / 'BATCH_ADMISSION.json'; path.write_text(json.dumps(admission)); return path

    def test_preflight_writes_one_request_and_per_pair_receipts(self):
        """Fail-before: .463 has no batch route; one admission per single-query run."""
        data = self.preflight()
        self.assertEqual((data['status'], data['pair_count'], data['admissible_pair_count'], data['refused_pair_count']), ('HOLD', 3, 2, 1))
        self.assertEqual(data['upstream_execution'], 'NOT_EXECUTED')
        for pid in ('pair_a', 'pair_b'):
            names = {p.name for p in (self.run_root / 'pairs' / pid).iterdir()}
            # write_terminal keeps the staging bytes beside the canonical link; they are never a terminal.
            self.assertEqual(names, {'PREFLIGHT.json', 'TERMINAL.json', 'TERMINAL.json.staging', 'NATIVE_REVIEW_REQUEST.json'})
            self.assertEqual(json.loads((self.run_root / 'pairs' / pid / 'TERMINAL.json').read_text())['holds'], ['HOLD_LOCAL_SOURCE_EXECUTION_ADMISSION'])
        refused = json.loads((self.run_root / 'pairs/pair_c/PAIR_REFUSED.json').read_text())
        self.assertEqual(refused['status'], 'REFUSED_INPUT'); self.assertIn('CDS_TRANSLATION_INVALID: subject CDS BAD_CDS', refused['reason'])
        self.assertEqual(refused['query_identity'], 'AS-SYN / ' + CONTIG + ' / region001 / AS-SYN_' + CONTIG + '.region001')
        request = json.loads((self.run_root / 'BATCH_REVIEW_REQUEST.json').read_text())
        self.assertEqual(request['decision'], 'PENDING_PARENT_REVIEW')
        self.assertEqual([p['pair_id'] for p in request['pairs']], ['pair_a', 'pair_b'])
        for item in request['pairs']:
            self.assertEqual(item['review_request_sha256'], sha(self.run_root / 'pairs' / item['pair_id'] / 'NATIVE_REVIEW_REQUEST.json'))
        # Each pair's preflight binds the excluded invalid CDS inside its own semantic record.
        pre = json.loads((self.run_root / 'pairs/pair_a/PREFLIGHT.json').read_text())
        self.assertEqual([x['subject_cds_id'] for x in pre['native_contract']['semantic_validation']['excluded_cds']], ['BAD_CDS'])

    def test_derived_single_query_roster_copies_identity_verbatim(self):
        self.preflight()
        q = json.loads((self.run_root / 'inputs/pair_b/queries.json').read_text())
        self.assertEqual(q['queries'], [{'enzyme_accession': 'TE_TTG', 'strain': 'AS-SYN', 'full_contig': CONTIG, 'region': 'region001', 'bgc_alias': 'AS-SYN_' + CONTIG + '.region001'}])

    def test_one_admission_runs_every_admitted_pair_with_its_own_terminal(self):
        self.preflight(); data = self.execute(self.approve())
        self.assertEqual(data['status'], 'COMPLETE_PER_PAIR_TERMINALS')
        by_id = {p['pair_id']: p for p in data['pairs']}
        self.assertEqual(set(by_id), {'pair_a', 'pair_b'})
        self.assertEqual(by_id['pair_b']['reason'], 'EXIT_NONZERO')  # its own launcher exit, not pair_a's
        self.assertNotEqual(by_id['pair_a']['reason'], 'EXIT_NONZERO')
        for pid, outcome in by_id.items():
            terminal = json.loads((self.run_root / 'pairs' / pid / 'EXECUTION_TERMINAL.json').read_text())
            self.assertEqual(outcome['terminal_sha256'], sha(self.run_root / 'pairs' / pid / 'EXECUTION_TERMINAL.json'))
            self.assertEqual(terminal['status'], outcome['status'])
            self.assertEqual(terminal['candidate_bgc_membership'], 'UNVERIFIED'); self.assertFalse(terminal['biological_absence_inferred'])
            admission = json.loads((self.run_root / 'admissions' / (pid + '.json')).read_text())
            self.assertEqual(admission['batch_admission_sha256'], data['admission_sha256'])
        self.assertEqual(data['refused_at_preflight'][0]['pair_id'], 'pair_c')
        self.assertFalse((self.run_root / 'pairs/pair_c/EXECUTION_TERMINAL.json').exists())

    def test_admission_is_consumed_once(self):
        self.preflight(); admission = self.approve(); self.execute(admission)
        with self.assertRaisesRegex(ValueError, 'BATCH_PREFLIGHT_ROOT_NOT_PRISTINE'):
            self.execute(admission)

    def test_mutated_admission_is_refused_before_any_launch(self):
        self.preflight(); admission = self.approve()
        for key, bad in (('decision', 'PENDING_PARENT_REVIEW'), ('roster_sha256', '0' * 64), ('pairs', []), ('local_use_decision', 'PENDING_LOCAL_EXECUTION_REVIEW_NO_DISTRIBUTION_CLEARANCE')):
            changed = json.loads(admission.read_text()); changed[key] = bad; bad_path = self.work / ('bad_' + key + '.json'); bad_path.write_text(json.dumps(changed))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'BATCH_PARENT_REVIEW_BINDING_MISMATCH'):
                self.execute(bad_path)
        self.assertFalse((self.run_root / 'admissions').exists())

    def test_changed_pair_input_after_preflight_is_refused(self):
        self.preflight(); admission = self.approve()
        faa = self.pair_files['pair_a']['query_fasta']; faa.write_text('>TE_GTG\n' + P_GTG + 'A\n')
        with self.assertRaises(ValueError):
            self.execute(admission)

    def test_roster_rules(self):
        rows = json.loads(self.roster.read_text())['queries']
        for label, change in (('duplicate pair id', lambda r: r[1].update(pair_id='pair_a')),
                              ('duplicate record x bait', lambda r: r[1].update(enzyme_accession='TE_GTG')),
                              ('missing identity', lambda r: r[0].pop('bgc_alias'))):
            changed = json.loads(json.dumps(rows)); change(changed)
            self.roster.write_text(json.dumps({'schema_version': 'ripper-queries/1', 'queries': changed}) + '\n'); self.write_spec()
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.preflight()
            self.assertFalse(self.run_root.exists())

    def test_cli_route_logs_batch_and_holds_without_execution(self):
        shared, paired = self.args()
        argv = ['lifecycle-batch', '--spec', str(self.spec), '--roster', str(self.roster), '--run-root', str(self.run_root), '--adapted-profile', str(self.adapted)]
        for item in shared:
            argv += ['--file', item]
        for item in paired:
            argv += ['--pair-file', item]
        api_value = self.api()  # build before the swap: self.api calls a.binding_api itself
        with mock.patch.object(a, 'binding_api', return_value=api_value), \
                self.assertLogs(a.LOG, level='INFO') as captured:
            code = a.main(argv)
        self.assertEqual(code, 0)
        self.assertIn('RiPPER lifecycle batch HOLD; phase=preflight; pairs=3', ' '.join(captured.output))


if __name__ == '__main__':
    unittest.main()
