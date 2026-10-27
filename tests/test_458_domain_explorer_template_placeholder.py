"""The domain explorer refuses a --template without exactly one __DATA__ placeholder.

A template with none wrote an index.html carrying no data and reported success.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_domain_explorer_fixture_458t", ROOT / "tests" / "test_domain_explorer.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


class TemplatePlaceholder(_fx.ProjectionFixture):
    def test_missing_placeholder_is_refused(self):
        self.template.write_text('<script>const D={}</script>')
        with self.assertRaisesRegex(ValueError, 'TEMPLATE_PLACEHOLDER_HOLD'):
            self.run_build()
        self.assertFalse((self.p / 'out' / 'index.html').exists())

    def test_doubled_placeholder_is_refused(self):
        self.template.write_text('<script>const D=__DATA__;const E=__DATA__</script>')
        with self.assertRaisesRegex(ValueError, 'TEMPLATE_PLACEHOLDER_HOLD'):
            self.run_build()
