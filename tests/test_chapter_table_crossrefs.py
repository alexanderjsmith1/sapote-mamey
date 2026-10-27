import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("crossrefs", Path(__file__).parents[1] / "tools/chapter_table_crossrefs.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def events(text, doc="main", scope="chapter5"):
    return m.scan_rows(m.visible_md(text), doc, scope)


class CrossrefTests(unittest.TestCase):
    def test_cross_document_supplement_resolves(self):
        main, _ = events("See Table S5.7.")
        supplement, _ = events("**Table S5.7. Attine reference panels.**", "part3")
        r = m.resolve(main + supplement)
        self.assertEqual(r[0]["status"], "RESOLVED")
        self.assertEqual(r[0]["targets"][0]["document_id"], "part3")

    def test_incomplete_corpus_does_not_invent_target(self):
        e, _ = events("Table S5.7 gives the panels.")
        self.assertEqual(m.resolve(e)[0]["status"], "UNRESOLVED_IN_SUPPLIED_SCOPE")

    def test_table_figure_data_namespaces_separate(self):
        e, _ = events("**Figure 5.1.** A plot.\nSee Table 5.1.\nData S5.G holds genes.")
        r = m.resolve(e, {("chapter5", "S5.G"): ["S5.C1"]})
        self.assertEqual([x["kind"] for x in r], ["Table", "Data"])
        self.assertEqual(r[0]["status"], "UNRESOLVED_IN_SUPPLIED_SCOPE")
        self.assertEqual(r[1]["status"], "RESOURCE_BOUND")

    def test_dotted_letter_table_label(self):
        e, h = events("**Table S5.C12.** Genes.\nSee Table S5.C12.")
        self.assertFalse(h)
        self.assertEqual([x["label"] for x in e], ["S5.C12", "S5.C12"])
        self.assertEqual(m.resolve(e)[1]["status"], "RESOLVED")

    def test_numeric_letter_suffix(self):
        e, _ = events("**Table 5.0b.** Older counts.\nTables 5.0 and 5.0b.")
        self.assertEqual([x["label"] for x in e], ["5.0b", "5.0", "5.0b"])

    def test_comments_code_and_link_destinations_not_visible(self):
        e, _ = events("<!-- Table S5.99 -->\n```\nTable S5.98\n```\n`Table S5.97`\n[link](Table S5.96)\nSee Table S5.1.")
        self.assertEqual([x["label"] for x in e], ["S5.1"])
        self.assertEqual(e[0]["location"], "line:7")

    def test_duplicate_definition_hold(self):
        a, _ = events("**Table S5.7.** One.")
        b, _ = events("**Table S5.7.** Two.", "other")
        self.assertEqual({x["status"] for x in m.resolve(a+b)}, {"DUPLICATE_DEFINITION_HOLD"})

    def test_separate_chapter_scopes_do_not_collide(self):
        a, _ = events("**Table S1.** One.", scope="chapter1")
        b, _ = events("See Table S1.", scope="chapter5")
        self.assertEqual(m.resolve(a+b)[1]["status"], "UNSCOPED_LABEL_HOLD")

    def test_caption_not_standalone_table_cell(self):
        e, _ = events("| Earlier label | Table S5.3 |\nTable S5.3\n**Table S5.3.** Defined.")
        self.assertEqual([x["role"] for x in e], ["citation", "citation", "definition"])

    def test_ranges_and_lists(self):
        e, h = events("Tables S5.C1–S5.C3 and S5.C5.")
        self.assertFalse(h)
        self.assertEqual([x["label"] for x in e], ["S5.C1", "S5.C2", "S5.C3", "S5.C5"])
        _, h = events("Tables 5.3–5.1.")
        self.assertEqual(h[0]["code"], "RANGE_PARSE_HOLD")
        e, h = events("Tables S5.C01–S5.C03.")
        self.assertFalse(h)
        self.assertEqual([x["label"] for x in e], ["S5.C01", "S5.C02", "S5.C03"])
        _, h = events("Tables S5.C01–S5.C3.")
        self.assertEqual(h[0]["code"], "RANGE_PARSE_HOLD")

    def test_sheet_context_and_names(self):
        e, _ = events("Data S5.G, sheet S5.C1.\nData S5.G, sheet S5.C2.\nSheet S5.C1.")
        r = m.resolve(e, {("chapter5", "S5.G"): ["Index", "S5.C1"]})
        self.assertEqual([x["status"] for x in r if x["kind"] == "Sheet"], ["SHEET_NAME_BOUND", "SHEET_NOT_FOUND_HOLD", "SHEET_RESOURCE_SCOPE_HOLD"])

    def test_nonrecognized_data_label_never_resolves_as_table(self):
        e, h = events("Table S5.G should not be parsed as Table S5. Data S5.G is separate.")
        self.assertEqual(h[0]["code"], "TABLE_LABEL_PARSE_HOLD")
        self.assertEqual([x["label"] for x in e if x["kind"] == "Table"], ["S5"])
        self.assertEqual(m.resolve(e)[0]["status"], "UNSCOPED_LABEL_HOLD")


if __name__ == "__main__": unittest.main()
