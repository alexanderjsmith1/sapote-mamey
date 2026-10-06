"""v9.7.448: tools/neighbour_panel_candidates.py builds an isolate's panel from 16S genome hits, the NCBI
genome table and TYGS, offline, with every unresolved item reported rather than substituted."""
import csv
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("neighbour_panel_candidates", ROOT / "tools" / "neighbour_panel_candidates.py")
npc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(npc)


def _asm(acc, org, strain="", typ="", paired="", level="Complete Genome"):
    return {"accession": acc, "paired_accession": paired,
            "organism": {"organism_name": org, "infraspecific_names": {"strain": strain}},
            "type_material": {"type_display_text": typ} if typ else {},
            "assembly_info": {"assembly_level": level, "assembly_status": "current"}}


def _fixture(tmp):
    asms = [_asm("GCF_000001.1", "Streptomyces alpha", "X1", paired="GCA_000001.1"),
            _asm("GCA_000001.1", "Streptomyces alpha", "X1", paired="GCF_000001.1"),
            _asm("GCF_000002.1", "Streptomyces beta", "Y2"),
            _asm("GCF_000099.1", "Streptomyces self", "AS-1")]
    types = [_asm("GCF_000010.1", "Streptomyces gamma", "DSM 100", "assembly from type material", level="Scaffold"),
             _asm("GCF_000011.1", "Streptomyces gamma", "NRRL B-9", "assembly from type material", level="Contig")]
    seqs = [{"assembly_accession": "GCF_000001.1", "genbank_accession": "CP000001.1", "refseq_accession": "NZ_CP000001.1"},
            {"assembly_accession": "GCA_000001.1", "genbank_accession": "CP000001.1"},
            {"assembly_accession": "GCF_000002.1", "genbank_accession": "CP000002.1"},
            {"assembly_accession": "GCF_000099.1", "genbank_accession": "CP000099.1"}]
    for name, rows in (("a.jsonl", asms), ("t.jsonl", types), ("s.jsonl", seqs)):
        (tmp / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    blast = ["#status block line", "<p>",
             "Query_1\tCP000002.1\t98.00\t1400\t0\t0\t1\t1400\t1\t1400\t0.0\t2500",
             "Query_1\tCP000001.1\t99.50\t1450\t0\t0\t1\t1450\t1\t1450\t0.0\t2600",
             "Query_1\tCP000001.1\t99.00\t1450\t0\t0\t1\t1450\t5\t1455\t0.0\t2550",
             "Query_1\tCP000099.1\t100.00\t1500\t0\t0\t1\t1500\t1\t1500\t0.0\t2700",
             "Query_1\tNR_999999.1\t99.90\t1480\t0\t0\t1\t1480\t1\t1480\t0.0\t2690",
             "Query_1\tCP000003.1\t97.00\t600\t0\t0\t1\t600\t1\t600\t0.0\t1000"]
    (tmp / "b.tsv").write_text("\n".join(blast) + "\n")
    tygs = ["comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d4",
            "U vs. T\t<b>'AS-1.fna'</b> \t\"<I>Streptomyces</I> <I>gamma</I> <a href=\"\"x\"\">NRRL B-9</a>\"\t30.5",
            "U vs. T\t<b>'AS-1.fna'</b> \t\"<I>Streptomyces</I> <I>delta</I> <a>DSM 7</a>\"\t20.1",
            "U vs. T\t<b>'AS-2.fna'</b> \t\"<I>Streptomyces</I> <I>beta</I> <a>Y2</a>\"\t80.0",
            "T vs. T\tx\ty\t50"]
    (tmp / "tygs.tsv").write_text("\n".join(tygs) + "\n")
    (tmp / "ex.txt").write_text("GCF_000099.1\n")


def _run(tmp, *extra):
    out = tmp / "out"
    rc = npc.main(["--isolate", "AS-1", "--blast", str(tmp / "b.tsv"), "--assemblies", str(tmp / "a.jsonl"),
                   "--sequences", str(tmp / "s.jsonl"), "--type-assemblies", str(tmp / "t.jsonl"),
                   "--tygs", str(tmp / "tygs.tsv"), "--exclude", str(tmp / "ex.txt"), "--out-dir", str(out), *extra])
    assert rc == 0
    panel = list(csv.DictReader(open(out / "PANEL_TREE.tsv"), delimiter="\t"))
    issues = list(csv.DictReader(open(out / "PANEL_ISSUES.tsv"), delimiter="\t"))
    return {r["ncbi_accession"]: r for r in panel}, issues


def test_16s_hits_resolve_to_refseq_and_rank_by_identity(tmp_path):
    _fixture(tmp_path)
    panel, _ = _run(tmp_path)
    assert "GCF_000001.1" in panel and "GCA_000001.1" not in panel
    assert panel["GCF_000001.1"]["best_16S_identity"] == "99.50"
    assert panel["GCF_000002.1"]["why"] == "16S_genome_hit"


def test_isolate_own_genome_is_excluded(tmp_path):
    _fixture(tmp_path)
    panel, _ = _run(tmp_path)
    assert "GCF_000099.1" not in panel


def test_short_alignments_and_gene_records_are_reported_not_added(tmp_path):
    _fixture(tmp_path)
    panel, issues = _run(tmp_path)
    assert all("CP000003" not in r["blast_hits"] for r in panel.values())
    assert any(i["source"] == "16S_blast" for i in issues)


def test_tygs_type_strain_prefers_strain_designation_and_reports_misses(tmp_path):
    _fixture(tmp_path)
    panel, issues = _run(tmp_path)
    assert panel["GCF_000011.1"]["why"] == "TYGS_type_strain"
    assert panel["GCF_000011.1"]["tygs_d4"] == "30.5"
    assert "GCF_000010.1" not in panel
    assert any(i["source"] == "TYGS" and "delta" in i["item"] for i in issues)
    # another isolate's TYGS rows never leak in
    assert all("beta" not in r["tygs_type_strain"] for r in panel.values())


def test_top_16s_cap(tmp_path):
    _fixture(tmp_path)
    panel, _ = _run(tmp_path, "--top-16s", "1", "--tygs-top", "0")
    assert list(panel) == ["GCF_000001.1"]


def test_tool_makes_no_network_call():
    src = (ROOT / "tools" / "neighbour_panel_candidates.py").read_text()
    for banned in ("urllib", "requests", "http.client", "socket", "Blast.cgi", "subprocess"):
        assert banned not in src


def test_same_strain_twice_is_kept_once_and_does_not_use_a_slot(tmp_path):
    _fixture(tmp_path)
    # GCF_000002.1 becomes a second deposit of the strain in GCF_000001.1 (same organism + strain designation)
    lines = [json.loads(l) for l in (tmp_path / "a.jsonl").read_text().splitlines()]
    for r in lines:
        if r["accession"] == "GCF_000002.1":
            r["organism"] = {"organism_name": "Streptomyces alpha", "infraspecific_names": {"strain": "X-1"}}
    (tmp_path / "a.jsonl").write_text("\n".join(json.dumps(r) for r in lines) + "\n")
    panel, issues = _run(tmp_path, "--tygs-top", "0")
    assert "GCF_000001.1" in panel and "GCF_000002.1" not in panel
    assert any(i["source"] == "duplicate_strain" and i["item"] == "GCF_000002.1" for i in issues)


def test_plain_text_tygs_rows_resolve_by_species_and_never_to_an_unrelated_genome(tmp_path):
    _fixture(tmp_path)
    # plain-text TYGS table (moss/attine job format), plus an unrelated type genome that must never be chosen
    (tmp_path / "tygs.tsv").write_text("comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d4\n"
        "U vs. T\t'AS-1.fna'\tStreptomyces gamma NRRL B-9\t92.7\n"
        "U vs. T\t'AS-1.fna'\tStreptomyces delta DSM 7\t91.0\n")
    types = [json.loads(l) for l in (tmp_path / "t.jsonl").read_text().splitlines()]
    types.append(_asm("GCF_999999.1", "Rhodococcus zeta", "DSM 1", "assembly from type material"))
    (tmp_path / "t.jsonl").write_text("\n".join(json.dumps(r) for r in types) + "\n")
    panel, issues = _run(tmp_path, "--top-16s", "0")
    assert "GCF_999999.1" not in panel
    assert panel["GCF_000011.1"]["tygs_d4"] == "92.7"
    assert any(i["source"] == "TYGS" and "delta" in i["item"] for i in issues)


def test_unreadable_subject_is_reported_not_matched():
    assert npc.parse_tygs_subject("12345") == ("", "")
    assert npc.resolve_type_strain("", "", {"GCF_1.1": {"organism": "Rhodococcus x", "strain": "", "type": "t", "status": "current"}})[0] is None


def test_every_tygs_top_row_is_in_the_panel_or_logged(tmp_path):
    _fixture(tmp_path)
    # the TYGS strain's only type assembly is excluded: it must be logged by name, not silently dropped
    (tmp_path / "ex.txt").write_text("GCF_000099.1\nGCF_000011.1\nGCF_000010.1\n")
    panel, issues = _run(tmp_path, "--top-16s", "0")
    assert not any(r["tygs_type_strain"] for r in panel.values())
    assert any(i["source"] == "TYGS" and "gamma" in i["item"] for i in issues)


def test_tygs_rows_tied_at_the_cutoff_are_returned_for_logging(tmp_path):
    t = tmp_path / "ty.tsv"
    t.write_text("comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d4\n"
                 "U vs. T\tAS-1\tStreptomyces alpha X1\t30\nU vs. T\tAS-1\tStreptomyces beta Y1\t25\nU vs. T\tAS-1\tStreptomyces gamma Z1\t25\n"
                 "U vs. T\tAS-1\tStreptomyces delta W1\t20\n")
    got = npc.read_tygs([str(t)], "AS-1", 2)
    assert [g[1] for g in got] == ["Streptomyces alpha", "Streptomyces beta", "Streptomyces gamma"]   # tie at the cutoff returned


def test_two_tygs_designations_of_one_assembly_are_both_recorded(tmp_path):
    _fixture(tmp_path)
    (tmp_path / "tygs.tsv").write_text("comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d4\n"
        "U vs. T\tAS-1\tStreptomyces gamma NRRL B-9\t30\nU vs. T\tAS-1\tStreptomyces gamma DSM 99\t29\n")
    panel, issues = _run(tmp_path, "--top-16s", "0")
    assert panel["GCF_000011.1"]["tygs_type_strain"] == "Streptomyces gamma NRRL B-9; Streptomyces gamma DSM 99"


def test_renamed_species_resolves_by_strain_designation_and_is_logged(tmp_path):
    _fixture(tmp_path)
    (tmp_path / "tygs.tsv").write_text("comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d4\n"
        "U vs. T\tAS-1\tStreptomyces oldname NRRL B-9T\t40\n")
    panel, issues = _run(tmp_path, "--top-16s", "0")
    assert "GCF_000011.1" in panel          # filed by NCBI as Streptomyces gamma NRRL B-9
    assert any(i["source"] == "TYGS_resolved_by_designation" and "oldname" in i["item"] for i in issues)


def test_short_designations_never_match():
    asm = {"GCF_1.1": {"organism": "X y", "strain": "A1", "type": "t", "status": "current", "designations": ["a1"]}}
    assert npc.resolve_type_strain("Z w", "A1", asm)[0] is None


def test_default_min_align_is_600(tmp_path):
    _fixture(tmp_path)
    # a 700-bp alignment to CP000002: kept with the default (600), dropped with --min-align 1000
    (tmp_path / "b.tsv").write_text("Query_1\tCP000002.1\t98.00\t700\t0\t0\t1\t700\t1\t700\t0.0\t1200\n")
    panel, _ = _run(tmp_path, "--tygs-top", "0")
    assert "GCF_000002.1" in panel
    panel, _ = _run(tmp_path, "--tygs-top", "0", "--min-align", "1000")
    assert "GCF_000002.1" not in panel
