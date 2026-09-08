"""blastp_online — the missing runner + interpreter for the NCBI web BLASTp channel.

The pipeline already emits NCBI-safe FASTA batches (blastp_batch_emitter) for manual
submission. This module is the automated runner the ONLINE_BLASTP_PROTOCOL specifies: it
submits a batch to NCBI's public BLAST URL API, polls until ready, parses the XML, and
reconciles each hit against the antiSMASH domain call (CONFIRM / REFINE / OVERTURN).

Design constraints (non-negotiable, from the pipeline's offline-first stance):
  * NETWORK IS OPTIONAL AND FAIL-CLOSED. If blast.ncbi.nlm.nih.gov is unreachable, the runner
    returns a clear "channel unavailable" result and NEVER fabricates hits. Mode B authoring
    then falls back to antiSMASH+KCB with an explicit unverified banner (protocol §6).
  * A BLASTp hit is SIMILARITY, not function or product identity. Coverage and %id are always
    reported so the reader can weight the lead. "Capacity consistent with," never "produces."
  * Batch <=10 proteins; giant proteins (>2500 aa) run solo (protocol §3.0/§3.1).

The reconciliation + parsing core is offline-unit-tested against recorded NCBI XML. The live
submit/poll path is SPECIFIED and structured per the verified recipe but, in a network-
restricted build, ships UNVERIFIED — it is exercised only where NCBI is reachable.
"""

from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import sys as _sys

import io
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from dataclasses import dataclass, field
try:
    from .csv_safety import SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_r7): the §4 panel is a computed table, not a byte-faithful capture
except ImportError:
    from mamey.csv_safety import SafeWriter as _SafeWriter

NCBI_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
# v9.7.240: raised 10 -> 30. The 10-protein cap was a conservative reading of the URLAPI guidance;
# a real 878-protein AS-XXX run over 30 RIDs at 30 proteins/batch completed successfully against
# nr_cluster_seq (BLASTP 2.17.0+). Keep 10 as the DEFAULT (courteous); allow up to 30 explicitly.
MAX_BATCH = 30
DEFAULT_BATCH = 10
# v9.7.250: the largest submission size for which per-gene hit recovery has been checked against a
# controlled batch-size-10 re-run. An analysis chat reproduced (3x, AS-XXX BGC034, real nr) an entire
# 30-query batch returning ZERO alignments, whose 30 genes were then written as tested-negatives; the
# same proteins at batch-size 10 recovered 82/83 at 61-99% identity. The mechanism is NOT established.
# Anything above SAFE_BATCH is opt-in and warns. MAX_BATCH is NOT lowered: an independent 36-RID AS-XXX
# campaign (evidence archive, 2026-07-09) ran five 30-query batches with 27-28/30 genes hit, so the
# failure is not "batch>10 always breaks". Making it DETECTABLE is the fix that does not depend on a
# mechanism -- see _zero_alignment_batch() below.
SAFE_BATCH = 10
GIANT_AA = 2500

# v9.7.252: batches were capped by PROTEIN COUNT only. Giants (>GIANT_AA) already ran solo, but nothing
# capped CUMULATIVE residues: thirty 2,400-aa proteins is 72,000 residues in one submission and not one
# of them is a "giant". Field report (the Developer or User, 2026-07-10): "batches of 30 worked fine except for very
# large proteins, and the submissions needed temporal spacing." That reconciles the two contradictory
# observations on record -- five clean 30-protein batches in the AS-XXX archive, and a 30-protein batch
# returning zero alignments, reproduced 3x. The variable was never the count; it was the payload.
# 30,000 is a first calibration from that report (30 x ~1,000 aa). Tune it with evidence, not taste.
RESIDUE_BUDGET = 30_000
SUBMIT_GAP_S = 3.0          # temporal spacing between submissions, not just on retry
CLAIM_SAFETY = ("BLASTp hit is homology (similarity), not function or product identity. "
                "Capacity consistent with, never produces.")


@dataclass
class BlastpHit:
    locus_tag: str
    aa_length: int
    antismash_domains: str
    blastp_top_def: str = ""
    blastp_accession: str = ""
    blastp_organism: str = ""
    pct_identity: float | None = None
    pct_positive: float | None = None
    query_coverage: float | None = None
    evalue: float | None = None
    bitscore: float | None = None
    agreement: str = ""          # CONFIRM / REFINE / OVERTURN / NO_HIT (author-set heuristic)
    top_hits: list = field(default_factory=list)   # protocol §9: top ~6 hits, full stats each


def _genus(organism: str) -> str:
    """First token of the organism string — the genus, for the cluster-coherence reads."""
    return (organism or "").strip().split()[0] if organism else ""


_ROLE_MAP = [
    (("ks", "ketoacyl", "beta-ketoacyl"), "core_PKS"),
    (("amp-binding", "condensation", "adenylation", "nrps"), "core_NRPS"),
    (("ycao", "rre", "lanthionine", "lasso", "lanthipeptide"), "core_RiPP"),
    (("p450", "rieske", "monooxygenase", "hydroxylase", "oxidoreductase", "dehydrogenase"), "tailoring_oxidative"),
    (("methyltransferase",), "tailoring_methyl"),
    (("glycosyltransferase",), "tailoring_glycosyl"),
    (("mfs", "abc", "rnd", "mmpl", "permease", "efflux", "transporter"), "transport"),
    (("aac(", "aph", " nat ", "beta-lactamase", "van", "erm", "resistance", "acetyltransferase"), "resistance"),
    (("hth", "tetr", "marr", "luxr", "sarp", "iclr", "regulator", "transcriptional"), "regulator"),
    (("precursor", "leader peptide"), "precursor"),
]
_UNCHAR_RE = re.compile(r"hypothetical|uncharacteri[sz]ed|DUF\d+|unknown function|putative protein", re.I)


def _consensus_def(top_hits: list) -> str:
    """Majority functional term across the top-N hit defs (strip [organism]). Guards against a
    single mis-annotated top hit — the ctg12_71 esterase-not-β-lactamase lesson (§10.1)."""
    from collections import Counter
    terms = []
    for row in top_hits:
        d = re.sub(r"\[[^\]]+\]", "", row.get("hit_def", row.get("blastp_top_def", "")) or "")
        d = re.sub(r"MULTISPECIES:\s*", "", d).strip().lower()
        if d:
            terms.append(d)
    if not terms:
        return ""
    return Counter(terms).most_common(1)[0][0]


def _role_of(text: str) -> str:
    t = (text or "").lower()
    for kws, role in _ROLE_MAP:
        if any(k in t for k in kws):
            return role
    return "accessory"


def _function_confidence(top_id, top_cov) -> str:
    if top_id is None or top_cov is None:
        return "NONE"
    if top_id >= 40 and top_cov >= 70:
        return "HIGH"
    if 25 <= top_id < 40 and top_cov >= 50:
        return "MEDIUM"
    return "NONE"


def function_and_novelty(hits, kcb_top: str = "", kcb_coverage_genes: int | None = None,
                         core_gene_frac_to_known: float = 0.5) -> dict:
    """Assess FUNCTION and NOVELTY per ONLINE_BLASTP_PROTOCOL §10 — deterministic; Sapote only
    interprets. FUNCTION uses the top-N CONSENSUS (not top-1) with confidence tiers. NOVELTY is
    kept as TWO SEPARATE AXES: gene-level (from BLASTp) and product-level (needs the characterised
    cross-check — BLASTp-to-nr alone cannot decide, the BGC006 lesson). Never raises; capacity
    language only."""
    # v9.7.335: `scored` drops every gene with no hit, but gene_novelty == "ORPHAN" requires
    # top_id is None — so orphans was structurally ALWAYS empty and the banner printed a constant
    # "0 orphan". characterized_fraction / pct_uncharacterized / mean_top_hit_identity all used a
    # survivorship-biased denominator. Assess over every submitted gene.
    scored = list(hits)
    n = len(scored)
    if n == 0:
        return {"n_genes": 0, "note": "no hits to assess"}

    per_gene, roles = [], []
    unchar_n = 0
    ids = []
    for h in scored:
        th = h.top_hits or [{"hit_def": h.blastp_top_def, "pct_identity": h.pct_identity,
                             "query_coverage": h.query_coverage, "organism": h.blastp_organism}]
        consensus = _consensus_def(th)
        uncharacterized = bool(_UNCHAR_RE.search(consensus)) if consensus else True
        top_id = h.pct_identity if h.pct_identity is not None else (th[0].get("pct_identity"))
        top_cov = h.query_coverage if h.query_coverage is not None else (th[0].get("query_coverage"))
        conf = _function_confidence(top_id, top_cov)
        # role from antiSMASH domain first (authoritative for core), else from the consensus def
        role = _role_of(h.antismash_domains) if h.antismash_domains else _role_of(consensus)
        if role == "accessory" and consensus:
            role = _role_of(consensus)
        if top_id is not None:
            ids.append(top_id)
        if uncharacterized:
            unchar_n += 1
        # gene-level novelty
        if top_id is None:
            gnov = "ORPHAN"
        elif top_id < 40:
            gnov = "HIGHLY_DIVERGENT"
        elif top_id < 70:
            gnov = "DIVERGENT"
        elif top_id < 90:
            gnov = "TYPICAL"
        else:
            gnov = "CONSERVED"
        per_gene.append({"locus_tag": h.locus_tag, "function_call": "UNKNOWN" if uncharacterized else consensus,
                         "role": role, "confidence": conf, "top_id": top_id, "top_cov": top_cov,
                         "uncharacterized": uncharacterized, "gene_novelty": gnov})
        roles.append(role)

    mean_id = round(sum(ids) / len(ids), 1) if ids else None
    pct_unchar = round(100.0 * unchar_n / n, 1)

    # product-level novelty (§10.2b): needs the characterised cross-check, gated by CORE coverage.
    # BLASTp-to-nr ALONE cannot decide this — so the gate is conservative and fails toward NOVEL
    # (the claim-safe direction: never call a compound KNOWN without strong cluster-level overlap).
    # A KCB anchor is a product match ONLY if it covers >= core_gene_frac_to_known of core genes
    # AND represents a substantial share of the whole cluster (not "a handful" — the BGC006 lesson:
    # colibrimycin score 3734 but few shared genes => NOT a product match).
    core_n = sum(1 for r in roles if r.startswith("core_"))
    if kcb_top and kcb_coverage_genes is not None and core_n:
        covers_core = kcb_coverage_genes >= max(2, int(core_gene_frac_to_known * core_n))
        substantial = kcb_coverage_genes >= max(5, int(0.3 * n))   # >= ~30% of the whole cluster
        if covers_core and substantial:
            product_novelty = "KNOWN_COMPOUND"
        elif kcb_coverage_genes >= 5:
            product_novelty = "KNOWN_CLASS"
        else:
            product_novelty = "NOVEL"          # few shared genes => novel at product level
    elif kcb_top and kcb_coverage_genes is not None:
        product_novelty = "KNOWN_CLASS" if kcb_coverage_genes >= 5 else "NOVEL"
    else:
        # v9.7.335: this branch ALWAYS fired — function_and_novelty is called with
        # getattr(args, "kcb_top", "") / getattr(args, "kcb_coverage_genes", None) but neither
        # argparse destination exists on the blastp-online parser, so the cross-check inputs were
        # always empty and every cluster ever analysed was reported NOVEL, including ones with a
        # named MIBiG KCB hit. A novelty claim is the headline result a thesis most wants; absent
        # inputs must yield UNDETERMINED, not the claim.
        product_novelty = "UNDETERMINED"

    from collections import Counter
    role_counts = dict(Counter(roles))
    return {
        "n_genes": n,
        "function": {
            "role_counts": role_counts,
            "characterized_fraction": round((n - unchar_n) / n, 2),
            "pct_uncharacterized": pct_unchar,
            "high_confidence_genes": sum(1 for g in per_gene if g["confidence"] == "HIGH"),
            "per_gene": per_gene,
        },
        "gene_novelty": {
            "mean_top_hit_identity": mean_id,
            "orphans": [g["locus_tag"] for g in per_gene if g["gene_novelty"] == "ORPHAN"],
            "highly_divergent": [g["locus_tag"] for g in per_gene if g["gene_novelty"] == "HIGHLY_DIVERGENT"],
            "conserved_unknown": [g["locus_tag"] for g in per_gene
                                  if g["uncharacterized"] and (g["top_id"] or 0) >= 80],
        },
        "product_novelty": {
            "tier": product_novelty,
            "read": {
                "KNOWN_COMPOUND": "core genes match one MIBiG BGC at high id+coverage — a known compound",
                "KNOWN_CLASS": "partial/class-level MIBiG hits — known class, product not pinned",
                "NOVEL": "no characterised product match at cluster level — novel at the product level "
                         "(gene conservation does NOT make the compound known — the BGC006 lesson)",
                # v9.7.335: the cross-check inputs (kcb_top / kcb_coverage_genes) are frequently
                # absent — indeed the blastp-online parser never supplies them — and absence of a
                # characterised-reference comparison is NOT evidence of novelty. Say so plainly.
                "UNDETERMINED": "no characterised-reference cross-check was available (no KCB anchor "
                                "or coverage supplied), so product novelty was NOT assessed — this is "
                                "an absent test, not a negative result",
            }[product_novelty],
            "note": "product novelty needs a characterised-reference cross-check; BLASTp-to-nr alone "
                    "cannot decide it. KCB anchors are gated by core-gene coverage, not score.",
        },
        "claim_safety": CLAIM_SAFETY,
    }


def chunk_proteins(proteins: list[tuple[str, str]], batch_size: int = DEFAULT_BATCH
                   ) -> list[list[tuple[str, str]]]:
    """Split [(locus_tag, seq)] into submission batches per protocol §3.0/§3.1: giant proteins
    (>2500 aa) go solo; the rest fill batches of <=batch_size."""
    batch_size = min(batch_size, MAX_BATCH)
    if batch_size > SAFE_BATCH:
        _sys.stderr.write(
            f"[blastp-online] WARNING: batch-size {batch_size} exceeds SAFE_BATCH={SAFE_BATCH}. "
            f"An entire large batch has been observed to return zero alignments, which this pipeline "
            f"would otherwise record as tested-negatives. The zero-alignment guard will refuse such a "
            f"batch rather than record it. Prefer --batch-size {SAFE_BATCH}.\n")
    giants = [(lt, s) for lt, s in proteins if len(s) > GIANT_AA]
    small = [(lt, s) for lt, s in proteins if len(s) <= GIANT_AA]
    batches = [[g] for g in giants]
    # v9.7.252: close a batch when EITHER the protein count OR the residue budget would be exceeded.
    cur: list[tuple[str, str]] = []
    cur_aa = 0
    for lt, seq in small:
        n = len(seq)
        if cur and (len(cur) >= batch_size or cur_aa + n > RESIDUE_BUDGET):
            batches.append(cur)
            cur, cur_aa = [], 0
        cur.append((lt, seq))
        cur_aa += n
    if cur:
        batches.append(cur)
    return batches


def _fasta(batch: list[tuple[str, str]]) -> str:
    return "".join(f">{lt}\n{seq}\n" for lt, seq in batch)


def domains_of(feat) -> str:
    """Domain string for a CDS feature, from its antiSMASH `/sec_met_domain` qualifiers.

    v9.7.240 (P5). antiSMASH writes each qualifier as
    `PKS_KS (E-value: 6.2e-177, bitscore: 583.1, seeds: 2284, tool: rule-based-clusters)`;
    only the leading token is the domain name. Dedupes, preserves order, returns ""
    when the CDS carries none.
    """
    q = getattr(feat, "qualifiers", {}) or {}
    names: list[str] = []
    for raw in q.get("sec_met_domain", []) or []:
        name = str(raw).split("(")[0].strip()
        if name and name not in names:
            names.append(name)
    return "; ".join(names)


def reconcile(antismash_domains: str, hit_def: str) -> str:
    """Heuristic agreement call (protocol §4/§7.4). CONFIRM when an antiSMASH domain keyword
    appears in the hit definition; otherwise REFINE (a named/sharpened but consistent hit) is
    left to the author — this returns CONFIRM or REVIEW only, never a false OVERTURN.
    OVERTURN is an author judgment (the hit contradicts the call), not auto-assigned."""
    if not hit_def:
        return "NO_HIT"
    hd = hit_def.lower()
    for kw in re.split(r"[ ;,_()]+", (antismash_domains or "").lower()):
        if len(kw) >= 4 and kw in hd:
            return "CONFIRM"
    return "REVIEW"   # author decides REFINE vs OVERTURN from %id/cov + biology


def _require_biopython():
    """Biopython backs the BLAST XML parse. It's an optional extra (the `bio` extra, or the
    sapote-addons stack vendors it) because extraction-only runs don't need it — but the online
    BLASTp channel does. Give an actionable message, not a bare ImportError, if it's absent."""
    try:
        from Bio.Blast import NCBIXML
        return NCBIXML
    except ImportError as exc:
        raise RuntimeError(
            "blastp-online needs biopython to parse BLAST XML. Install the `bio` extra "
            "(pip install 'sapote-mamey[bio]') or ship the sapote-addons stack (it vendors "
            "biopython). The rest of the pipeline runs without it."
        ) from exc


def batch_shape(batch: list[tuple[str, str]]) -> str:
    """v9.7.252: describe a batch so a zero-alignment refusal reports its own cause.

    The guard added in v9.7.250 refused an all-empty batch correctly and said nothing useful about why,
    so the mechanism stayed unknown across two lineages and three reproductions. The three numbers that
    matter are the protein count, the largest protein, and the cumulative residues -- the last is the
    one the batcher was never capping. Print them at the refusal, and nobody has to guess again.
    """
    n = len(batch)
    lens = [len(s) for _, s in batch] or [0]
    return (f"n={n}, max_aa={max(lens)}, total_aa={sum(lens)}, "
            f"budget={RESIDUE_BUDGET}{' (OVER BUDGET)' if sum(lens) > RESIDUE_BUDGET else ''}")

def _zero_alignment_batch(hits: list["BlastpHit"]) -> bool:
    """True when a multi-query batch came back with zero alignments for EVERY query.

    v9.7.250. `reconcile()` maps an empty ``hit_def`` to ``NO_HIT``, so such a batch is otherwise
    written to ``<BGC>_online_blastp.csv`` as N tested-negatives -- indistinguishable from a gene that
    was genuinely queried and has no nr homolog. Those rows then feed ``conservation_median_id``, the
    input to ``NOVELTY_CONTRADICTION``. That is the v9.7.241 P7a shape (a biased subset silently arming
    the novelty guard) arriving through a different door.

    A whole batch of proteins from one BGC having no nr homolog at e<1e-5, while its sibling batches
    return 94-100% identity, is not a result. It is a transport failure. Refuse it.

    Single-protein batches (giants are submitted solo) are exempt: one gene with no homolog is an
    ordinary, and scientifically real, outcome.
    """
    if len(hits) < 2:
        return False
    return all(not (h.blastp_top_def or "").strip() for h in hits)


def parse_blast_xml(xml_text: str, batch: list[tuple[str, str]], top_n: int = 6) -> list[BlastpHit]:
    """Parse NCBI BLAST XML. Records come back in submission order (protocol §3.5) — map by
    index to the batch's locus tags; do not trust query-name round-trip. Retains the top `top_n`
    hits per gene with full stats (protocol §9: the source-organism distribution across the
    cluster is a primary evidence axis, not throwaway). Offline-testable."""
    NCBIXML = _require_biopython()
    out: list[BlastpHit] = []
    # S2/B2: a non-XML NCBI response (HTML error page, rate-limit, empty body) makes Biopython's
    # NCBIXML.parse raise ValueError before expat_parser is bound, then its finally-block references
    # the unbound var -> UnboundLocalError. Catch it here (return [] -> caller's fail-closed path) and
    # keep the real cause visible instead of a leaked UnboundLocalError.
    if not xml_text.lstrip().startswith("<?xml"):
        return out
    # v9.7.410 hostile audit: a reply carrying an internal DTD subset with ENTITY declarations
    # (billion-laughs) kept Biopython's expat busy for ~20 s at 10^6 expansions before this
    # process's expat amplification limit would have tripped. NCBI's real replies carry an
    # external DOCTYPE only, never entity declarations, so a declaration is refused outright —
    # the same fail-closed path as any other non-BLAST body.
    if "<!ENTITY" in xml_text[:65536]:
        return out
    try:
        records = list(NCBIXML.parse(io.StringIO(xml_text)))
    except Exception:
        return out
    for idx, rec in enumerate(records):
        if idx >= len(batch):
            break
        lt, seq = batch[idx]
        hit = BlastpHit(locus_tag=lt, aa_length=len(seq), antismash_domains="")
        qlen = rec.query_length or len(seq)
        for ai, a in enumerate(rec.alignments[:top_n]):
            h = a.hsps[0]
            org = re.search(r"\[([^\]]+)\]", a.hit_def)
            row = {
                "hit_def": a.hit_def.split(">")[0].strip(),
                "accession": getattr(a, "accession", "") or "",
                "organism": org.group(1) if org else "",
                "pct_identity": round(100.0 * h.identities / h.align_length, 1) if h.align_length else None,
                "pct_positive": round(100.0 * getattr(h, "positives", 0) / h.align_length, 1) if (h.align_length and getattr(h, "positives", None) is not None) else None,
                "query_coverage": round(100.0 * (h.query_end - h.query_start + 1) / qlen, 1) if qlen else None,
                "evalue": h.expect, "bitscore": h.bits,
            }
            hit.top_hits.append(row)
            if ai == 0:   # top hit populates the flat fields (back-compatible)
                hit.blastp_top_def = row["hit_def"]
                hit.blastp_accession = row["accession"]
                hit.blastp_organism = row["organism"]
                hit.pct_identity = row["pct_identity"]
                hit.pct_positive = row["pct_positive"]
                hit.query_coverage = row["query_coverage"]
                hit.evalue = row["evalue"]
                hit.bitscore = row["bitscore"]
        out.append(hit)
    return out


def cluster_coherence(hits: list[BlastpHit], core_domain_kw=("KS", "NRPS", "AMP-binding",
                                                             "Condensation", "precursor")) -> dict:
    """Protocol §9 — the three cluster-level reads from per-gene top-N hits:

      1. genome-span / syntenic-block signal — the max fraction of cluster genes any single
         source genome appears in (high → recent transfer / near-complete copy; low spread →
         old genus-conserved cluster, vertically inherited).
      2. identity distribution: catalytic core vs periphery (high-id core + lower-id shell =
         stable pathway with an evolvable regulatory shell — a believability point).
      3. genus-break / mosaic detection — contiguous runs whose top-hit genus departs from the
         cluster consensus at lower identity (candidate HGT sub-islands; flagged provisional).

    Returns a dict ready to seed §8 / §10 / §25. Never raises on sparse input."""
    scored = [h for h in hits if h.top_hits]
    n = len(scored)
    if n == 0:
        return {"n_genes": 0, "note": "no hits to analyze"}

    # 1) genome-span: how many genes list each accession's organism among their top hits
    from collections import Counter
    genome_hits = Counter()
    for h in scored:
        seen = {row["organism"] for row in h.top_hits if row["organism"]}
        for org in seen:
            genome_hits[org] += 1
    top_genome, top_genome_n = (genome_hits.most_common(1)[0] if genome_hits else ("", 0))
    span_frac = round(top_genome_n / n, 3)
    span_read = ("recent-transfer / near-complete syntenic copy" if span_frac >= 0.5
                 else "diverged genus-wide family (vertically inherited)" if span_frac <= 0.15
                 else "intermediate")

    # 2) core vs periphery identity
    def _is_core(h):
        d = (h.antismash_domains or "").upper()
        return any(kw.upper() in d for kw in core_domain_kw)
    core = [h.pct_identity for h in scored if _is_core(h) and h.pct_identity is not None]
    peri = [h.pct_identity for h in scored if not _is_core(h) and h.pct_identity is not None]
    core_mean = round(sum(core) / len(core), 1) if core else None
    peri_mean = round(sum(peri) / len(peri), 1) if peri else None

    # 3) genus-break: consensus genus, then contiguous runs departing from it at lower id
    genus_seq = [(h.locus_tag, _genus(h.blastp_organism), h.pct_identity) for h in scored]
    consensus = Counter(g for _, g, _ in genus_seq if g).most_common(1)
    consensus_genus = consensus[0][0] if consensus else ""
    breaks, run = [], []
    for lt, g, pid in genus_seq:
        if g and g != consensus_genus and (pid is not None and pid < 85):
            run.append((lt, g, pid))
        else:
            if len(run) >= 2:
                breaks.append({"range": f"{run[0][0]}–{run[-1][0]}", "n": len(run),
                               "genus": run[0][1], "mean_id": round(sum(p for _, _, p in run) / len(run), 1)})
            run = []
    if len(run) >= 2:
        breaks.append({"range": f"{run[0][0]}–{run[-1][0]}", "n": len(run), "genus": run[0][1],
                       "mean_id": round(sum(p for _, _, p in run) / len(run), 1)})

    return {
        "n_genes": n,
        "genome_span": {"top_genome": top_genome, "genes": top_genome_n, "fraction": span_frac,
                        "read": span_read},
        "identity_distribution": {"core_mean": core_mean, "periphery_mean": peri_mean,
                                  "n_core": len(core), "n_periphery": len(peri)},
        "consensus_genus": consensus_genus,
        "genus_breaks": breaks,   # candidate HGT sub-islands (provisional genes)
    }


@dataclass
class OnlineResult:
    ok: bool
    reason: str = ""
    rid: str = ""
    hits: list[BlastpHit] = field(default_factory=list)


def _post(data: dict, timeout: int = 120) -> str:
    req = urllib.request.Request(NCBI_URL, data=urllib.parse.urlencode(data).encode())
    return urllib.request.urlopen(req, timeout=timeout).read().decode()


def run_batch_online(batch: list[tuple[str, str]], *, database: str = "nr",
                     evalue: str = "1e-5", poll_seconds: int = 60,
                     max_wait_seconds: int = 600) -> OnlineResult:
    """Submit one batch to NCBI, poll, retrieve+parse. FAIL-CLOSED: any network error returns
    ok=False with a clear reason and NO fabricated hits (protocol §6). Never raises on network
    failure. In a network-restricted environment this simply reports the channel is off."""
    if not batch:
        return OnlineResult(ok=False, reason="empty batch")
    if len(batch) > MAX_BATCH:
        return OnlineResult(ok=False, reason=f"batch >{MAX_BATCH} proteins (protocol §3.0)")
    try:
        put = _post({"CMD": "Put", "PROGRAM": "blastp", "DATABASE": database,
                     "QUERY": _fasta(batch), "HITLIST_SIZE": "3", "EXPECT": evalue,
                     "tool": "SapoteMamey"})
        m = re.search(r"RID = (\S+)", put)
        if not m:
            return OnlineResult(ok=False, reason="no RID returned (NCBI submission failed)")
        rid = m.group(1)
        waited = 0
        while waited < max_wait_seconds:
            time.sleep(poll_seconds)
            waited += poll_seconds
            info = _post({"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"})
            st = re.search(r"Status=(\w+)", info)
            status = st.group(1) if st else "UNKNOWN"
            if status == "READY":
                xml = _post({"CMD": "Get", "RID": rid, "FORMAT_TYPE": "XML",
                             "ALIGNMENTS": "3", "DESCRIPTIONS": "3"})
                _hits = parse_blast_xml(xml, batch)
                if _zero_alignment_batch(_hits):
                    return OnlineResult(ok=False, rid=rid, reason=(
                        f"zero alignments for ALL {len(_hits)} queries in this batch — refusing to "
                        f"record them as tested-negatives (v9.7.250 guard). Re-run at "
                        f"--batch-size {SAFE_BATCH}."))
                return OnlineResult(ok=True, rid=rid, hits=_hits)
            if status == "FAILED":
                return OnlineResult(ok=False, rid=rid, reason="NCBI status FAILED")
            # v9.7.197: transient UNKNOWN is pending, not terminal (matches run_batches_online).
            # Keep polling until the wait budget; the loop's timeout handles a persistently-unknown RID.
        return OnlineResult(ok=False, rid=rid, reason=f"timed out after {max_wait_seconds}s")
    except Exception as exc:  # network-restricted or NCBI down — fail closed, never fabricate
        return OnlineResult(ok=False, reason=f"channel unavailable: {type(exc).__name__}: {exc}")


def _submit_batch(batch: list[tuple[str, str]], *, database: str = "nr",
                  evalue: str = "1e-5") -> OnlineResult:
    """Submit ONE batch (CMD=Put), return an OnlineResult carrying the RID only (no poll, no hits).
    Fail-closed: any network error → ok=False with a reason, never raises. This is the submit half
    of run_batch_online, split out so many batches can be in flight at once (NCBI's URL API is
    asynchronous — results persist ~24 h)."""
    if not batch:
        return OnlineResult(ok=False, reason="empty batch")
    if len(batch) > MAX_BATCH:
        return OnlineResult(ok=False, reason=f"batch >{MAX_BATCH} proteins (protocol §3.0)")
    try:
        put = _post({"CMD": "Put", "PROGRAM": "blastp", "DATABASE": database,
                     "QUERY": _fasta(batch), "HITLIST_SIZE": "3", "EXPECT": evalue,
                     "tool": "SapoteMamey"})
        m = re.search(r"RID = (\S+)", put)
        if not m:
            return OnlineResult(ok=False, reason="no RID returned (NCBI submission failed)")
        return OnlineResult(ok=True, rid=m.group(1))
    except Exception as exc:
        return OnlineResult(ok=False, reason=f"channel unavailable: {type(exc).__name__}: {exc}")


def run_batches_online(batches: list[list[tuple[str, str]]], *, database: str = "nr",
                       evalue: str = "1e-5", poll_seconds: int = 60,
                       max_wait_seconds: int = 600, submit_gap_seconds: int = 10
                       ) -> list[OnlineResult]:
    """Submit ALL batches up front (spacing Puts by submit_gap_seconds (>=10s per NCBI BLAST URL-API rules)), then
    poll the resulting RIDs together until each is READY. Because NCBI runs the searches in
    parallel on their side, total wall-clock is ~one batch's runtime instead of N×.

    Equivalent in output to calling run_batch_online per batch, but ~Nx faster for N batches.
    Fail-closed and offline-safe per protocol §6: a batch that fails to submit or times out yields
    an ok=False OnlineResult in the returned list (same order as input); nothing is ever fabricated.

    Returns one OnlineResult per input batch, in input order.
    """
    if not batches:
        return []
    # --- SUBMIT PHASE: fire every Put, collect RIDs (or per-batch failure) ---
    # Fair-use budget across runs: NCBI throttles/blocks >~100 searches/24 h per IP, and submit_gap
    # only spaces Puts WITHIN this call. Refuse up front if the durable ledger says the rolling window
    # is exhausted, and record each Put so a later run sees this one. (Inert inside pytest unless a
    # test sets MAMEY_BLAST_LEDGER.) See mamey/blast_ledger.py.
    from .blast_ledger import refuse_if_exhausted, record
    refuse_if_exhausted("ncbi", need=len(batches))
    submitted: list[OnlineResult] = []
    for i, batch in enumerate(batches):
        submitted.append(_submit_batch(batch, database=database, evalue=evalue))
        record("ncbi")
        if i < len(batches) - 1 and submit_gap_seconds:
            time.sleep(submit_gap_seconds)   # be a good citizen: one Put at a time, brief gap
    # --- POLL PHASE: round-robin the live RIDs until all READY / FAILED / timed out ---
    results: list[OnlineResult | None] = list(submitted)   # failed submits already final
    pending = [(idx, r.rid, batches[idx]) for idx, r in enumerate(submitted) if r.ok and r.rid]
    waited = 0
    try:
        _unknown_streak: dict[str, int] = {}
        while pending and waited < max_wait_seconds:
            time.sleep(poll_seconds)
            waited += poll_seconds
            still: list[tuple[int, str, list]] = []
            for idx, rid, batch in pending:
                info = _post({"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"})
                st = re.search(r"Status=(\w+)", info)
                status = st.group(1) if st else "UNKNOWN"
                if status == "READY":
                    xml = _post({"CMD": "Get", "RID": rid, "FORMAT_TYPE": "XML",
                                 "ALIGNMENTS": "3", "DESCRIPTIONS": "3"})
                    _hits = parse_blast_xml(xml, batch)
                    if _zero_alignment_batch(_hits):
                        results[idx] = OnlineResult(ok=False, rid=rid, reason=(
                            f"zero alignments for ALL {len(_hits)} queries in this batch — refusing "
                            f"to record them as tested-negatives (v9.7.250 guard). Re-run at "
                            f"--batch-size {SAFE_BATCH}."))
                    else:
                        results[idx] = OnlineResult(ok=True, rid=rid, hits=_hits)
                    _unknown_streak.pop(rid, None)
                elif status == "FAILED":
                    # only an explicit FAILED is terminal
                    results[idx] = OnlineResult(ok=False, rid=rid, reason="NCBI status FAILED")
                    _unknown_streak.pop(rid, None)
                elif status == "UNKNOWN":
                    # Patch D: transient/unparseable status is PENDING, not FAILED — NCBI briefly
                    # returns UNKNOWN for a live RID (throttling / SearchInfo not yet populated).
                    # Abandoning here loses a running search. Tolerate a bounded streak, then time out.
                    _unknown_streak[rid] = _unknown_streak.get(rid, 0) + 1
                    if _unknown_streak[rid] >= 5:
                        results[idx] = OnlineResult(ok=False, rid=rid,
                                                    reason="NCBI status UNKNOWN persisted (5 polls)")
                    else:
                        still.append((idx, rid, batch))
                else:  # WAITING / etc.
                    _unknown_streak.pop(rid, None)
                    still.append((idx, rid, batch))
            pending = still
        # any batch still pending after the wait budget → timed out
        for idx, rid, _ in pending:
            results[idx] = OnlineResult(ok=False, rid=rid,
                                        reason=f"timed out after {max_wait_seconds}s")
    except Exception as exc:  # network dropped mid-poll — fail closed for the unresolved ones
        for idx, rid, _ in pending:
            results[idx] = OnlineResult(ok=False, rid=rid,
                                        reason=f"channel unavailable: {type(exc).__name__}: {exc}")
    return [r for r in results]  # type: ignore[misc]


def plan_round(package_dir, *, full_top: int = 3, sample_per_bgc: int = 1,
               round_num: int = 1) -> dict:
    """Plan a phased BLASTp round for a whole strain, per the standing prioritization model:

      * FULL proteins for the top `full_top` BGCs (by Corrected_rank) — so the complete
        homology evidence is back BEFORE their Mode B cards are authored.
      * A SAMPLING of `sample_per_bgc` protein(s) for EVERY other BGC — including saccharides
        (a representative BLASTp can promote a saccharide the scanners would downgrade).

    Follow-up rounds deepen the sampled BGCs. This does not submit anything; it produces the
    ordered per-BGC protein plan the runner consumes (submission stays batched <=10, giants solo).
    Returns {"strain", "round", "full_bgcs", "sampled_bgcs", "batches": [...], "n_proteins"}.
    Never raises on per-BGC failure — a BGC with no loadable proteins is skipped with a note.
    """
    from pathlib import Path
    from . import modeb_template_emitter as emit

    pkg = Path(package_dir)
    triage = emit._read_triage(pkg)
    if not triage:
        return {"strain": pkg.parent.name, "round": round_num, "full_bgcs": [],
                "sampled_bgcs": [], "batches": [], "n_proteins": 0,
                "note": "no triage board CSV found"}

    ranked = emit._select_scope(pkg, triage, "all", None)          # rank order
    full_ids = ranked[:full_top]
    sampled_ids = ranked[full_top:]

    # v9.7.335: gene_context.jsonl carries has_translation + locus_tag but NEITHER "translation"
    # nor "seq", so this returned [] for every BGC and `blastp-round` planned ZERO proteins on a
    # valid sealed package — printing "0 proteins -> 0 batch(es) ... est. ~0 min" with exit 0. An
    # operator following the documented per-gene BLASTp step concluded the strain needed none.
    # The translations DO exist in the package (<strain>_proteins.faa); look there.
    _faa_cache: dict[str, str] = {}

    def _load_faa():
        if _faa_cache:
            return _faa_cache
        import glob as _glob, os as _os
        for fp in _glob.glob(_os.path.join(str(pkg), "*_proteins.faa")):
            tag, buf = None, []
            with open(fp, encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.startswith(">"):
                        if tag and buf:
                            _faa_cache.setdefault(tag, "".join(buf))
                        tag = line[1:].split()[0].split("|")[0].strip()
                        buf = []
                    elif tag:
                        buf.append(line.strip())
            if tag and buf:
                _faa_cache.setdefault(tag, "".join(buf))
        return _faa_cache

    def _proteins(bgc_id):
        rows = emit._gene_rows_for_bgc(pkg, bgc_id)
        out = []
        for r in rows:
            tr = r.get("translation") or r.get("seq") or ""
            lt = r.get("locus_tag") or r.get("lt") or ""
            if not tr and lt:
                tr = _load_faa().get(lt, "")
            if tr and lt:
                out.append((lt, tr))
        return out

    def _representative(prots):
        """Pick the sampling protein for a BGC: prefer the longest core-ish protein (a large
        protein is more likely a biosynthetic anchor that resolves/promotes the cluster)."""
        return sorted(prots, key=lambda p: -len(p[1]))[:sample_per_bgc]

    plan_proteins: list[tuple[str, str, str]] = []   # (bgc_id, locus_tag, seq)
    full_used, sampled_used = [], []
    for bid in full_ids:
        ps = _proteins(bid)
        if ps:
            full_used.append(bid)
            plan_proteins.extend((bid, lt, s) for lt, s in ps)
    for bid in sampled_ids:
        ps = _proteins(bid)
        if ps:
            sampled_used.append(bid)
            plan_proteins.extend((bid, lt, s) for lt, s in _representative(ps))

    # chunk into submission batches (<=10, giants solo) — carry the bgc_id through
    flat = [(lt, s) for _, lt, s in plan_proteins]
    batches = chunk_proteins(flat, DEFAULT_BATCH)   # v9.7.245: the courteous default, not the ceiling
    return {
        "strain": pkg.parent.name, "round": round_num,
        "full_bgcs": full_used, "sampled_bgcs": sampled_used,
        "n_proteins": len(plan_proteins),
        "n_batches": len(batches),
        "batches": batches,
        "plan": [{"bgc": b, "locus_tag": lt, "aa": len(s)} for b, lt, s in plan_proteins],
    }


def blastp_round_command(args) -> int:
    """CLI: mamey blastp-round — plan (and optionally run) a phased strain BLASTp round.
    Round 1 = full proteins for the top-N BGCs + one representative per remaining BGC (saccharides
    included). Dry-run by default (prints the plan + submission cost); --run submits fail-closed."""
    import json
    import os

    plan = plan_round(args.package, full_top=getattr(args, "full_top", 3),
                      sample_per_bgc=getattr(args, "sample_per_bgc", 1),
                      round_num=getattr(args, "round_num", 1))
    if plan.get("note"):
        emit(f"[blastp-round] {plan['note']}")
        return 1

    emit(f"[blastp-round] {plan['strain']} · round {plan['round']}", f"[blastp-round] FULL proteins for top {len(plan['full_bgcs'])} BGC(s): {', '.join(plan['full_bgcs']) or '—'}", f"[blastp-round] +1 representative for {len(plan['sampled_bgcs'])} other BGC(s) (saccharides included)", f"[blastp-round] {plan['n_proteins']} proteins -> {plan['n_batches']} batch(es) (<=10/batch, giants solo)", sep="\n")

    outdir = getattr(args, "outdir", None) or os.path.join(str(args.package), "bgc_blastp_panel")
    os.makedirs(outdir, exist_ok=True)
    plan_path = os.path.join(outdir, f"round{plan['round']}_plan.json")
    with open(plan_path, "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in plan.items() if k != "batches"}, fh, indent=2)
    emit(f"[blastp-round] plan -> {plan_path}")

    if not getattr(args, "run", False):
        est = plan["n_batches"] * 2.5
        emit(f"[blastp-round] DRY RUN. Est. ~{est:.0f} min at ~2.5 min/batch. "
              f"Re-run with --run to submit (fail-closed; never fabricates).")
        return 0

    # --run: submit ALL batches, then poll together (async; ~Nx faster than serial). Fail-closed.
    all_hits, unavailable = [], False
    results = run_batches_online(plan["batches"], database=getattr(args, "database", "nr"),
                                 evalue=getattr(args, "evalue", "1e-5"))
    for bi, res in enumerate(results, 1):
        if not res.ok:
            emit(f"[blastp-round] batch {bi}: {res.reason}")
            unavailable = True
            continue
        emit(f"[blastp-round] batch {bi}: RID {res.rid}, {len(res.hits)} hits")
        all_hits.extend(res.hits)
    if unavailable and not all_hits:
        emit("[blastp-round] ONLINE CHANNEL UNAVAILABLE — plan saved; submit where NCBI is "
              "reachable. No hits fabricated.")
        return 2
    emit(f"[blastp-round] {len(all_hits)} hits across the round.")
    return 0


def _find_crosswalk(args) -> dict | None:
    """Load `*_2b_bgc_crosswalk.csv` → {bgc_id: row}. Resolution order (Patch B v9.7.196 fix):
    1. explicit --crosswalk (a CSV path or a package dir);
    2. --package if it's a package dir (or its parent / a `*/package` sibling if it's a ZIP).
    Returns None when no crosswalk is found (caller then refuses a --bgc scope rather than crash).
    Never raises."""
    import csv as _csv

    def _load(csv_path) -> dict | None:
        try:
            with open(csv_path, encoding="utf-8-sig") as _fh:  # BLAST-P07: with-block (was a bare open handle leak)
                rows = list(_csv.DictReader(_fh))
            return {str(r.get("bgc_id", "")).strip(): r for r in rows if r.get("bgc_id")}
        except Exception:
            return None

    def _search(d: Path) -> dict | None:
        for cand in (d, d.parent, d / "package", d.parent / "package"):
            try:
                hits = list(cand.glob("*_2b_bgc_crosswalk.csv"))
            except Exception:
                hits = []
            if hits:
                return _load(hits[0])
        return None

    # 1. explicit --crosswalk
    xw = getattr(args, "crosswalk", None)
    if xw:
        xp = Path(xw)
        if xp.is_file():
            return _load(xp)
        if xp.is_dir():
            got = _search(xp)
            if got is not None:
                return got
    # 2. derive from --package
    pkg = getattr(args, "package", None)
    if not pkg:
        return None
    return _search(Path(pkg))


def _derive_kcb_anchor(args) -> tuple[str, int | None]:
    """Resolve the (kcb_top, kcb_coverage_genes) cross-check inputs for function_and_novelty.

    v9.7.338 (BLP-02): these were read via getattr(args, "kcb_top"/"kcb_coverage_genes") from
    argparse destinations that never existed, so product-novelty was permanently UNDETERMINED
    on every real run — even for a cluster with a named MIBiG anchor. Resolution order:
      1. explicit --kcb-top / --kcb-coverage-genes;
      2. auto-derive from the sealed package's per-gene MIBiG profile (`*_3_mibig_profile.csv`,
         the PRIMARY convergence layer): `dominant_mibig_compound` (fallback
         `dominant_mibig_accession`) as the anchor label and `dominant_distinct_query_genes` as
         the coverage-gene count for --bgc.
    Auto-derivation only applies when scoping a single --bgc against a sealed package; a bare
    region GBK with no anchor context stays UNDETERMINED (the claim-safe absent-test read).
    Never raises."""
    kcb_top = getattr(args, "kcb_top", None) or ""
    cov = getattr(args, "kcb_coverage_genes", None)
    if kcb_top and cov is not None:
        return kcb_top, cov
    bgc = getattr(args, "bgc", None)
    if not bgc:
        return kcb_top, cov
    import csv as _csv
    roots: list[Path] = []
    for attr in ("crosswalk", "package"):
        p = getattr(args, attr, None)
        if p:
            pp = Path(p)
            roots += [pp, pp.parent, pp / "package", pp.parent / "package"]
    prof = None
    for root in roots:
        try:
            hits = list(root.glob("*_3_mibig_profile.csv"))
        except Exception:
            hits = []
        if hits:
            prof = hits[0]
            break
    if prof is None:
        return kcb_top, cov
    try:
        with open(prof, encoding="utf-8-sig") as fh:
            for r in _csv.DictReader(fh):
                if str(r.get("bgc_id", "")).strip() != str(bgc).strip():
                    continue
                if not kcb_top:
                    kcb_top = (r.get("dominant_mibig_compound") or
                               r.get("dominant_mibig_accession") or "").strip()
                if cov is None:
                    try:
                        cov = int(float(r.get("dominant_distinct_query_genes") or 0)) or None
                    except (TypeError, ValueError):
                        cov = None
                break
    except Exception:
        pass
    return kcb_top, cov


def _scope_feats(feats, bgc=None, region=None, crosswalk=None):
    """Scope CDS features to a region by contig + coordinate window. Grounded on the antiSMASH
    locator (contig + start/end from the crosswalk), never on the ungrounded global BGC number.
    Returns [] on an unresolved locator so the caller can refuse rather than submit a whole proteome."""
    contig = None
    win = None
    if bgc and crosswalk and bgc in crosswalk:
        row = crosswalk[bgc]
        contig = (row.get("contig") or "").strip()
        try:
            win = (int(float(row["start"])), int(float(row["end"])))
        except Exception:
            win = None
    elif region:
        contig = str(region).strip()
    if not contig:
        return []
    out = []
    # v9.7.329 (SM-P-031): the sealed crosswalk `contig` can carry a mangled coverage decimal
    # (leading-zero drop, e.g. real NODE_49_length_57614_cov_34.087283 recorded as ...cov_34.87283).
    # The raw substring match below then never matches the true feature contig, so the BGC scopes to
    # [] — the same value used for "unresolved locator" — and the whole BGC is silently skipped
    # (observed live on AS-XXX BGC060/BGC058 -> 0 genes). Match on the stable NODE_<n>_length_<L> key
    # (strip the trailing _cov_<float> tail) first; keep the raw substring test as a fallback.
    def _node_key(c):
        return re.sub(r"_cov_[0-9.]+.*$", "", str(c or ""))
    ckey = _node_key(contig)
    for f in feats:
        fc = str(getattr(f, "contig", "") or "")
        fk = _node_key(fc)
        if fk != ckey and ckey not in fk and contig not in fc:
            continue
        if win and getattr(f, "start", None) is not None and getattr(f, "end", None) is not None:
            if f.end < win[0] or f.start > win[1]:
                continue
        out.append(f)
    return out


def blastp_online_command(args) -> int:
    """CLI: mamey blastp-online. Fail-closed and offline-safe. Emits the §4 CSV when hits
    return; prints a clear unavailable banner otherwise (never fabricates)."""
    import os
    from .parsers import extract_cds_features

    # Patch B (v9.7.196 fix): extract_cds_features raises on a sealed package dir (no GenBank protein
    # records). The command needs proteins from a ZIP/region-GBK; a package dir supplies only the
    # crosswalk. Fail soft to [] so the two-source resolution below (proteins from ZIP + crosswalk
    # from the sibling package) can proceed, and the guard/refuse path stays reachable.
    try:
        feats = extract_cds_features(args.package) if hasattr(args, "package") else []
    except Exception:
        feats = []
    # v9.7.185 P7: --bgc/--region previously affected only the output filename, so a genome + --bgc
    # BGC001 submitted the ENTIRE proteome to NCBI. Scope to the named region, and refuse an
    # oversized unscoped submission.
    # v9.7.196 (Patch B): resolve --bgc to a contig + coordinate window via the sealed crosswalk,
    # NOT by string-transforming the ungrounded global BGC number. On a full-genome multi-region ZIP
    # the old `BGC006 -> region006` token matched nothing (regions are per-contig; source_gbk is
    # empty on the features; contig strings carry no regionNNN), so scoping silently failed and the
    # whole proteome was submitted (→ guard refused). Ground scoping on the antiSMASH locator.
    _bgc = getattr(args, "bgc", None)
    _region = getattr(args, "region", None)  # a real NODE·contig / regionNNN locator, if given
    if _bgc or _region:
        _xwalk = _find_crosswalk(args)
        _scoped = _scope_feats(feats, bgc=_bgc, region=_region, crosswalk=_xwalk)
        if _scoped:
            feats = _scoped
        elif _bgc and _xwalk is None:
            emit("[blastp-online] --bgc needs the sealed package crosswalk to resolve to a "
                  "contig+region window; pass --package <package_dir> (not a bare ZIP), or a single "
                  "region GBK as --package, or use --region <NODE…regionNNN>.")
            return 1
        # else: locator given but unresolved → fall through; the unscoped guard below refuses.
    proteins = [((f.locus_tag or f"cds_{i}"), f.translation) for i, f in enumerate(feats) if f.translation]
    import os as _os2
    _UNSCOPED_GUARD = int(_os2.environ.get("MAMEY_BLASTP_MAX_UNSCOPED", "200"))
    if len(proteins) > _UNSCOPED_GUARD:
        emit(f"[blastp-online] REFUSING: {len(proteins)} proteins would be submitted to NCBI "
              f"unscoped (guard={_UNSCOPED_GUARD}). Add --bgc <BGC_ID> (or --region) to scope a full "
              f"ZIP to one BGC's proteins, pass a single region GBK as --package, or raise "
              f"MAMEY_BLASTP_MAX_UNSCOPED if intentional.")
        return 1
    if not proteins:
        emit("[blastp-online] no CDS translations found (need an antiSMASH region GBK/ZIP)")
        return 1

    _bs = getattr(args, "batch_size", DEFAULT_BATCH)
    batches = chunk_proteins(proteins, _bs)
    # v9.7.250: the banner printed the MAX_BATCH constant, not the argument actually used, so
    # `--batch-size 10` announced "<= 30/batch". A log that cannot tell you what was submitted made
    # the zero-alignment defect meaningfully harder to see.
    _widest = max((len(b) for b in batches), default=0)
    emit(f"[blastp-online] {len(proteins)} proteins -> {len(batches)} batch(es) "
          f"(requested {_bs}/batch, widest batch {_widest}, hard cap {MAX_BATCH}, giants solo). "
          f"Channel is fail-closed + offline-safe.")
    # Token-friendly route reminder: live polling is ~1-2 min/query. If NCBI BLAST results already
    # exist (hit-table CSV [+ Alignment XML]), `mamey ingest-blastp --hit-table … [--xml …] --package …`
    # writes the same <BGC>_online_blastp.csv panel with ZERO network. This live path is for when no
    # pre-run results exist.
    emit("[blastp-online] note: to skip live polling, pre-run NCBI BLAST and ingest the hit-table "
          "offline via `mamey ingest-blastp --hit-table <hits.csv> [--xml <aln.xml>] --package <pkg>` "
          "(same panel, no network wait).")

    all_hits: list[BlastpHit] = []
    unavailable = False
    # submit ALL batches, then poll together (async; ~Nx faster than serial). Fail-closed.
    results = run_batches_online(batches, database=getattr(args, "database", "nr"),
                                 evalue=getattr(args, "evalue", "1e-5"))
    for bi, res in enumerate(results, 1):
        if not res.ok:
            emit(f"[blastp-online] batch {bi}: {res.reason}")
            unavailable = True
            continue
        emit(f"[blastp-online] batch {bi}: RID {res.rid}, {len(res.hits)} hits")
        all_hits.extend(res.hits)

    if unavailable and not all_hits:
        emit("[blastp-online] ONLINE CHANNEL UNAVAILABLE — author the card from antiSMASH+KCB "
              "with the unverified banner (protocol §6). No hits fabricated.")
        return 2

    # v9.7.240 (P5): parse_blast_xml constructs every BlastpHit with antismash_domains=""
    # (the BLAST XML carries no domain info) and nothing ever filled it in. Consequences,
    # all observed on the real AS-XXX BGC041 run (45 proteins):
    #   * the CSV's `antismash_domains` column was empty on every row;
    #   * reconcile("", hit_def) can only return REVIEW -- the `agreement` column was a
    #     constant, not a reconciliation, so §4's CONFIRM/REFINE/OVERTURN triage had no input;
    #   * cluster_coherence()._is_core matches on domain keywords, so n_core was always 0
    #     and identity_distribution.core_mean always null -- the §9 core-vs-periphery read
    #     silently degraded to "0 core genes" on every cluster ever analysed.
    # The CDS features we submitted carry /sec_met_domain. Backfill by locus_tag, before
    # any consumer reads the field.
    _dom_by_lt = {(f.locus_tag or ""): domains_of(f) for f in feats if getattr(f, "locus_tag", None)}
    for _h in all_hits:
        if not _h.antismash_domains:
            _h.antismash_domains = _dom_by_lt.get(_h.locus_tag, "")

    outdir = getattr(args, "outdir", None) or os.getcwd()
    os.makedirs(outdir, exist_ok=True)
    out_csv = os.path.join(outdir, f"{(getattr(args, 'bgc', None) or getattr(args, 'region', None) or 'region')}_online_blastp.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        # v9.7.410 (CLAUDE_410_r7 export-injection): route through SafeWriter, NOT a bare
        # csv.writer. This is a *computed* 13-column §4 panel — blastp_top_def / blastp_organism
        # are free text copied verbatim from a public GenBank record's hit_def / organism (an
        # attacker-influenceable field). A hit_def of "=1+1" would otherwise land a live formula
        # in the CSV. csv_safety.py's docstring listed this file among the byte-faithful raw
        # captures (blastp_ebi/ebi_xml_to_outfmt10) exempt from the guard; that note does NOT
        # apply to this table and the exemption is no longer honoured here.
        w = _SafeWriter(fh)
        # BGC node.region locator (cov-stripped, matching the GCF context table) — constant per BGC.
        _xw = _find_crosswalk(args)
        _bgc_id = getattr(args, "bgc", None)
        node_region = ""
        if _xw and _bgc_id and _bgc_id in _xw:
            _r = _xw[_bgc_id]
            _nid = re.sub(r"_cov_[0-9.]+", "", (_r.get("node_id") or _r.get("contig") or "").strip())
            _reg = (_r.get("antismash_region") or "").strip()
            node_region = f"{_nid}.{_reg}" if (_nid and _reg) else _nid
        w.writerow(["locus_tag", "node_region", "aa_length", "antismash_domains", "blastp_top_def",
                    "blastp_accession", "blastp_organism", "pct_identity", "pct_positive", "query_coverage",
                    "evalue", "bitscore", "agreement"])
        for h in all_hits:
            w.writerow([h.locus_tag, node_region, h.aa_length, h.antismash_domains, h.blastp_top_def,
                        h.blastp_accession, h.blastp_organism, h.pct_identity, h.pct_positive, h.query_coverage,
                        h.evalue, h.bitscore, h.agreement or reconcile(h.antismash_domains, h.blastp_top_def)])
    emit(f"[blastp-online] wrote {out_csv} ({len(all_hits)} rows). {CLAIM_SAFETY}")

    # protocol §9 + function/novelty: the cluster-level reads that belong in §8/§10/§25/§29
    coherence = cluster_coherence(all_hits)
    # v9.7.338 (BLP-02): resolve the product-novelty cross-check inputs (explicit flags, else
    # auto-derived from the sealed per-gene MIBiG profile) instead of reading argparse dests that
    # never existed — otherwise product_novelty is permanently UNDETERMINED even with a KCB anchor.
    _kcb_top, _kcb_cov = _derive_kcb_anchor(args)
    fn = function_and_novelty(all_hits, kcb_top=_kcb_top, kcb_coverage_genes=_kcb_cov)
    import json as _json
    reads_path = os.path.join(outdir, f"{(getattr(args, 'bgc', None) or getattr(args, 'region', None) or 'region')}_cluster_reads.json")
    with open(reads_path, "w", encoding="utf-8") as fh:
        _json.dump({"coherence": coherence, "function_and_novelty": fn}, fh, indent=2)
    if coherence.get("genome_span"):
        gs = coherence["genome_span"]
        emit(f"[blastp-online] §9 coherence: genome-span {gs['genes']}/{coherence['n_genes']} "
              f"({gs['read']}); core {coherence['identity_distribution']['core_mean']}% vs "
              f"periphery {coherence['identity_distribution']['periphery_mean']}%")
        if coherence["genus_breaks"]:
            emit(f"[blastp-online] §9 mosaic islands (provisional): "
                  f"{', '.join(b['range'] for b in coherence['genus_breaks'])}")
    if fn.get("product_novelty"):
        emit(f"[blastp-online] product novelty: {fn['product_novelty']['tier']} — "
              f"{fn['product_novelty']['read']}")
        gn = fn.get("gene_novelty", {})
        if gn.get("orphans") or gn.get("highly_divergent"):
            emit(f"[blastp-online] gene novelty: {len(gn.get('orphans', []))} orphan, "
                  f"{len(gn.get('highly_divergent', []))} highly-divergent genes")
    emit(f"[blastp-online] cluster reads -> {reads_path}")
    return 0
