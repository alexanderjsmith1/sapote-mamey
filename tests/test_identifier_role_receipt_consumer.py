"""Consumer schema controls only; no identifiers, registry, source cut or semantic audit."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from identifier_source_roles import validate_role_audit_receipt


class RoleReceiptConsumer(unittest.TestCase):
    def record(self):
        return dict(schema='sapote.source-test-role-audit.v1', state='PASS_SOURCE_ROLE_SCOPE',
                    artifact_export_permission=False,
                    scope='readable tests source sites only; other privacy/archive/source-integrity gates remain required',
                    policy_sha256='1' * 64, test_source_sha256='2' * 64, findings=[],
                    counts=dict(public_reference_sites=0, authored_fixture_sites=0,
                                existing_placeholder_sites=0, declared_unreviewed_sites=0,
                                unlisted_unreviewed_sites=0, binary_outside_source_scope=0))

    def test_matching_canonical_policy_and_snapshot_are_accepted_in_source_scope_only(self):
        record = self.record()
        self.assertEqual(validate_role_audit_receipt(record, '1' * 64), '2' * 64)
        self.assertIs(record['artifact_export_permission'], False)

    def test_matching_malformed_policy_values_are_not_bindings(self):
        for value in [None, 'not-a-digest', 'a' * 63, True, [], {}, 3, 'A' * 64]:
            record = self.record()
            record['policy_sha256'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'role receipt binding'):
                validate_role_audit_receipt(record, value)

    def test_malformed_snapshot_values_are_typed_refusals(self):
        for value in [None, [], ['nonempty'], {}, True, 3, 'a' * 63, 'A' * 64]:
            record = self.record()
            record['test_source_sha256'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'role receipt binding'):
                validate_role_audit_receipt(record, '1' * 64)

    def test_boolean_count_and_export_promotion_are_refused(self):
        for changes in [dict(artifact_export_permission=True), dict(state='HOLD'), dict(findings=[{}])]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_role_audit_receipt(dict(self.record(), **changes), '1' * 64)
        record = self.record()
        record['counts']['declared_unreviewed_sites'] = False
        with self.assertRaises(ValueError):
            validate_role_audit_receipt(record, '1' * 64)


if __name__ == '__main__':
    unittest.main()
