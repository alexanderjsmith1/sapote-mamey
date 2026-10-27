"""Card 452_local_16s_database_guide_and_resolver.

The 16S RefSeq BLAST database had one line of setup text and was found six different ways by seven tools.
These tests hold the fix: one guide (docs/LOCAL_16S_DATABASE.md) linked from the places a reader looks, one
resolver (`_phylo16s.refseq_16s_blastdb`) with a documented order, every consumer routed through it, and a
receipt from the similarity check naming the database it used. Hermetic: fake BLAST programs, temp roots.
"""
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
GUIDE = ROOT / "docs" / "LOCAL_16S_DATABASE.md"
CONSUMERS = ("sixteen_s_similarity_check", "comparator_select", "harvest_16s", "phylo_refset",
             "outgroup_registry", "phylo_autopilot", "phylo_16s_from_genome")
OLD_LITERALS = ('"blast_dbs" / "16S_ribosomal_RNA"', "Tools/databases/ncbi_16S_RefSeq/16S_ribosomal_RNA")


def _load(name, alias=None):
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(alias or name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias or name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    for var in ("SAPOTE_16S_DB", "NCBI_16S_DB", "SAPOTE_ROOT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    return tmp_path


def _volumes(prefix: Path):
    prefix.parent.mkdir(parents=True, exist_ok=True)
    Path(str(prefix) + ".nin").write_text("")


# ---------------------------------------------------------------- the guide
def test_guide_exists_and_is_linked_from_the_reader_entry_points():
    assert GUIDE.is_file()
    for doc in ("docs/EXTERNAL_ASSETS_GUIDE.md", "docs/PHYLOGENETICS_WORKFLOW.md",
                "docs/NEIGHBOUR_PANEL_16S_TYGS.md", "CURRENT_DOCS_INDEX.md"):
        assert "LOCAL_16S_DATABASE.md" in (ROOT / doc).read_text(), doc


def test_guide_covers_full_and_partial_builds_and_the_store():
    text = GUIDE.read_text()
    for needle in ("## Full build", "## Partial build", "## The 16S SQLite store", "## Which tools use what",
                   "update_blastdb.pl --decompress 16S_ribosomal_RNA", "33175[BioProject]", "makeblastdb",
                   "blastdbcmd -db", "-info", "SAPOTE_16S_DB", "SAPOTE_16S_SQLITE"):
        assert needle in text, needle


def test_every_tool_named_in_the_guide_exists():
    names = set(re.findall(r"tools/([A-Za-z0-9_]+\.py)", GUIDE.read_text()))
    names |= {n + ".py" for n in re.findall(r"`(phylo_16s_[a-z_]+)\.py`", GUIDE.read_text())}
    assert names
    missing = sorted(n for n in names if not (TOOLS / n).is_file())
    assert not missing, missing


def test_flags_named_in_the_guide_exist_in_their_tools(tmp_path):
    """Every --flag the guide gives a tool appears in that tool's own --help (the parser may live elsewhere)."""
    text = GUIDE.read_text()
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(tmp_path))
    checked = 0
    for tool in ("phylo_16s_build_db", "phylo_16s_validate_db", "harvest_16s", "sixteen_s_similarity_check"):
        flags = set()
        for block in re.findall(rf"tools/{tool}\.py((?:[^\n`]*\\\n)*[^\n`]*)", text):
            flags |= set(re.findall(r"(--[a-z][a-z-]+)", block))
        if not flags:
            continue
        helptext = subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), "--help"], cwd=str(ROOT), env=env,
                                  capture_output=True, text=True, timeout=120).stdout
        for flag in flags:
            assert flag in helptext, (tool, flag)
            checked += 1
    assert checked >= 8


# ---------------------------------------------------------------- the resolver
def test_resolver_order_explicit_then_env(clean_env, monkeypatch):
    p16 = _load("_phylo16s", "_phylo16s_t452")
    assert p16.refseq_16s_blastdb("/x/explicit") == "/x/explicit"
    monkeypatch.setenv("NCBI_16S_DB", "/x/ncbi")
    assert p16.refseq_16s_blastdb() == "/x/ncbi"
    monkeypatch.setenv("SAPOTE_16S_DB", "/x/sapote")
    assert p16.refseq_16s_blastdb() == "/x/sapote"


def test_resolver_reads_the_registry_row_then_the_two_defaults(clean_env):
    root = clean_env
    p16 = _load("_phylo16s", "_phylo16s_t452b")
    _volumes(root / "blast_dbs" / "16S_ribosomal_RNA")
    assert p16.refseq_16s_blastdb() == str(root / "blast_dbs" / "16S_ribosomal_RNA")
    _volumes(root / "Tools/databases/ncbi_16S_RefSeq" / "16S_ribosomal_RNA")
    assert p16.refseq_16s_blastdb() == str(root / "Tools/databases/ncbi_16S_RefSeq" / "16S_ribosomal_RNA")
    (root / "OFFICIAL_DATA").mkdir()
    (root / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").write_text(
        "# registry\nncbi_16s_blastdb\tdatabase\tchosen_db\t70M\t16S\tthe one copy\n")
    _volumes(root / "chosen_db" / "16S_ribosomal_RNA")
    assert p16.refseq_16s_blastdb() == str(root / "chosen_db" / "16S_ribosomal_RNA")


def test_registry_row_without_volumes_is_not_trusted(clean_env):
    root = clean_env
    p16 = _load("_phylo16s", "_phylo16s_t452c")
    (root / "OFFICIAL_DATA").mkdir()
    (root / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").write_text("ncbi_16s_blastdb\tdatabase\tempty_dir\t0\t16S\t\n")
    (root / "empty_dir").mkdir()
    _volumes(root / "blast_dbs" / "16S_ribosomal_RNA")
    assert p16.refseq_16s_blastdb() == str(root / "blast_dbs" / "16S_ribosomal_RNA")


# ---------------------------------------------------------------- the consumers
@pytest.mark.parametrize("tool", CONSUMERS)
def test_consumers_use_the_shared_resolver_and_no_private_default(tool):
    src = (TOOLS / f"{tool}.py").read_text()
    assert "refseq_16s_blastdb" in src, tool
    for lit in OLD_LITERALS:
        assert lit not in src, (tool, lit)


@pytest.mark.parametrize("tool", ("comparator_select", "harvest_16s", "phylo_refset", "outgroup_registry"))
def test_consumer_lookup_follows_one_setting(tool, clean_env, monkeypatch):
    monkeypatch.setenv("SAPOTE_16S_DB", "/x/one_setting")
    mod = _load(tool, f"{tool}_t452")
    assert mod._shared_16s_db(None) == "/x/one_setting"
    assert mod._shared_16s_db("/x/own_arg") == "/x/own_arg"


def test_autopilot_route_and_run16s_no_longer_require_db():
    src = (TOOLS / "phylo_autopilot.py").read_text()
    assert 'add_argument("--db", required=True' not in src
    assert src.count("a.db = _p16.refseq_16s_blastdb(a.db)") == 2


# ---------------------------------------------------------------- the receipt
def _fake_bin(d: Path):
    d.mkdir()
    (d / "blastdbcmd").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  *-info*) printf "Database: fake 16S type strains\\n\\t1 sequences; 1400 total bases\\nDate: Oct 1, 2026\\n";;\n'
        '  *"-entry all"*) printf "NR_000001.1\\tStreptomyces griseus strain T1 16S ribosomal RNA\\n";;\n'
        '  *) out=""; prev=""; for a in "$@"; do [ "$prev" = "-out" ] && out="$a"; prev="$a"; done;\n'
        '     printf ">NR_000001.1\\nACGT\\n" > "$out";;\n'
        "esac\n")
    (d / "blastn").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        '  *-subject*) printf "99.50\\t1400\\t2500\\n";;\n'
        '  *) printf "99.20\\t1400\\t1450\\t2400\\tStreptomyces griseus strain T1 16S\\n";;\n'
        "esac\n")
    for f in d.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IEXEC)


def test_similarity_check_writes_a_receipt_naming_the_database(clean_env, monkeypatch):
    tmp = clean_env
    _fake_bin(tmp / "bin")
    (tmp / "q.fa").write_text(">STR-1 isolate\n" + "ACGT" * 350 + "\n")
    (tmp / "t.tsv").write_text("strain\tgenus_16s\tclosest_type_strain\tsimilarity_percent\n"
                               "STR-1\tStreptomyces sp.\tS. griseus\t99.5\n")
    monkeypatch.setenv("SAPOTE_16S_DB", str(tmp / "db" / "16S_ribosomal_RNA"))
    mod = _load("sixteen_s_similarity_check", "sixteen_s_t452")
    out = tmp / "check.tsv"
    assert mod.main(["--fasta", str(tmp / "q.fa"), "--table", str(tmp / "t.tsv"),
                     "--blast-bin", str(tmp / "bin"), "--out", str(out)]) == 0
    rec = json.loads(Path(str(out) + ".receipt.json").read_text())
    assert rec["blastdb_prefix"] == str(tmp / "db" / "16S_ribosomal_RNA")
    assert rec["blastdbcmd_info_exit"] == 0
    assert any("fake 16S type strains" in ln for ln in rec["blastdbcmd_info"])
    assert rec["strains_checked"] == 1 and len(rec["fasta_sha256"]) == 64
    assert "99.50" in out.read_text()
