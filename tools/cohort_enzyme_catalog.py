#!/usr/bin/env python3
"""Cohort enzyme catalog: every antiSMASH-region gene of a cohort grouped by enzyme family, with BLASTp distance.

Two levels:
  broad     each gene gets one family and one functional category.
            Family rule, first that applies: the antiSMASH smCOG call ("SMCOGnnnn: <name>"); else the first sec_met
            domain whose category (mamey.domain_reference.categorize) is not "other"/"uncharacterized"; else the first
            sec_met domain; else "no antiSMASH family call".
            The smCOG name is the word prefix shared by every occurrence of that smCOG ID in the run, with trailing words
            removed while they are domain names called on that smCOG's genes, stopping before a cut that would leave the name
            ending in a comma. A comma already at the end of the shared prefix is kept as written (two real smCOGs end
            that way); the tool does not invent the missing words. The words after the name (antiSMASH writes
            a domain or KS-subtype token there, e.g. mod_KS) go to the smcog_subtype_token column.
            Category: the earliest category in CAT_ORDER among the gene's domains and its smCOG name, ignoring
            "other"/"uncharacterized"; else the first domain's category; else "no call". Halogenation is decided by
            the domain: a gene with a halogenation domain (e.g. Trp_halogenase) is tailoring-halogenation even when
            an FAD or monooxygenase call would rank earlier, because flavin-dependent halogenases carry those signals
            too. A halogenase smCOG name without a halogenation domain counts as tailoring-oxidoreduction.
  specific  (only with --clusters) each DIAMOND cluster is one group of the same protein across strains, listing its
            member genes. The tool reads cluster output; it does not run DIAMOND. --emit-fasta writes the pooled
            region-protein FASTA (<strain>|<locus_tag>) to cluster.

BLASTp: --gene-values is GENE_VALUES.tsv from tools/blastp_identity_figures.py. A gene's value is its highest
top10_mean_identity across the databases in that file; blank when the gene has none. With --root, the rank-1 hit
(accession, organism, definition, identity) is read from the gene's result CSVs named in source_file, highest-value row
first, then its other rows; --source-alias OLD=NEW reads a missing path that starts with OLD under NEW. A row belongs to
the gene only when its query (the gene column) is the gene's locus tag, or a proven alias: first word
"<strain>__<locus_tag>" or "<strain>__BGCnnn__<locus_tag>", or (with --query-index) a query in that same file whose
protein SHA-256 equals the gene's protein in the genome's FASTA. The query index is the QUERY_INDEX TSV the GENE_VALUES
run bound by sequence (strain, gene, source_file, protein_sha256, binding_evidence); rows with binding_evidence "none" or
no hash are not used. This keeps results run under an earlier assembly's locus tags. A readable file whose queries are all other genes gives no
hit, and its value is not used: the gene's value comes only from files that hold its own query or cannot be read. When no
such file is left, the gene's value is blank and blastp_hold names the other queries; RUN_INFO.json counts these genes
(genes_blastp_held_query_mismatch) and genes_with_blastp_but_no_top_hit (value kept, file unreadable).

A CDS that antiSMASH places in two adjacent regions appears once per region in the broad tables and once per region
in SPECIFIC_MEMBERS.tsv (same locus tag, different region identity); RUN_INFO.json counts these genes.

Excluded contigs: --exclude-contigs takes a TSV with columns strain and contig (other columns kept as notes). Genes on
those contigs are left out of every table and of the --emit-fasta FASTA. RUN_INFO.json records genes left out per strain,
how many listed contigs matched a gene, the listed (strain, contig) pairs that matched nothing, and listed strains not in
the run, so a name mismatch shows instead of passing silently. Names are compared after trimming whitespace. With an
exclusion list, --emit-fasta refuses a protein that has no gene_context record (its contig would be unknown). Use it to
omit contigs judged unreliable (for example, far below the genome's usual coverage).

Category overrides: --category-overrides takes a TSV with columns family, action, target_category (other columns kept
as notes). It records an owner's ruling that a family's genes do not belong in their rule-based category:
  move_family    every gene of the family that sits in a biosynthetic category moves to target_category
  split_context  only genes in regions whose antiSMASH products are all broad calls (BROAD_CALLS) move; genes in other
                 regions keep their category
Each moved gene keeps its rule-based category in category_before_override and the action in override; RUN_INFO.json
counts moves per action and lists override families absent from the run.

Group IDs: a group's ID is "G" + the first 10 hex characters of the SHA-256 of its centroid protein's sequence
(upper case, trailing "*" removed), read from the genome's protein FASTA. The same centroid gives the same ID in any
build; group_rank keeps the size order (most genomes first). If two centroids share a sequence, the second and later get
"-2", "-3" in centroid-id order. With --previous-members (a SPECIFIC_MEMBERS.tsv from an earlier build), GROUP_CROSSWALK.tsv
maps each earlier group to the current group holding most of its members, with the shared count.

Identity: every gene is written as strain / contig / region / BGC alias / locus tag, from the package's
<strain>_2_inventory.csv row for the BGC (Contig, antiSMASH_Region). A BGC with no inventory row is written with "?"
for the missing parts and counted in RUN_INFO.json identity_holds.

CLAIM SAFETY: a family is a domain/smCOG call and a group is sequence similarity between cohort proteins. Neither is
a product, an activity, or a function claim. BLASTp identity is distance to deposited proteins, not compound novelty.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
BUNDLE = TOOLS.parent
for _p in (str(BUNDLE), str(TOOLS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import argparse
import csv
import hashlib
import json
import os
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

from mamey.csv_safety import SafeDictWriter  # noqa: E402
from mamey.domain_reference import BIOSYNTHETIC_CATEGORIES, CAT_ORDER, categorize  # noqa: E402
from mamey.exclusions import hard_excluded  # noqa: E402
from mamey.protein_binding import protein_sha256  # noqa: E402

TOOL = "cohort_enzyme_catalog"
NO_CALL_FAMILY = "no antiSMASH family call"
BROAD_CALLS = frozenset({"saccharide", "ectoine", "NAPAA", "fatty_acid", "halogenated", "quinone_isoprenoid_chain",
                         "terpene-precursor", "other"})
OVERRIDE_ACTIONS = ("move_family", "split_context")
BIOSYNTHETIC = BIOSYNTHETIC_CATEGORIES
RANK = {c: i for i, c in enumerate(CAT_ORDER)}
HALOGENATION = "tailoring-halogenation"
_SMCOG = re.compile(r"(SMCOG\d+):\s*(.*)")
_STOPS = (" (E-value", " biosynthetic", " transport (", " regulatory (", " other (", " resistance (")


class CatalogError(Exception):
    """Input refused; message says what to fix."""


def smcog_raw(gene_functions: str) -> tuple[str, str]:
    m = _SMCOG.search(gene_functions or "")
    if not m:
        return "", ""
    text = m.group(2)
    for stop in _STOPS:
        k = text.find(stop)
        if k > 0:
            text = text[:k]
    return m.group(1), " ".join(text.split())


def smcog_names(records) -> dict[str, str]:
    """records: iterable of (gene_functions, sec_met_domains). The name of each smCOG ID is the word prefix shared by
    all its occurrences, then with trailing words removed while the last word is a domain name called on any gene of
    that smCOG (antiSMASH appends the domain hit after the smCOG name), unless that would leave a trailing comma."""
    seen: dict[str, list[str]] = {}
    doms: dict[str, set[str]] = defaultdict(set)
    for gf, dl in records:
        sid, text = smcog_raw(gf)
        if not sid:
            continue
        doms[sid].update(d for d in (dl or []) if d)
        words = text.split()
        if sid not in seen:
            seen[sid] = words
        else:
            prefix = []
            for a, b in zip(seen[sid], words):
                if a != b:
                    break
                prefix.append(a)
            seen[sid] = prefix
    out = {}
    for sid, words in seen.items():
        # stop before a cut that would leave the name ending in a comma ("tellurium resistance protein, TerD")
        while len(words) > 1 and words[-1] in doms[sid] and not words[-2].endswith(","):
            words = words[:-1]
        out[sid] = " ".join(words)
    return out


def classify(cds: dict, names: dict[str, str]) -> tuple[str, str, str]:
    """(family, category, smcog_subtype_token) for one gene_context CDS record."""
    doms = [d for d in (cds.get("sec_met_domains") or []) if d]
    sid, text = smcog_raw(cds.get("gene_functions") or "")
    family, sub = "", ""
    if sid:
        name = names.get(sid, text)
        sub = text[len(name):].strip() if name and text.startswith(name) else ""
        family = f"{sid}: {name}" if name else sid
    cats = [(categorize(d)[0], d) for d in doms]
    halo_domain = any(c == HALOGENATION for c, _ in cats)
    if sid:
        label = categorize("", family.split(":", 1)[-1])[0]
        cats.append(("tailoring-oxidoreduction" if label == HALOGENATION and not halo_domain else label, family))
    named = [c for c in cats if c[0] not in ("other", "uncharacterized")]
    if halo_domain:
        named = [c for c in named if c[0] != "tailoring-oxidoreduction"]
    category = min(named, key=lambda c: RANK[c[0]])[0] if named else (cats[0][0] if cats else "no call")
    if not family:
        bio = [d for d in doms if categorize(d)[0] not in ("other", "uncharacterized")]
        family = bio[0] if bio else (doms[0] if doms else NO_CALL_FAMILY)
    return family, category, sub


def read_genomes(path: Path, root: Path) -> list[dict]:
    rows = list(csv.DictReader(open(path, newline=""), delimiter="\t"))
    need = {"strain", "gene_context"}
    if not rows or not need <= set(rows[0]):
        raise CatalogError(f"{path}: needs a header with columns {sorted(need)} (genus, block, proteins optional)")
    strains = [r["strain"] for r in rows]
    dup = sorted(s for s, n in Counter(strains).items() if n > 1)
    if dup:
        raise CatalogError(f"{path}: strain listed more than once: {', '.join(dup)}")
    bad = sorted(set(strains) & hard_excluded())
    if bad:
        raise CatalogError(f"{path}: hard-excluded strain(s) {', '.join(bad)} (mamey.exclusions); remove them from the list")
    for r in rows:
        gc = (root / r["gene_context"]).resolve()
        if not gc.is_file():
            raise CatalogError(f"{r['strain']}: gene_context not found: {gc}")
        r["_gc"] = gc
        r["_inv"] = gc.parent / f"{r['strain']}_2_inventory.csv"
        r["_faa"] = (root / r["proteins"]).resolve() if r.get("proteins") else gc.parent / f"{r['strain']}_proteins.faa"
    return rows


def read_gene_context(path: Path) -> list[dict]:
    lines = path.read_text().splitlines()
    out = []
    for ln in lines[1:]:
        if ln.strip():
            out.append(json.loads(ln))
    return out


def read_gene_values(path: Path | None) -> dict[tuple[str, str], list[tuple[float, str]]]:
    """(strain, gene) -> every (top10_mean_identity, source_file) row of that gene, highest value first.
    All rows are kept so a row whose file holds another gene's query can be dropped and the next one used."""
    rows: dict[tuple[str, str], list[tuple[float, str]]] = defaultdict(list)
    if path is None:
        return {}
    for r in csv.DictReader(open(path, newline=""), delimiter="\t"):
        v = r.get("top10_mean_identity", "")
        if v in ("", None):
            continue
        rows[(r["strain"], r["gene"])].append((float(v), r.get("source_file", "")))
    for v in rows.values():
        v.sort(key=lambda t: -t[0])
    return dict(rows)


class TopHits:
    """Rank-1 hit per gene from blastp_identity_figures source CSVs (columns gene, hit_rank, subject_*)."""

    def __init__(self, root: Path | None, aliases: list[tuple[str, str]] | None = None,
                 query_index: dict | None = None, protein_sha: dict | None = None, query_names: dict | None = None):
        self.root, self.cache, self.aliases = root, {}, list(aliases or [])
        self.qi, self.psha = query_index or {}, protein_sha or {}
        self.qrev = query_names or {}  # (strain, source) -> query name -> its sequence hashes, from every index row
        self.by_sequence = self.conflicts = 0

    def _path(self, source: str) -> Path:
        p = self.root / source
        if not p.is_file():
            for old, new in self.aliases:
                if source.startswith(old):
                    q = self.root / (new + source[len(old):])
                    if q.is_file():
                        return q
        return p

    def lookup(self, source: str, strain: str, gene: str):
        """(status, hit, other_queries) for one source file. status: "match" (the file holds this gene's rank-1 row,
        by the query index's protein hash, or by locus tag or proven alias), "other" (readable, only other genes'
        queries), "conflict" (a name matches, the index records that query as a different protein, and no query in
        the file carries this gene's sequence), "unreadable". Sequence evidence wins over a name: locus tags are
        renumbered between assemblies, so a query whose indexed sequence is this gene's protein is used even when
        another query in the file has this gene's tag."""
        d = self._load(source)
        if d is None:
            return "unreadable", None, []
        h = self.psha.get((strain, gene))
        q = self.qi.get((strain, source), {}).get(h) if h else None
        rev = self.qrev.get((strain, source), {})
        alias = sorted(k for k in d if proven_alias(k, strain, gene))
        named = gene if gene in d else (alias[0] if alias else None)
        if named and h and h in rev.get(named, set()):
            return "match", d[named], []  # name and sequence agree
        if q and q in d:
            if q != named:
                self.by_sequence += 1
            return "match", d[q], []
        if named:
            if h and rev.get(named):
                self.conflicts += 1
                return "conflict", None, [named]
            return "match", d[named], []
        return "other", None, sorted(d)

    def _load(self, source: str):
        if self.root is None or not source:
            return None
        if source not in self.cache:
            d = {}
            try:
                with open(self._path(source), newline="") as fh:
                    for r in csv.DictReader(fh):
                        if r.get("hit_rank") in ("1", "1.0") and r.get("gene"):
                            d.setdefault(r["gene"], (r.get("subject_acc", ""), r.get("subject_organism", ""),
                                                     (r.get("subject_def", "") or "")[:140], r.get("pct_identity", "")))
            except (OSError, csv.Error, UnicodeDecodeError):
                d = None
            self.cache[source] = d
        return self.cache[source]


def read_query_index(path: Path | None) -> dict[tuple[str, str], dict[str, str]]:
    """(strain, source_file) -> {protein_sha256: query name in that file}, from sequence-bound rows only."""
    if path is None:
        return {}
    if not path.is_file():
        raise CatalogError(f"--query-index not found: {path}")
    out: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    rows = csv.DictReader(open(path, newline=""), delimiter="\t")
    need = {"strain", "gene", "source_file", "protein_sha256", "binding_evidence"}
    if not need <= set(rows.fieldnames or []):
        raise CatalogError(f"{path}: needs columns {', '.join(sorted(need))}")
    for r in rows:
        h = (r["protein_sha256"] or "").strip().lower()
        if h and r["binding_evidence"].strip() not in ("", "none"):
            out[(r["strain"], r["source_file"])].setdefault(h, r["gene"])
    return dict(out)


def read_query_names(path: Path | None) -> dict[tuple[str, str], dict[str, set[str]]]:
    """(strain, source_file) -> {query name: its protein_sha256 values}, from every sequence-bound index row. Unlike
    read_query_index this keeps each name, so identical proteins under two names are both known."""
    out: dict = defaultdict(lambda: defaultdict(set))
    if path is None:
        return {}
    for r in csv.DictReader(open(path, newline=""), delimiter="\t"):
        h = (r["protein_sha256"] or "").strip().lower()
        if h and r["binding_evidence"].strip() not in ("", "none"):
            out[(r["strain"], r["source_file"])][r["gene"]].add(h)
    return {k: dict(v) for k, v in out.items()}


def protein_shas(genomes: list[dict]) -> dict[tuple[str, str], str]:
    """(strain, locus_tag) -> SHA-256 of the protein sequence as written in the genome's FASTA."""
    out = {}
    for g in genomes:
        if not g["_faa"].is_file():
            raise CatalogError(f"{g['strain']}: protein FASTA not found for --query-index: {g['_faa']}")
        cur, buf = None, []
        for ln in list(open(g["_faa"])) + [">"]:
            if ln.startswith(">"):
                if cur:
                    out[(g["strain"], cur)] = protein_sha256("".join(buf))
                cur, buf = (ln[1:].split() or [None])[0], []
            else:
                buf.append(ln.strip())
    return out


def proven_alias(query: str, strain: str, gene: str) -> bool:
    """True when a BLASTp query title names this gene: first word "<strain>__<tag>" or "<strain>__BGCnnn__<tag>"."""
    w = query.split()
    t = w[0].split("__") if w else []
    return len(t) >= 2 and t[0] == strain and t[-1] == gene and all(re.fullmatch(r"BGC\d+", x) for x in t[1:-1])


def bind_blastp(rows: list[tuple[float, str]] | None, hits: "TopHits", strain: str, gene: str, check: bool):
    """(value, (acc, org, def, pct), hold) for one gene from its GENE_VALUES rows. Rows whose file holds only other
    genes' queries, or whose name match conflicts with the query index, are dropped. The value is the highest kept
    row; the hit is shown only when that same file holds the gene's own query, so value and hit share one source."""
    blank = ("", "", "", "")
    if not rows:
        return "", blank, ""
    if not check:
        return rows[0][0], blank, ""
    kept, others, conflicts = [], [], []
    for val, src in rows:
        status, h, oth = hits.lookup(src, strain, gene)
        if status == "other":
            others += oth
            continue
        if status == "conflict":
            conflicts += oth
            continue
        kept.append((val, h if status == "match" else None))
    if not kept:
        if conflicts:
            return "", blank, "query index ties " + ", ".join(sorted(set(conflicts))[:3]) + " to a different protein"
        names = sorted(set(others))
        return "", blank, "source query is " + ", ".join(names[:3]) + (" ..." if len(names) > 3 else "") + ", not this gene"
    return kept[0][0], kept[0][1] or blank, ""


def summarize(rows: list[dict]) -> dict:
    v = [r["blastp_top10_mean"] for r in rows if r["blastp_top10_mean"] != ""]
    return dict(genes=len(rows), genomes=len({r["strain"] for r in rows}), regions=len({r["region_identity"] for r in rows}),
                genes_with_blastp=len(v), median_blastp=round(st.median(v), 1) if v else "",
                share_below_70=round(sum(x < 70 for x in v) / len(v), 3) if v else "",
                share_below_50=round(sum(x < 50 for x in v) / len(v), 3) if v else "")


class StagedOutputs:
    """Output files that must not exist yet, published together.

    Every declared path is checked before anything is written: an existing file, a hard link to an input, or a
    symlink (even a dangling one) is refused. Writes go to a hidden temp file beside each target (`staged / name`
    returns it). commit() links each temp into place with os.link, which never replaces an existing path, then
    removes the temps; abort() removes the temps. A run that fails part way leaves no output."""

    def __init__(self, folder: Path, names):
        self.dir, self.names, self.tmp = Path(folder), list(names), {}
        taken = [str(self.dir / n) for n in self.names if os.path.lexists(self.dir / n)]
        if taken:
            raise CatalogError(f"output already exists: {', '.join(taken[:3])}; choose another path or an empty folder")

    def __truediv__(self, name: str) -> Path:
        if name not in self.names:
            raise CatalogError(f"{name} is not a declared output")
        t = self.dir / f".{name}.partial-{os.getpid()}"
        if os.path.lexists(t):
            raise CatalogError(f"temporary output already exists: {t}")
        self.tmp[name] = t
        return t

    def commit(self) -> None:
        done = []
        try:
            for name, t in self.tmp.items():
                os.link(t, self.dir / name)
                done.append(self.dir / name)
        except OSError as e:
            for d in done:
                d.unlink()
            self.abort()
            raise CatalogError(f"could not publish {self.dir / name}: {e}") from e
        self.abort()

    def abort(self) -> None:
        for t in self.tmp.values():
            if os.path.lexists(t):
                os.unlink(t)


def write_tsv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with open(path, "w", newline="") as fh:
        w = SafeDictWriter(fh, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_excluded(path: Path | None) -> set[tuple[str, str]]:
    if path is None:
        return set()
    if not path.is_file():
        raise CatalogError(f"--exclude-contigs not found: {path}")
    rows = list(csv.DictReader(open(path, newline=""), delimiter="\t"))
    if not rows or not {"strain", "contig"} <= set(rows[0]):
        raise CatalogError(f"{path}: needs columns strain and contig")
    return {(r["strain"].strip(), r["contig"].strip()) for r in rows if r["strain"].strip() and r["contig"].strip()}


def read_overrides(path: Path | None) -> dict[str, tuple[str, str]]:
    if path is None:
        return {}
    if not path.is_file():
        raise CatalogError(f"--category-overrides not found: {path}")
    rows = list(csv.DictReader(open(path, newline=""), delimiter="\t"))
    if not rows or not {"family", "action", "target_category"} <= set(rows[0]):
        raise CatalogError(f"{path}: needs columns family, action, target_category")
    out = {}
    for r in rows:
        fam, act, tgt = r["family"].strip(), r["action"].strip(), r["target_category"].strip()
        if act not in OVERRIDE_ACTIONS:
            raise CatalogError(f"{path}: action for {fam!r} must be one of {', '.join(OVERRIDE_ACTIONS)}")
        if tgt not in CAT_ORDER:
            raise CatalogError(f"{path}: target_category {tgt!r} for {fam!r} is not a domain_reference category")
        if fam in out:
            raise CatalogError(f"{path}: family {fam!r} listed twice")
        out[fam] = (act, tgt)
    return out


def broad_only(products: str) -> bool:
    prods = {x.strip() for x in (products or "").replace(";", ",").split(",") if x.strip()}
    return bool(prods) and prods <= BROAD_CALLS


def contig_of_locus(genomes: list[dict]) -> dict[tuple[str, str], set[str]]:
    """(strain, locus_tag) -> the contig names a gene is recorded under: its CDS contig and its region's inventory Contig."""
    out: dict[tuple[str, str], set[str]] = defaultdict(set)
    for g in genomes:
        inv = {}
        if g["_inv"].is_file():
            inv = {r.get("BGC_ID", ""): r.get("Contig", "") for r in csv.DictReader(open(g["_inv"], newline=""))}
        for rec in read_gene_context(g["_gc"]):
            for c in rec.get("cds", []):
                names = out[(g["strain"], c["locus_tag"])]
                names.update(x for x in (c.get("contig", ""), inv.get(rec.get("bgc_id", ""), "")) if x)
    return out


def emit_fasta(genomes: list[dict], out: Path, excluded: set[tuple[str, str]] | None = None) -> int:
    """Write the pooled FASTA to `out`, which must not exist. Every protein FASTA is checked first, and the file is
    published only when complete, so a refused run leaves no output and never touches an input."""
    excluded = excluded or set()
    missing = [g for g in genomes if not g["_faa"].is_file()]
    if missing:
        raise CatalogError(f"{missing[0]['strain']}: protein FASTA not found: {missing[0]['_faa']}")
    contig = contig_of_locus(genomes) if excluded else {}
    seen, n = set(), 0
    staged = StagedOutputs(out.parent, [out.name])
    try:
        n = _write_fasta(genomes, staged / out.name, excluded, contig, seen)
        staged.commit()
    except BaseException:
        staged.abort()
        raise
    return n


def _write_fasta(genomes: list[dict], path: Path, excluded, contig, seen) -> int:
    n = 0
    with open(path, "x") as fo:
        for g in genomes:
            for ln in open(g["_faa"]):
                if ln.startswith(">"):
                    tag = ln[1:].split()[0]
                    key = f"{g['strain']}|{tag}"
                    if excluded and (g["strain"], tag) not in contig:
                        raise CatalogError(f"{g['strain']}|{tag} is in the protein FASTA but in no gene_context record, "
                                           "so its contig is unknown; exclusions cannot be applied safely")
                    skip = any((g["strain"], name) in excluded for name in contig.get((g["strain"], tag), ()))
                    if skip:
                        continue
                    if key in seen:
                        raise CatalogError(f"duplicate protein id {key}")
                    seen.add(key)
                    fo.write(f">{key}\n")
                    n += 1
                elif not skip:
                    fo.write(ln)
    return n


def read_clusters(path: Path) -> dict[str, list[str]]:
    """centroid -> members. Each member must appear on exactly one row, and each centroid must be its own member."""
    cl: dict[str, list[str]] = defaultdict(list)
    seen: dict[str, str] = {}
    for n, ln in enumerate(open(path), 1):
        parts = ln.rstrip("\n").split("\t")
        if len(parts) < 2 or parts[0] == "centroid":
            continue
        c, m = parts[0], parts[1]
        if m in seen:
            raise CatalogError(f"{path}: line {n}: member {m} is listed again (first under centroid {seen[m]}, "
                               f"now under {c}); each protein must belong to one cluster")
        seen[m] = c
        cl[c].append(m)
    if not cl:
        raise CatalogError(f"{path}: no centroid/member rows (expected DIAMOND cluster output: centroid<TAB>member)")
    bad = sorted(c for c in cl if seen.get(c) != c)
    if bad:
        raise CatalogError(f"{path}: {len(bad)} centroid(s) are not listed as their own member, e.g. {bad[0]}")
    return cl


def read_realign(path: Path | None) -> dict[tuple[str, str], tuple[float, float]]:
    """(centroid, member) -> (pident, member cover). A repeated pair must repeat the same values."""
    out: dict[tuple[str, str], tuple[float, float]] = {}
    if path is None:
        return out
    for n, ln in enumerate(open(path), 1):
        p = ln.rstrip("\n").split("\t")
        if len(p) >= 8:  # qseqid (centroid) sseqid (member) pident length qlen slen qcovhsp scovhsp ...
            k, v = (p[0], p[1]), (float(p[2]), float(p[7]))
            if k in out and out[k] != v:
                raise CatalogError(f"{path}: line {n}: {k[0]} -> {k[1]} is listed twice with different values")
            out[k] = v
    return out


CATALOG_OUTPUTS = ("ENZYME_GENES.tsv", "ENZYME_CATEGORY_SUMMARY.tsv", "ENZYME_FAMILY_SUMMARY.tsv",
                   "ENZYME_CATEGORY_BY_BLOCK.tsv", "SPECIFIC_GROUPS.tsv", "SPECIFIC_MEMBERS.tsv", "GROUP_CROSSWALK.tsv",
                   "RUN_INFO.json")


def build(genomes_tsv: Path, root: Path, out: Path, gene_values: Path | None = None, clusters: Path | None = None,
          realign: Path | None = None, cluster_settings: str = "", read_top_hits: bool = True,
          source_aliases: list[tuple[str, str]] | None = None, exclude_contigs: Path | None = None,
          category_overrides: Path | None = None, previous_members: Path | None = None,
          query_index: Path | None = None) -> dict:
    """Build the catalog into `out`. No output may exist yet; all outputs are published together at the end."""
    out.mkdir(parents=True, exist_ok=True)
    clash = [p.name for p in out.glob("ENZYME_*.tsv")] + [p.name for p in out.glob("SPECIFIC_*.tsv")]
    if clash:
        raise CatalogError(f"{out}: already holds {', '.join(sorted(clash))}; choose an empty folder")
    staged = StagedOutputs(out, CATALOG_OUTPUTS)
    try:
        info = _build(genomes_tsv, root, staged, gene_values, clusters, realign, cluster_settings, read_top_hits,
                      source_aliases, exclude_contigs, category_overrides, previous_members, query_index)
        staged.commit()
    except BaseException:
        staged.abort()
        raise
    return info


def _build(genomes_tsv: Path, root: Path, out: "StagedOutputs", gene_values, clusters, realign, cluster_settings,
           read_top_hits, source_aliases, exclude_contigs, category_overrides, previous_members, query_index) -> dict:
    genomes = read_genomes(genomes_tsv, root)
    excluded = read_excluded(exclude_contigs)
    dropped: Counter = Counter()
    matched: set[tuple[str, str]] = set()
    overrides = read_overrides(category_overrides)
    moved: Counter = Counter()
    contexts = {g["strain"]: read_gene_context(g["_gc"]) for g in genomes}
    names = smcog_names((c.get("gene_functions") or "", c.get("sec_met_domains") or [])
                        for recs in contexts.values() for rec in recs for c in rec.get("cds", []))
    best = read_gene_values(gene_values)
    qi = read_query_index(query_index)
    hits = TopHits(root if read_top_hits else None, source_aliases, qi, protein_shas(genomes) if qi else None,
                   read_query_names(query_index) if qi else None)
    genes, holds = [], 0
    for g in genomes:
        s = g["strain"]
        inv = {}
        if g["_inv"].is_file():
            inv = {r.get("BGC_ID", ""): r for r in csv.DictReader(open(g["_inv"], newline=""))}
        for rec in contexts[s]:
            b = rec.get("bgc_id", "")
            iv = inv.get(b)
            if iv is None:
                holds += 1
                iv = {}
            region_id = f"{s} / {iv.get('Contig') or '?'} / {iv.get('antiSMASH_Region') or '?'} / {b or '?'}"
            for c in rec.get("cds", []):
                hit = [(s, n) for n in (c.get("contig", ""), iv.get("Contig", "")) if (s, n) in excluded]
                if hit:
                    dropped[s] += 1
                    matched.update(hit)
                    continue
                fam, cat, sub = classify(c, names)
                before, how = cat, ""
                ov = overrides.get(fam)
                if ov and cat in BIOSYNTHETIC and (ov[0] == "move_family" or broad_only(iv.get("Products", ""))):
                    cat, how = ov[1], ov[0]
                    moved[how] += 1
                val, (acc, org, de, pid), hold = bind_blastp(best.get((s, c["locus_tag"])), hits, s, c["locus_tag"],
                                                             read_top_hits)
                genes.append(dict(strain=s, genus=g.get("genus", ""), block=g.get("block", ""),
                                  region_identity=region_id, gene_identity=f"{region_id} / {c['locus_tag']}",
                                  locus_tag=c["locus_tag"], aa_length=c.get("aa_length", ""), family=fam,
                                  smcog_subtype_token=sub, category=cat, category_before_override=before,
                                  override=how, gene_kind=c.get("gene_kind") or "",
                                  domains=";".join(c.get("sec_met_domains") or []), products=iv.get("Products", ""),
                                  blastp_top10_mean=round(val, 2) if val != "" else "", blastp_hold=hold,
                                  top_hit_acc=acc, top_hit_organism=org, top_hit_pct=pid, top_hit_def=de))
    order = lambda c: RANK.get(c, len(RANK))
    write_tsv(out / "ENZYME_GENES.tsv", genes)
    bycat, byfam, byblock = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in genes:
        bycat[r["category"]].append(r)
        byfam[r["family"]].append(r)
        byblock[(r["category"], r["block"])].append(r)
    write_tsv(out / "ENZYME_CATEGORY_SUMMARY.tsv",
              [dict(category=c, **summarize(v)) for c, v in sorted(bycat.items(), key=lambda x: order(x[0]))])
    fams = []
    for f, v in byfam.items():
        cc = Counter(r["category"] for r in v)
        c = cc.most_common(1)[0][0]
        vv = [r for r in v if r["blastp_top10_mean"] != ""]
        lo = min(vv, key=lambda r: r["blastp_top10_mean"]) if vv else None
        subs = Counter(r["smcog_subtype_token"] for r in v if r["smcog_subtype_token"])
        fams.append(dict(category=c, family=f, **summarize(v),
                         other_categories="; ".join(f"{k} {n}" for k, n in cc.most_common() if k != c),
                         subtype_tokens="; ".join(f"{k} {n}" for k, n in subs.most_common(6)),
                         most_distant_gene=f"{lo['gene_identity']} ({lo['aa_length']} aa)" if lo else "",
                         most_distant_value=lo["blastp_top10_mean"] if lo else ""))
    fams.sort(key=lambda r: (order(r["category"]), -r["genes"], r["family"]))
    write_tsv(out / "ENZYME_FAMILY_SUMMARY.tsv", fams)
    if any(g.get("block") for g in genomes):
        write_tsv(out / "ENZYME_CATEGORY_BY_BLOCK.tsv",
                  [dict(category=c, block=b, **summarize(v)) for (c, b), v in sorted(byblock.items(), key=lambda x: (order(x[0][0]), x[0][1]))])
    info = dict(tool=TOOL, genomes=len(genomes), genes=len(genes), families=len(byfam),
                genes_with_blastp=sum(1 for r in genes if r["blastp_top10_mean"] != ""),
                genes_bound_by_sequence_alias=hits.by_sequence if read_top_hits else None,
                blastp_rows_dropped_index_conflict=hits.conflicts if read_top_hits else None,
                genes_blastp_held_query_mismatch=sum(1 for r in genes if r["blastp_hold"]) if read_top_hits else None,
                genes_with_blastp_but_no_top_hit=sum(1 for r in genes if r["blastp_top10_mean"] != "" and not r["top_hit_acc"]) if read_top_hits else None,
                smcog_genes=sum(1 for r in genes if r["family"].startswith("SMCOG")),
                no_call_genes=sum(1 for r in genes if r["family"] == NO_CALL_FAMILY), identity_holds=holds,
                excluded_genes_by_strain=dict(sorted(dropped.items())), excluded_contigs_listed=len(excluded),
                excluded_contigs_matched=len(matched),
                excluded_contigs_unmatched=sorted(f"{a}\t{b}" for a, b in excluded - matched),
                excluded_strains_not_in_run=sorted({a for a, _ in excluded} - {g["strain"] for g in genomes}),
                overrides_listed=len(overrides), genes_moved_by_override=dict(sorted(moved.items())),
                override_families_not_in_run=sorted(set(overrides) - {r["family"] for r in genes}),
                inputs=dict(genomes=dict(path=str(genomes_tsv), sha256=sha256(genomes_tsv)),
                            gene_values=dict(path=str(gene_values), sha256=sha256(gene_values)) if gene_values else None,
                            exclude_contigs=dict(path=str(exclude_contigs), sha256=sha256(exclude_contigs)) if exclude_contigs else None,
                            query_index=dict(path=str(query_index), sha256=sha256(query_index)) if query_index else None,
                            category_overrides=dict(path=str(category_overrides), sha256=sha256(category_overrides)) if category_overrides else None))
    if clusters is not None:
        info.update(_specific(genes, out, clusters, realign, cluster_settings, genomes, previous_members))
    (out / "RUN_INFO.json").write_text(json.dumps(info, indent=1) + "\n")
    return info


def centroid_ids(centroids, genomes: list[dict]) -> dict[str, str]:
    """centroid key (strain|locus_tag) -> stable group ID from the centroid protein's sequence."""
    want = defaultdict(set)
    for c in centroids:
        st_, tag = c.split("|", 1)
        want[st_].add(tag)
    seqs: dict[str, str] = {}
    for g in genomes:
        tags = want.get(g["strain"])
        if not tags:
            continue
        if not g["_faa"].is_file():
            raise CatalogError(f"{g['strain']}: protein FASTA not found for group IDs: {g['_faa']}")
        cur, buf = None, []
        for ln in list(open(g["_faa"])) + [">"]:
            if ln.startswith(">"):
                if cur in tags:
                    seqs[f"{g['strain']}|{cur}"] = "".join(buf)
                cur, buf = (ln[1:].split() or [None])[0], []
            else:
                buf.append(ln.strip())
    missing = sorted(set(centroids) - set(seqs))
    if missing:
        raise CatalogError(f"no protein sequence for {len(missing)} group centroid(s), e.g. {missing[0]}")
    out, used = {}, Counter()
    for c in sorted(centroids):
        base = "G" + hashlib.sha256(seqs[c].upper().rstrip("*").encode()).hexdigest()[:10]
        used[base] += 1
        out[c] = base if used[base] == 1 else f"{base}-{used[base]}"
    return out


def write_crosswalk(previous: Path, members: list[dict], out: Path) -> dict:
    if not previous.is_file():
        raise CatalogError(f"--previous-members not found: {previous}")
    new_of = {m["gene_identity"]: m["group"] for m in members}
    old = defaultdict(set)
    for r in csv.DictReader(open(previous, newline=""), delimiter="\t"):
        old[r["group"]].add(r["gene_identity"])
    new_size = Counter(new_of.values())
    rows = []
    for g, ids in old.items():
        hits = Counter(new_of[i] for i in ids if i in new_of)
        best, n = hits.most_common(1)[0] if hits else ("", 0)
        rows.append(dict(previous_group=g, current_group=best, shared_members=n, previous_members=len(ids),
                         current_members=new_size.get(best, 0), previous_members_not_in_current=len(ids) - sum(hits.values()),
                         split_into=len(hits)))
    rows.sort(key=lambda r: r["previous_group"])
    write_tsv(out / "GROUP_CROSSWALK.tsv", rows)
    return dict(previous_groups=len(rows), exact_same_membership=sum(1 for r in rows if r["shared_members"] == r["previous_members"] == r["current_members"]),
                previous_groups_without_current=sum(1 for r in rows if not r["current_group"]))


def _specific(genes: list[dict], out: Path, clusters: Path, realign: Path | None, settings: str,
              genomes: list[dict] | None = None, previous_members: Path | None = None) -> dict:
    by_key: dict[str, list[dict]] = defaultdict(list)  # a CDS on the boundary of two regions has one row per region
    for r in genes:
        by_key[f"{r['strain']}|{r['locus_tag']}"].append(r)
    cl = read_clusters(clusters)
    unknown = sorted({m for ms in cl.values() for m in ms if m not in by_key})
    if unknown:
        raise CatalogError(f"{clusters}: {len(unknown)} member id(s) are not genes of this run, e.g. {unknown[0]}; "
                           "cluster the FASTA written by --emit-fasta for the same genomes list")
    ra = read_realign(realign)
    pairs = {(c, m) for c, ms in cl.items() for m in ms}
    stray = sorted(set(ra) - pairs)
    if stray:
        raise CatalogError(f"{realign}: {len(stray)} realignment row(s) pair a member with a centroid that is not its "
                           f"cluster's, e.g. {stray[0][0]} -> {stray[0][1]}; realign the same cluster output")
    strains_of = lambda ms: {m.split("|", 1)[0] for m in ms}
    order = sorted(cl, key=lambda c: (-len(strains_of(cl[c])), -len(cl[c]), c))
    stable = centroid_ids(order, genomes or [])
    members, groups, grouped = [], [], set()
    for i, c in enumerate(order, 1):
        gid = stable[c]
        recs = []
        for m in cl[c]:
            pid, cov = ra.get((c, m), ("", ""))
            for r in by_key[m]:
                recs.append(dict(group=gid, strain=r["strain"], gene_identity=r["gene_identity"], aa_length=r["aa_length"],
                                 is_centroid=m == c, pct_id_to_centroid="" if m == c else pid,
                                 member_cover="" if m == c else cov, family=r["family"], category=r["category"],
                                 products=r["products"], blastp_top10_mean=r["blastp_top10_mean"],
                                 top_hit_acc=r["top_hit_acc"], top_hit_organism=r["top_hit_organism"],
                                 top_hit_pct=r["top_hit_pct"], top_hit_def=r["top_hit_def"]))
        members += recs
        grouped.update(cl[c])
        vals = [r["blastp_top10_mean"] for r in recs if r["blastp_top10_mean"] != ""]
        ids = [r["pct_id_to_centroid"] for r in recs if r["pct_id_to_centroid"] != ""]
        cat = Counter(r["category"] for r in recs).most_common(1)[0][0]
        groups.append(dict(group=gid, group_rank=i, centroid=c, members=len(recs), strains=len({r["strain"] for r in recs}),
                           family=Counter(r["family"] for r in recs).most_common(1)[0][0], category=cat,
                           biosynthetic=cat in BIOSYNTHETIC, min_pct_id_to_centroid=min(ids) if ids else "",
                           members_with_blastp=len(vals), median_blastp=round(st.median(vals), 1) if vals else "",
                           min_blastp=min(vals) if vals else "",
                           strain_list=", ".join(sorted({r["strain"] for r in recs}))))
    write_tsv(out / "SPECIFIC_GROUPS.tsv", groups)
    write_tsv(out / "SPECIFIC_MEMBERS.tsv", members)
    multi = [g for g in groups if g["strains"] >= 2]
    xwalk = write_crosswalk(previous_members, members, out) if previous_members else None
    return dict(specific=dict(group_id_basis="sha256 of centroid protein sequence, first 10 hex", crosswalk=xwalk,groups=len(groups), groups_in_2plus_strains=len(multi),
                              biosynthetic_groups_in_2plus_strains=sum(1 for g in multi if g["biosynthetic"]),
                              genes_not_in_any_group=len(set(by_key) - grouped),
                              genes_in_two_or_more_regions=sum(1 for v in by_key.values() if len(v) > 1),
                              clusters=dict(path=str(clusters), sha256=sha256(clusters), settings=settings or "not recorded"),
                              realign=dict(path=str(realign), sha256=sha256(realign)) if realign else None))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cohort_enzyme_catalog.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--genomes", type=Path, required=True,
                   help="TSV: strain, gene_context (path relative to --root); optional genus, block, proteins")
    p.add_argument("--root", type=Path, required=True, help="folder the genomes TSV paths and BLASTp source_file paths are relative to")
    p.add_argument("--out", type=Path, help="empty output folder")
    p.add_argument("--gene-values", type=Path, help="GENE_VALUES.tsv from tools/blastp_identity_figures.py")
    p.add_argument("--no-top-hits", action="store_true", help="do not read rank-1 hits from the BLASTp source CSVs")
    p.add_argument("--source-alias", action="append", default=[], metavar="OLD=NEW",
                   help="when a source_file path starting with OLD is missing, read it under NEW instead (repeatable)")
    p.add_argument("--clusters", type=Path, help="DIAMOND cluster output (centroid<TAB>member) over the --emit-fasta FASTA")
    p.add_argument("--realign", type=Path, help="DIAMOND realign output, -f 6 qseqid sseqid pident length qlen slen qcovhsp scovhsp ...")
    p.add_argument("--cluster-settings", default="", help="the DIAMOND command used, recorded in RUN_INFO.json")
    p.add_argument("--query-index", type=Path,
                   help="QUERY_INDEX TSV of the GENE_VALUES run: accept a source query whose protein hash equals the gene's")
    p.add_argument("--previous-members", type=Path,
                   help="SPECIFIC_MEMBERS.tsv of an earlier build: write GROUP_CROSSWALK.tsv (earlier group -> current group)")
    p.add_argument("--category-overrides", type=Path,
                   help="TSV family, action (move_family|split_context), target_category: an owner's category ruling")
    p.add_argument("--exclude-contigs", type=Path, help="TSV with strain and contig columns: genes on these contigs are left out")
    p.add_argument("--emit-fasta", type=Path, help="write the pooled region-protein FASTA (<strain>|<locus_tag>) and stop")
    a = p.parse_args(argv)
    try:
        if a.emit_fasta:
            emit_fasta(read_genomes(a.genomes, a.root), a.emit_fasta, read_excluded(a.exclude_contigs))
            return 0
        if a.out is None:
            raise CatalogError("--out is required unless --emit-fasta is given")
        if a.realign and not a.clusters:
            raise CatalogError("--realign needs --clusters")
        aliases = []
        for spec in a.source_alias:
            if "=" not in spec:
                raise CatalogError(f"--source-alias needs OLD=NEW, got {spec!r}")
            old, new = spec.split("=", 1)
            aliases.append((old, new))
        build(a.genomes, a.root, a.out, a.gene_values, a.clusters, a.realign, a.cluster_settings, not a.no_top_hits,
              aliases, a.exclude_contigs, a.category_overrides, a.previous_members, a.query_index)
    except CatalogError as e:
        p.error(f"REFUSED: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
