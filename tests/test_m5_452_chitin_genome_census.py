"""Tests for tools/chitin_genome_census.py (card M5_452_chitin_genome_census).

Synthetic genomes only (SYN-01..). hmmsearch is replaced by a small stand-in script that writes a
real-format --tblout from a hit map, so the extraction, counting, totals and refusal paths are
tested without HMMER installed. The family logic is what carries the claims: which families count
as chitinolytic, a protein with two families counting in both, and refuse-rather-than-zero.
"""
import csv, importlib.util, json, os, stat, sys, textwrap, zipfile
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "tools", "chitin_genome_census.py")
spec = importlib.util.spec_from_file_location("chitin_genome_census", SRC)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def _gbk(cds, locus="SYN_CONTIG_1", length=3000):
    """Minimal GenBank text; cds = [(locus_tag or None, translation or None), ...]."""
    out = [f"LOCUS       {locus}    {length} bp    DNA     linear   UNK 01-JAN-2000\n",
           "FEATURES             Location/Qualifiers\n",
           "     source          1..%d\n" % length]
    for i, (lt, tr) in enumerate(cds):
        out.append(f"     CDS             {i*300+1}..{i*300+90}\n")
        if lt:
            out.append(f'                     /locus_tag="{lt}"\n')
        if tr:
            first, rest = tr[:40], tr[40:]
            if rest:
                out.append(f'                     /translation="{first}\n')
                out.append(f'                     {rest}"\n')
            else:
                out.append(f'                     /translation="{first}"\n')
    out.append("ORIGIN\n        1 acgt\n//\n")
    return "".join(out)


def _zip(path, genome_gbk, extra=None):
    with zipfile.ZipFile(path, "w") as zf:
        if genome_gbk is not None:
            zf.writestr("SYN_genome.gbk", genome_gbk)
        zf.writestr("SYN_CONTIG_1.region001.gbk", genome_gbk or _gbk([("SYN_r1", "MKV")]))
        zf.writestr("input/SYN_input.gbk", _gbk([("SYN_in", "MKV" * 500)]))
        for n, t in (extra or {}).items():
            zf.writestr(n, t)
    return str(path)


def _hmm(path, fams=None, drop_ga=()):
    fams = fams if fams is not None else m.ALL_FAMS
    with open(path, "w") as fh:
        for f in fams:
            fh.write(f"HMMER3/f [3.4 | SYN]\nNAME  {f}\nACC   {m.PFAM_ACC.get(f, 'PF99999')}.1\n")
            if f not in drop_ga:
                fh.write("GA    20.0 20.0;\n")
            fh.write("//\n")
    return str(path)


@pytest.fixture
def fake_hmmsearch(tmp_path):
    """Stand-in hmmsearch: tblout rows from SYN_HITS = {locus_tag: [family, ...]}."""
    hits = tmp_path / "hits.json"
    exe = tmp_path / "hmmsearch"
    exe.write_text(textwrap.dedent(f"""\
        #!{sys.executable}
        import json, sys
        a = sys.argv[1:]
        if a == ["-h"]:
            print("# hmmsearch :: search profile(s) against a sequence database\\n# HMMER 3.4 (Aug 2023)"); sys.exit(0)
        assert "--cut_ga" in a, "census must use --cut_ga"
        tbl = a[a.index("--tblout") + 1]; faa = a[-1]
        want = json.load(open({str(hits)!r}))
        ids = [l[1:].strip() for l in open(faa) if l.startswith(">")]
        with open(tbl, "w") as out:
            out.write("# target name accession query name accession E-value\\n")
            for pid in ids:
                lt = pid.rsplit("_", 1)[0]
                for fam in want.get(lt, []):
                    out.write(f"{{pid}} - {{fam}} PF0 1e-30 99.0 0.0 1e-30 99.0 0.0 1.0 1 0 0 1 1 1 1 -\\n")
        """))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    def set_hits(d):
        hits.write_text(json.dumps(d))
    set_hits({})
    return str(exe), set_hits


def _run(args):
    return m.main([str(x) for x in args])


def _read(out):
    with open(out) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_whole_genome_member_skips_region_and_input_files(tmp_path):
    zp = _zip(tmp_path / "SYN-01.zip", _gbk([("SYN_a", "M" * 50)]))
    with zipfile.ZipFile(zp) as zf:
        assert m.full_genome_gbk_member(zf) == "SYN_genome.gbk"


def test_parse_gbk_multiline_translation_stop_and_missing_translation():
    text = _gbk([("SYN_a", "MKVL" * 15 + "*"), ("SYN_b", None), (None, "MSTQ")])
    lengths, prots = m.parse_gbk(text.splitlines(keepends=True))
    assert lengths == [3000]
    assert prots == [("SYN_a", "MKVL" * 15), ("cds_2", "MSTQ")]


def test_counts_two_family_protein_in_both_and_total_is_degradative_only(tmp_path, fake_hmmsearch):
    exe, set_hits = fake_hmmsearch
    set_hits({"SYN_a": ["Glyco_hydro_18", "ChitinaseA_N"], "SYN_b": ["Glyco_hydro_19"],
              "SYN_c": ["Glyco_hydro_16"], "SYN_d": ["Glyco_hydro_3"], "SYN_e": ["Glucosamine_iso"],
              "SYN_f": ["LPMO_10", "CBM_5_12"]})
    zp = _zip(tmp_path / "SYN-01.zip", _gbk([(f"SYN_{c}", "M" * 60) for c in "abcdefg"]))
    out = tmp_path / "census.tsv"
    assert _run(["--hmm", _hmm(tmp_path / "c.hmm"), "--input", f"SYN-01={zp}", "--out", out,
                 "--hmmsearch", exe]) == 0
    r = _read(out)[0]
    assert r["Glyco_hydro_18"] == "1" and r["ChitinaseA_N"] == "1" and r["Glyco_hydro_19"] == "1"
    assert r["LPMO_10"] == "1" and r["CBM_5_12"] == "1"
    assert r["Glyco_hydro_16"] == "1" and r["Glyco_hydro_3"] == "1" and r["Glucosamine_iso"] == "1"
    assert r["chitinolytic_domains_total"] == "5"      # GH16, GH3, NagB not counted
    assert r["cds_searched"] == "7" and r["error"] == ""
    assert r["Glyco_hydro_18_loci"] == "SYN_a"
    rec = json.load(open(str(out) + ".json"))
    assert rec["hmmer_version"] == "3.4" and rec["n_errors"] == 0
    assert set(rec["hmm_accessions"]) == set(m.ALL_FAMS)


def test_genome_without_hits_counts_zero_not_error(tmp_path, fake_hmmsearch):
    exe, _ = fake_hmmsearch
    zp = _zip(tmp_path / "SYN-02.zip", _gbk([("SYN_a", "M" * 60)]))
    out = tmp_path / "census.tsv"
    assert _run(["--hmm", _hmm(tmp_path / "c.hmm"), "--input", f"SYN-02={zp}", "--out", out,
                 "--hmmsearch", exe]) == 0
    r = _read(out)[0]
    assert r["chitinolytic_domains_total"] == "0" and r["error"] == ""


def test_zip_without_whole_genome_gbk_is_an_error_row_with_empty_counts(tmp_path, fake_hmmsearch):
    exe, _ = fake_hmmsearch
    zp = _zip(tmp_path / "SYN-03.zip", None)
    out = tmp_path / "census.tsv"
    assert _run(["--hmm", _hmm(tmp_path / "c.hmm"), "--input", f"SYN-03={zp}", "--out", out,
                 "--hmmsearch", exe]) == 2
    r = _read(out)[0]
    assert "no whole-genome GenBank" in r["error"]
    assert r["chitinolytic_domains_total"] == "" and r["Glyco_hydro_18"] == ""   # never 0


def test_genbank_file_input_and_manifest_passthrough(tmp_path, fake_hmmsearch):
    exe, set_hits = fake_hmmsearch
    set_hits({"SYN_x": ["Glyco_hydro_20"]})
    gb = tmp_path / "SYN-04.gbk"; gb.write_text(_gbk([("SYN_x", "M" * 60)]))
    man = tmp_path / "genomes.tsv"
    man.write_text(f"strain_id\tpath\tgenus\tisolation_source\nSYN-04\t{gb}\tSyngenus\tPlace A\n")
    out = tmp_path / "census.tsv"
    assert _run(["--hmm", _hmm(tmp_path / "c.hmm"), "--manifest", man, "--out", out,
                 "--hmmsearch", exe]) == 0
    r = _read(out)[0]
    assert r["genus"] == "Syngenus" and r["isolation_source"] == "Place A"
    assert r["Glyco_hydro_20"] == "1" and r["genbank_member"] == "SYN-04.gbk"


@pytest.mark.parametrize("fams,drop_ga,msg", [
    (m.ALL_FAMS[:-1], (), "missing"),
    (m.ALL_FAMS + ["LysM"], (), "extra"),
    (m.ALL_FAMS, ("Glyco_hydro_18",), "GA line"),
])
def test_hmm_without_exactly_the_11_families_is_refused(tmp_path, fake_hmmsearch, fams, drop_ga, msg, capsys):
    exe, _ = fake_hmmsearch
    zp = _zip(tmp_path / "SYN-05.zip", _gbk([("SYN_a", "M" * 60)]))
    out = tmp_path / "census.tsv"
    assert _run(["--hmm", _hmm(tmp_path / "c.hmm", fams, drop_ga), "--input", f"SYN-05={zp}",
                 "--out", out, "--hmmsearch", exe]) == 2
    assert msg in capsys.readouterr().err
    assert not out.exists()


def test_duplicate_strain_ids_are_refused(tmp_path, fake_hmmsearch, capsys):
    exe, _ = fake_hmmsearch
    zp = _zip(tmp_path / "SYN-06.zip", _gbk([("SYN_a", "M" * 60)]))
    assert _run(["--hmm", _hmm(tmp_path / "c.hmm"), "--input", f"SYN-06={zp}", "--input", f"SYN-06={zp}",
                 "--out", tmp_path / "o.tsv", "--hmmsearch", exe]) == 2
    assert "duplicate strain_id" in capsys.readouterr().err


def test_missing_hmmsearch_is_refused(tmp_path, capsys):
    zp = _zip(tmp_path / "SYN-07.zip", _gbk([("SYN_a", "M" * 60)]))
    assert _run(["--hmm", _hmm(tmp_path / "c.hmm"), "--input", f"SYN-07={zp}",
                 "--out", tmp_path / "o.tsv", "--hmmsearch", tmp_path / "no_such_hmmsearch"]) == 2
    assert "hmmsearch not found" in capsys.readouterr().err
