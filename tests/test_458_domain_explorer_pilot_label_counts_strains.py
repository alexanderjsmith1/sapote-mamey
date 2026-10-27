"""The domain explorer's pilot label states how many strains the pilot holds.

It always said "five-strain pilot subset", even when fewer strains were available.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_domain_explorer_fixture_458", ROOT / "tests" / "test_domain_explorer.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


class PilotLabel(_fx.ProjectionFixture):
    def test_label_counts_the_strains_present(self):
        d = _fx.build(self.db, self.reader, self.p / 'out', self.template, pilot=True,
                      population='fixture only', expected_census='fixture-population')
        self.assertEqual(d['counts']['strains'], 1)
        self.assertEqual(d['population'], 'fixture only / 1-strain pilot subset')
