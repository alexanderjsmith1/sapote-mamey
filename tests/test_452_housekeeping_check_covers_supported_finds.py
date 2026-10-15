"""The housekeeping check covers adjacent partner finds, not only lone ones.

A MIBiG entry can carry housekeeping flanks. A genome's matching housekeeping block then holds several adjacent finds,
and adjacency alone called every one SUPPORTED without a Pfam check. Now every find that is not a paralog-family member
gets the neighbour check, and support must come from an adjacent find that is not housekeeping itself.
"""
from mamey import ref_completion as rc

CORE = {"contig": "core", "start": 0, "end": 10000, "n": 1, "identity": "T / core / region001 / BGC001", "edge": "True"}


def _p(tag, contig, start):
    return {"tag": tag, "contig": contig, "start": start, "end": start + 900, "strand": 1, "contig_len": 50000,
            "aa": "M" + "A" * 300, "kind": ""}


def _row(i, pid):
    return {"reference_gene": i, "name": f"r{i}", "status": "MISSING_FOUND_CLEAR", "best_protein": pid,
            "best_identity_pct": 60.0}


def _hit(i, pid):
    return {"qseqid": f"g{i:03d}", "sseqid": pid, "pident": 60.0, "qcovhsp": 90.0, "bitscore": 300.0}


def _run(layout, finds, pfam=True):
    """layout: {contig: [(tag, [pfam names]), ...]} with genes 1 kb apart; finds: tags matched by reference genes."""
    prots, names = {"c1": _p("c1", "core", 1000)}, {}
    for contig, genes in layout.items():
        for i, (tag, pf) in enumerate(genes):
            prots[tag] = _p(tag, contig, 1000 * i)
            names[tag] = pf
    rows = [{"reference_gene": 1, "name": "r1", "status": "PRESENT_IN_CORE", "best_protein": "c1"}]
    rows += [_row(i + 2, tag) for i, tag in enumerate(finds)]
    hits = [_hit(i + 2, tag) for i, tag in enumerate(finds)]
    fake = lambda seqs, hmm, cpus=4: {k: names.get(k, []) for k in seqs}
    summary = rc.partner_checks(rows, prots, hits, CORE, "BGC0000001", pfam_hmm="Pfam-A.hmm" if pfam else None,
                                pfam_names=fake)
    return {r["best_protein"]: r["partner_verdict"] for r in rows[1:]}, summary, rows


HK_BLOCK = [("h0", ["YgbB"]), ("h1", ["IspD"]), ("h2", ["CarD_TRCF_RID", "CarD_C"]), ("n3", []), ("n4", []),
            ("n5", []), ("n6", []), ("n7", []), ("b8", ["Methyltransf_11"]), ("n9", []), ("n10", []), ("n11", []),
            ("n12", [])]


def test_an_adjacent_block_of_housekeeping_finds_is_set_aside():
    v, summary, rows = _run({"ctgH": HK_BLOCK}, ["h0", "h1", "h2"])
    assert v == {"h0": "HOUSEKEEPING_CONTEXT", "h1": "HOUSEKEEPING_CONTEXT", "h2": "HOUSEKEEPING_CONTEXT"}
    assert summary["neighbour_pfam"] == "run"
    assert all(r["housekeeping_neighbours"] >= rc.HOUSEKEEPING_MIN for r in rows[1:])


def test_a_find_supported_only_by_housekeeping_finds_is_a_single_gene():
    # b8 is 6 kb from h2 (adjacent) but more than 4 genes away, so its own neighbours carry no housekeeping domain
    v, _s, rows = _run({"ctgH": HK_BLOCK}, ["h0", "h1", "h2", "b8"])
    assert v["b8"] == "SINGLE_GENE"
    assert rows[-1]["adjacent_finds"] == 3  # the raw adjacency count is still reported


def test_a_biosynthetic_pair_stays_supported():
    pair = [("k0", ["ketoacyl-synt", "Ketoacyl-synt_C"]), ("k1", ["Acyl_transf_1"]), ("k2", ["Methyltransf_11"]),
            ("k3", ["Abhydrolase_1"]), ("k4", ["FAD_binding_2"])]
    v, _s, _r = _run({"ctgB": pair}, ["k0", "k2"])
    assert v == {"k0": "SUPPORTED", "k2": "SUPPORTED"}


def test_without_pfam_adjacency_alone_supports_and_the_summary_says_the_check_did_not_run():
    v, summary, _r = _run({"ctgH": HK_BLOCK}, ["h0", "h1", "h2"], pfam=False)
    assert set(v.values()) == {"SUPPORTED"}
    assert summary["neighbour_pfam"].startswith("not run")


def test_the_marker_list_names_the_new_primary_metabolism_families_and_not_generic_ones():
    for name in ("YgbB", "IspD", "CarD_TRCF_RID", "CarD_C", "Clp_N", "ClpB_D2-small", "Lsr2", "Lsr2_DNA-bd",
                 "Pan_kinase", "Asp_decarbox", "Pantoate_ligase", "NadA", "QRPTase_N", "QRPTase_C", "Histidinol_dh",
                 "DHDPS", "tRNA-synt_2"):
        assert rc.HOUSEKEEPING_PFAM.match(name), name
    for name in ("FAD_binding_2", "Methyltransf_11", "Abhydrolase_1", "ketoacyl-synt", "AMP-binding", "Chal_sti_synt_N",
                 "UbiA", "Lsr2x", "NadA_like"):
        assert not rc.HOUSEKEEPING_PFAM.match(name), name
