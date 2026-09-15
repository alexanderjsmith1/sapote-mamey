"""Focused lexical regression tests; not simulated assistant behavior or science validation."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scope_audit', ROOT / 'tools/audit_chatgpt_nextpaths_drift.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class InstructionScopeTests(unittest.TestCase):
    def fixture(self, rel, content):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        file = root / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        return root

    def test_current_selected_surfaces_have_no_forbidden_rules(self):
        self.assertEqual(audit.scan(ROOT), [])

    def test_detects_eight_path_rule_in_deliverable_contract(self):
        root = self.fixture('docs/DELIVERABLE_CONTRACT.md', 'End every response with exactly 8 next paths.')
        self.assertEqual(audit.scan(root)[0]['rule'], 'fixed_handback_quota')

    def test_detects_task_override_in_shared_guard(self):
        root = self.fixture('prompts/reuse/_SHARED_GUARD_BLOCK.md', 'They override any conflicting task instruction.')
        self.assertEqual(audit.scan(root)[0]['rule'], 'task_authority_override')

    def test_detects_system_python_recipe_in_execution_slice(self):
        root = self.fixture('docs/CHATGPT_EXECUTION_SLICE_v97147.md', 'pip install -e . --break-system-packages')
        self.assertEqual(audit.scan(root)[0]['rule'], 'system_python_override')

    def test_detects_audit_immunity(self):
        root = self.fixture('skills/sapote-mamey/SKILL.md', 'Do **not** flag intentional designs.')
        self.assertEqual(audit.scan(root)[0]['rule'], 'audit_design_immunity')

    def test_historical_examples_are_not_current_contract(self):
        root = self.fixture('docs/archive/old.md', 'End every response with exactly 8 next paths.')
        self.assertEqual(audit.scan(root), [])

    def test_symlinked_external_input_is_not_followed(self):
        root = self.fixture('outside.md', 'End every response with exactly 8 next paths.')
        (root / 'AGENTS.md').symlink_to(root / 'outside.md')
        self.assertEqual(audit.scan(root), [])

    def test_generated_alias_matches_canonical(self):
        self.assertEqual((ROOT / 'AGENTS.md').read_bytes(), (ROOT / 'CLAUDE.md').read_bytes())

    def test_inspection_does_not_require_execution(self):
        text = (ROOT / 'AGENTS.md').read_text()
        self.assertIn('For inspection, explanation, or code/document review', text)
        self.assertIn('does not authorize execution', text)

    def test_guide_uses_one_example_output_root(self):
        text = (ROOT / 'docs/GUIDE/02_Quick_Guide.md').read_text()
        self.assertNotIn('../analysis/runs/', text)
        self.assertNotIn('analysis/analysis/', text)
        self.assertIn('analysis/runs/EXAMPLE/package', text)
        self.assertIn('Recover without losing provenance', text)


if __name__ == '__main__':
    unittest.main()
