"""Behavioral regressions for portable metadata, authority and alignment composition."""
import ast
import re
import importlib.util
from pathlib import Path
import sqlite3
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]

def tool(name):
    spec = importlib.util.spec_from_file_location("composition_" + name, ROOT / "tools" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod

def database(tmp_path, rows):
    path = tmp_path / "metadata.sqlite"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE record(acc_base TEXT, isolation_source TEXT, country TEXT)")
        con.executemany("INSERT INTO record VALUES (?,?,?)", rows)
    return path

@pytest.mark.parametrize("missing", [None, "", "unknown", "not provided", "N/A"])
def test_deposited_missingness_and_accession_namespace(tmp_path, missing):
    m = tool("build_placement_ggtree_inputs")
    sources = m._load_ref_sources(database(tmp_path, [("NR_151944", missing, None)]))
    assert m._reference_source("Example_species_NR_151944_1", sources, True) == ("METADATA_ABSENT", "")
    assert m._reference_source("Example_species_NR_151945_1", sources, True)[0] == "ACCESSION_UNMATCHED"
    assert m._reference_source("Example_species", sources, True)[0] == "ACCESSION_UNBOUND"
    assert m._reference_source("Example_species", sources, False)[0] == "NOT_REQUESTED"


def test_long_source_display_keeps_raw_metadata_and_accession(tmp_path):
    m = tool("build_placement_ggtree_inputs")
    raw = "marine sediment deposited in a collection with a very long location description"
    sources = m._load_ref_sources(database(tmp_path, [("NR_151944", raw, "Example country")]))
    label = m._ref_label("Example_Example_species_NR_151944_1", "Example", sources)
    assert label.startswith("E. species [") and label.endswith(" (NR_151944)")
    assert len(label.split("[")[1].split("]")[0]) <= m.REF_SOURCE_CHARS
    assert "…" in label and sources["NR151944"] == raw + " · Example country"


def test_missing_malformed_conflicting_database_refused(tmp_path):
    m = tool("build_placement_ggtree_inputs")
    with pytest.raises(FileNotFoundError): m._load_ref_sources(tmp_path / "missing.sqlite")
    assert not (tmp_path / "missing.sqlite").exists()
    p = database(tmp_path, [("NR_151944", "soil", ""), ("NR_151944", "water", "")])
    with pytest.raises(ValueError, match="REFERENCE_SOURCE_CONFLICT"): m._load_ref_sources(p)
    with sqlite3.connect(p) as con: con.execute("DROP TABLE record")
    with pytest.raises(sqlite3.OperationalError): m._load_ref_sources(p)


def test_reference_accession_conflict_refused():
    m = tool("build_placement_ggtree_inputs")
    with pytest.raises(ValueError, match="REFERENCE_ACCESSION_CONFLICT"):
        m._ref_label("Example_NR_151944_1_NR_151945_1", "Example")


def test_bundled_registry_inspectable_but_not_implicitly_approved(monkeypatch, tmp_path):
    from mamey import outgroup_registry_path as paths
    monkeypatch.delenv("OUTGROUP_REGISTRY", raising=False)
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(tmp_path))
    for key in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"): monkeypatch.delenv(key, raising=False)
    m = tool("outgroup_registry")
    assert m.load_registry(paths.shipped_registry_path())
    with pytest.raises(paths.RegistryAuthorityError, match="OUTGROUP_AUTHORITY_UNBOUND"):
        m.find_row("Example", path=paths.shipped_registry_path())
    assert Path(tool("phylo_preflight").REGISTRY) == paths.outgroup_registry_path()
    monkeypatch.setenv("OUTGROUP_REGISTRY", str(tmp_path / "missing.tsv"))
    with pytest.raises(FileNotFoundError): paths.outgroup_registry_path()

@pytest.mark.parametrize("reverse", [False, True])
def test_incompatible_locked_rows_never_selected_by_order(tmp_path, reverse):
    from mamey.outgroup_registry_path import RegistryAuthorityError
    m = tool("outgroup_registry")
    rows = ["genus\tExample\tFamily\tOther\tOther species\tNR_151944\tLOCKED\tfixture",
            "genus\tExample\tFamily\tDifferent\tDifferent species\tNR_151945\tLOCKED\tfixture"]
    p = tmp_path / "registry.tsv"; p.write_text("\n".join(reversed(rows) if reverse else rows) + "\n")
    with pytest.raises(RegistryAuthorityError, match="OUTGROUP_REGISTRY_CONFLICT"):
        m.find_row("Example", path=p)

@pytest.mark.parametrize("source,count", [
    ("import mamey.console\ndef f():\n mamey.console.emit('x')", 1),
    ("import _console as c\ndef f(c):\n c.emit('x')", 0),
    ("import thirdparty.console as c\ndef f():\n c.emit('x')", 0),
    ("import _console as c\ndef f():\n c = object()\n c.emit('x')", 0),
])
def test_console_metric_respects_import_scope(source, count):
    assert tool("repo_health")._count_console_attributes(ast.parse(source)) == count

@pytest.mark.parametrize("fragmentary", [False, True])
@pytest.mark.parametrize("failure", [None, "missing_split", "width", "reference", "lost_query"])
def test_fresh_alignment_preserves_reference_and_query_identity(tmp_path, monkeypatch, fragmentary, failure):
    m = tool("phylo_place")
    ref = tmp_path / "reference.fasta"; ref.write_text(">reference\nACGT\n")
    query = tmp_path / "query.fasta"; query.write_text(">query\nAC\n")
    target = tmp_path / "query.aligned.fasta"; target.write_text("stale")
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if args[0] == "mafft":
            kwargs["stdout"].write(">reference\n" + ("TCGT" if failure == "reference" else "ACGT") + "\n" + ("" if failure == "lost_query" else ">query\nAC--\n"))
        elif failure != "missing_split":
            Path(args[-1], "query.fasta").write_text(">query\n" + ("AC" if failure == "width" else "AC--") + "\n")
    monkeypatch.setattr(m.subprocess, "check_call", run)
    if failure:
        with pytest.raises(ValueError, match="ALIGNMENT_"):
            m._align_queries("mafft", "epa", str(ref), str(query), str(tmp_path), fragmentary)
        assert target.read_text() == "stale"
    else:
        assert Path(m._align_queries("mafft", "epa", str(ref), str(query), str(tmp_path), fragmentary)).read_text() == ">query\nAC--\n"
    assert calls[0][1] == ("--addfragments" if fragmentary else "--add")
    assert ref.read_text() == ">reference\nACGT\n"


def test_census_separates_collection_from_execution(tmp_path, monkeypatch):
    m = tool("suite_count_census"); monkeypatch.setattr(m, "ROOT", tmp_path)
    p = tmp_path / "test_fixture.py"
    p.write_text("import pytest\ndef test_pass(): assert True\n@pytest.mark.skip(reason='fixture')\ndef test_skip(): assert False\n")
    result = m.census()
    assert (result["selected"], result["marked_skip"], result["deselected"]) == (2, 1, 0)
    assert result["execution"] is None
    p.write_text("raise RuntimeError('collection failure')")
    with pytest.raises(ValueError, match="CENSUS_COLLECTION_FAILED"): m.census()
    junit = tmp_path / "result.xml"; junit.write_text('<testsuite><testcase/><testcase><skipped/></testcase><testcase><failure/></testcase></testsuite>')
    assert m.read_junit(junit)["testcase_outcomes"] == {"passed": 1, "skipped": 1, "failure": 1}


@pytest.mark.parametrize("isolation,expected", [("", "host: Example host · Example country"), ("soil", "soil · host: Example host · Example country"), ("unknown", "host: Example host · Example country")])
def test_optional_deposited_host_keeps_field_identity(tmp_path, isolation, expected):
    m = tool("build_placement_ggtree_inputs")
    path = tmp_path / "host.sqlite"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE record(acc_base TEXT, isolation_source TEXT, host TEXT, country TEXT)")
        con.execute("INSERT INTO record VALUES (?,?,?,?)", ("NR_151944", isolation, "Example host", "Example country"))
    source = m._load_ref_sources(path)
    assert source["NR151944"] == expected
    assert m._reference_source("Example_NR_151944_1", source, True) == ("DEPOSITED_METADATA", expected)

@pytest.mark.parametrize("tip,genus,label", [
 ("Nocardia_colli_strain_KY2_1__NR_170398_1", "Nocardia", "N. colli KY2 1 (NR_170398.1)"),
 ("GCF_000372745.1_Embleya_scabrispora", "Embleya", "E. scabrispora (GCF_000372745.1)"),
 ("Pseudonocardia_thermophila_ATCC_19285_NR_118886_1", "", "Pseudonocardia thermophila ATCC 19285 (NR_118886.1)"),
])
def test_accession_slot_cannot_be_filled_by_a_strain_code(tip, genus, label):
    m = tool("build_placement_ggtree_inputs")
    assert m._ref_label(tip, genus) == re.sub(r"\.\d+\)$", ")", label)
    assert label.endswith("(" + m._ref_accession(tip) + ")")
