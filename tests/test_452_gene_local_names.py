"""Local gene names for the grey genes of a gap-rescue locus map (card 452_gene_local_names).

The step that named region genes by DIAMOND against Swiss-Prot and MIBiG was a loose script with fixed paths, keyed by
locus tag only. It is now tools/gene_local_names.py: inputs on the command line, a protein_sha256 on every row so the map
binds names by sequence, and genes already named by another table bound by protein before they are skipped. DIAMOND is
replaced here by a stub that writes fixed hits.
"""
import csv
import importlib.util
import io
import sys
import textwrap
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from mamey.protein_binding import protein_sha256  # noqa: E402

LABEL = "SYN-0001"
PROTS = {"syn_1": "MSTNPKPQRKTKRNTNRRPQDVKFPGG", "syn_2": "MAELLKRAGVDVTTLAEHLGLSRRA",
         "syn_3": "MKKLLPTAAAGLLLLAAQPAMA", "syn_4": "MTQRLAVIGAGPAGLSAAWHLARAGH"}


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gln = _load("gene_local_names", "tools/gene_local_names.py")


def _gbk(prots):
    feats, pos = [], 1
    for tag, aa in prots.items():
        end = pos + 3 * len(aa) + 2
        feats.append(f"     CDS             {pos}..{end}\n"
                     f"                     /locus_tag=\"{tag}\"\n"
                     f"                     /translation=\"{aa}\"\n")
        pos = end + 10
    seq = "a" * (pos + 10)
    lines = [f"LOCUS       {'SYN_CONTIG_1':<16} {len(seq):>11} bp    DNA     linear   UNK 01-JAN-2000",
             "DEFINITION  synthetic region.", "ACCESSION   SYN_CONTIG_1", "VERSION     SYN_CONTIG_1",
             "KEYWORDS    .", "SOURCE      synthetic", "  ORGANISM  synthetic", "            .",
             "FEATURES             Location/Qualifiers", f"     source          1..{len(seq)}"]
    body = "\n".join(lines) + "\n" + "".join(feats) + "ORIGIN\n"
    for i in range(0, len(seq), 60):
        chunk = seq[i:i + 60]
        body += f"{i + 1:>9} " + " ".join(chunk[j:j + 10] for j in range(0, len(chunk), 10)) + "\n"
    return body + "//\n"


def _stub(tmp, log):
    """A DIAMOND stand-in: writes fixed hits for the database named by -d and logs each call."""
    sp = (f"{LABEL}|syn_1\tP00001.1\t60.0\t200\tP00001.1 RecName: Full=Polyketide synthase PksA; AltName: x [SYN org]\n"
          f"{LABEL}|syn_1\tP00002.1\t50.0\t150\tP00002.1 RecName: Full=Polyketide synthase PksA [SYN org 2]\n"
          f"{LABEL}|syn_1\tP00003.1\t40.0\t120\tP00003.1 RecName: Full=Thioesterase TesB [SYN org 3]\n"
          f"{LABEL}|syn_2\tP00004.1\t30.0\t50\tP00004.1 RecName: Full=Uncharacterized protein Y [SYN org]\n")
    mb = (f"{LABEL}|syn_1\tBGC9000001|1\t45.0\t110\tBGC9000001|1\n"
          f"{LABEL}|syn_2\tBGC9000001|2\t70.0\t90\tBGC9000001|2\n"
          f"{LABEL}|syn_2\tBGC9000002|1\t66.0\t80\tBGC9000002|1\n"
          f"{LABEL}|syn_2\tBGC9000002|2\t62.0\t70\tBGC9000002|2\n")
    path = tmp / "diamond_stub.py"
    path.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import sys
        a = sys.argv
        db, out = a[a.index("-d") + 1], a[a.index("-o") + 1]
        open({str(log)!r}, "a").write(db + "\\n")
        open(out, "w").write({mb!r} if "mibig" in db else {sp!r})
        """))
    path.chmod(0o755)
    return path


def _setup(tmp):
    region = _gbk(PROTS)
    z = tmp / "SYN-0001.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("SYN_CONTIG_1.region001.gbk", region)
    sp = tmp / "sp.dmnd"
    sp.write_text("x")
    mib = tmp / "mibig"
    mib.mkdir()
    (mib / "mibig_proteins.dmnd").write_text("x")
    (mib / "mibig_proteins.tsv").write_text("id\taccession\tname\tproduct\n"
                                            "BGC9000001|1\tBGC9000001\tsynA\tpolyketide synthase\n"
                                            "BGC9000001|2\tBGC9000001\tctg3_2\t\n"
                                            "BGC9000002|1\tBGC9000002\tregR\tTetR family transcriptional regulator\n"
                                            "BGC9000002|2\tBGC9000002\tregS\tTetR family transcriptional regulator\n")
    # syn_4 is named already, under another run's tag: it must be skipped by its protein, not its tag
    named = tmp / "named.tsv"
    named.write_text("strain\tgene\taa_length\tprotein_sha256\ttop10_consensus_name\tdb\n"
                     f"{LABEL}\tctg9_9\t{len(PROTS['syn_4'])}\t{protein_sha256(PROTS['syn_4'])}\tFAD-binding protein\tnr\n")
    log = tmp / "calls.log"
    return z, sp, mib, named, log, _stub(tmp, log)


def _run(tmp, z, sp, mib, named, stub, out):
    return gln.main(["--input", f"{LABEL}={z}", "--swissprot", str(sp), "--mibig-proteins", str(mib),
                     "--out", str(out), "--skip-named", str(named), "--diamond", str(stub), "--threads", "1"])


def _rows(out):
    with open(out / "GENE_LOCAL_NAMES.tsv", newline="") as fh:
        return {r["gene"]: r for r in csv.DictReader(fh, delimiter="\t")}


def test_names_by_better_database_with_checksums(tmp_path):
    z, sp, mib, named, log, stub = _setup(tmp_path)
    out = tmp_path / "out"
    assert _run(tmp_path, z, sp, mib, named, stub, out) == 0
    rows = _rows(out)
    assert set(rows) == {"syn_1", "syn_2"}            # syn_3 has no hit; syn_4 was named already
    r1, r2 = rows["syn_1"], rows["syn_2"]
    assert r1["db"] == "Swiss-Prot" and r1["top10_consensus_name"] == "Polyketide synthase PksA"
    assert r1["consensus_share"] == "2 of 3" and r1["top10_mean_identity"] == "50.0"
    assert r1["function_class"] == "biosynthetic core" and r1["top_hit_organism"] == "SYN org"
    assert r2["db"] == "MIBiG" and r2["top10_consensus_name"] == "TetR family transcriptional regulator"
    assert r2["consensus_share"] == "2 of 3" and r2["function_class"] == "regulator"
    assert r2["top_hit_def"] == "BGC9000001|2"        # no product text: the id, never the gene name "ctg3_2"
    for tag, r in rows.items():
        assert r["protein_sha256"] == protein_sha256(PROTS[tag]) and r["aa_length"] == str(len(PROTS[tag]))
        assert r["bgc_id"] == "SYN_CONTIG_1.region001" and r["strain"] == LABEL
    counts = (out / "GENE_LOCAL_NAMES_COUNTS.md").read_text()
    assert f"| {LABEL} | 4 | 1 | 3 | 2 | 1 |" in counts
    assert "syn_4" not in (out / "QUERIES.faa").read_text()


def test_finished_search_is_reused(tmp_path):
    z, sp, mib, named, log, stub = _setup(tmp_path)
    out = tmp_path / "out"
    _run(tmp_path, z, sp, mib, named, stub, out)
    _run(tmp_path, z, sp, mib, named, stub, out)
    assert len(log.read_text().splitlines()) == 2     # one call per database, the second run reads the finished files


def test_rows_bind_on_the_locus_map_by_sequence(tmp_path):
    z, sp, mib, named, log, stub = _setup(tmp_path)
    out = tmp_path / "out"
    _run(tmp_path, z, sp, mib, named, stub, out)
    glm = _load("gap_rescue_locus_map", "tools/gap_rescue_locus_map.py")
    # the map's genome came from another antiSMASH run: same proteins, other tags
    prots = {"p1": {"tag": "ctg1_7", "aa": PROTS["syn_1"]}, "p2": {"tag": "ctg1_8", "aa": PROTS["syn_2"]}}
    names = glm.load_gene_names([out / "GENE_LOCAL_NAMES.tsv"], LABEL, prots)
    assert names["ctg1_7"]["top10_consensus_name"] == "Polyketide synthase PksA"
    assert names["ctg1_8"]["db"] == "MIBiG"


def test_swissprot_titles_ncbi_and_uniprot():
    assert gln.swissprot_title("P1.1 RecName: Full=Chalcone synthase; AltName: Full=X [SYN org]") == \
        ("Chalcone synthase", "SYN org")
    assert gln.swissprot_title("sp|P1|CHS_SYN Chalcone synthase OS=SYN org OX=1 GN=chs PE=1 SV=1") == \
        ("Chalcone synthase", "SYN org")


def test_missing_tools_refused(tmp_path, capsys):
    z, sp, mib, named, log, stub = _setup(tmp_path)
    rc = gln.main(["--input", f"{LABEL}={z}", "--swissprot", str(tmp_path / "none.dmnd"), "--mibig-proteins", str(mib),
                   "--out", str(tmp_path / "out"), "--diamond", str(stub)])
    assert rc == 2 and "not run: no Swiss-Prot database" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
