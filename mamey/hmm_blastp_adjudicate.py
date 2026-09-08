"""hmm_blastp_adjudicate — the intrinsic-structure HMM channel, reconciled with extrinsic BLASTp.

Now that per-gene BLASTp leads Mode B annotation (extrinsic identity: which named protein, which
organism, how novel), the offline HMM channel is demoted from primary annotation to the specific
jobs BLASTp structurally cannot do (intrinsic structure):

  1. Sub-gene domain architecture + ORDER — BLASTp gives one alignment over a whole protein; it
     says "a type I PKS" but not the module grammar (KS-AT-DH-KR-ACP, how many modules). Profile
     HMMs tile the protein into ordered domains. This is what dissolves a megasynthase-trap call
     (single module, no chain-extension partners).
  2. Short / divergent things BLASTp misses — RiPP precursors, leader motifs, small modifiers, and
     "orphan" genes with no nr hit. An HMM hit can rescue a family assignment where homology search
     comes up empty.
  3. ADJUDICATION of BLASTp reconciliation disagreements — when BLASTp overturns an antiSMASH call
     (β-lactamase -> esterase), the tie-breaker is the domain signature: does the protein carry the
     α/β-hydrolase catalytic motif or the β-lactamase fold? HMM settles description-vs-Pfam splits.
  4. Deterministic, offline, quantitative floor — pyHMMER + scanner_pfam.hmm runs offline in
     seconds with reproducible bitscores; it never depends on NCBI being reachable. This is the
     channel the engine can run in CI against the CCTT bitscore floors.

Clean division: HMM = what the machine IS (intrinsic, offline, deterministic); BLASTp = whose
machine it is most like and whether the product is known (extrinsic, online, contextual). A Mode B
card wants both reconciled. This module supplies the HMM side and the adjudication.

Uses the bundled pyHMMER engine via bgc_walk; degrades cleanly if pyhmmer / the HMM db are absent.
"""

from __future__ import annotations

import re

# keyword -> the HMM/domain-name tokens whose presence supports that functional call. Used to
# adjudicate a BLASTp-vs-antiSMASH disagreement by asking which call the domain signature backs.
# v9.7.232 (patch-chat, a cohort HMM census, item-2): expanded from the original 7-family early
# set. The original set returned AMBIGUOUS for many real gene-level checks on RiPP/lasso
# leads purely because the vocabulary was missing (lanthipeptide dehydratase, LanC cyclase, ABC
# transporter, asparagine synthase, relaxase, transposase, HTH regulators, etc.) -- see
# NO_SIGNATURE_DICT below, which now distinguishes "no dictionary entry" from a real disagreement.
_SIGNATURE_TOKENS = {
    "esterase": ("abhydrolase", "abhydro", "alpha_beta", "ab_hydrolase", "esterase", "lipase"),
    "hydrolase": ("abhydrolase", "abhydro", "alpha_beta", "ab_hydrolase", "hydrolase"),
    "beta-lactamase": ("beta-lactamase", "lactamase", "beta_lactam", "transpeptidase"),
    "ferritin": ("ferritin", "rubrerythrin", "bacterioferritin"),
    "p450": ("p450",),
    "methyltransferase": ("methyltransf", "_mt", "ubie", "cmas", "mtase", "pcmt"),
    "rieske": ("rieske",),
    "acetyltransferase": ("acetyltransf", "hexapep", "at_", "nat"),
    # -- lanthipeptide / RiPP (added from RiPP/lanthipeptide adjudication cards) --
    "lantibiotic dehydratase": ("lant_dehydr", "lanthipeptide_lanb", "lanb"),
    "lanthipeptide dehydratase": ("lant_dehydr", "lanthipeptide_lanb", "lanb"),
    "lanthionine synthetase": ("lanc_like", "lanc"),
    "lasso peptide": ("transglut_core", "asn_synthase"),
    "lasso": ("transglut_core", "asn_synthase"),
    # -- transport (added from AS-XXX BGC028) --
    "abc transporter": ("abc_tran", "abc2_membrane", "bpd_transp"),
    "mfs transporter": ("mfs_1",),
    # -- mobile-element genes (added from AS-XXX BGC043/BGC028 relaxase/transposase finding) --
    "relaxase": ("trwc", "mobf", "aaa_30", "relaxase"),
    "mobilization": ("trwc", "mobf", "relaxase", "mob"),
    "transposase": ("tnsa", "transpos"),
    # -- regulators (added from AS-XXX census; generic, catches most HTH-superfamily calls) --
    "regulatory protein": ("tpr_", "hth_", "gere", "lysr", "tetr", "marr", "response_reg"),
    "transcriptional regulator": ("hth_", "gere", "lysr", "tetr", "marr"),
    "helix-turn-helix": ("hth_", "gere"),
    # -- other frequent AS-XXX rescue-set families worth having an entry for --
    "asparagine synthase": ("asn_synthase",),
    "oxidoreductase": ("pyr_redox", "nad_binding", "fad_binding", "amino_oxidase", "adh_short"),
    "nudix": ("nudix",),
    "chaperone": ("mbth",),
}


def _tokens_for(text: str) -> tuple:
    t = (text or "").lower()
    for kw, toks in _SIGNATURE_TOKENS.items():
        if kw in t:
            return toks
    return ()


def resolve_hmm_db(package_dir=None):
    """Locate the scanner HMM database (delegates to the bundle's resolver if present)."""
    try:
        from .wheelhouse import resolve_hmm_database
        return resolve_hmm_database()
    except Exception:
        from pathlib import Path
        for c in ("Wheelhouse/hmm/scanner_pfam.hmm",):
            p = Path(c)
            if p.exists():
                return str(p)
    return None


def walk_domains(region_gbk, hmm_file=None):
    """Ordered per-gene HMM domain readout with bitscores (role 1). Thin wrapper over bgc_walk that
    returns {locus_tag: [(pos, hmm_name, bitscore), ...]} plus the ordered gene list. Returns
    ({}, [], reason) if the HMM channel is unavailable — never raises."""
    if not hmm_file:
        # v9.7.207 (item-1 bug): resolve_hmm_db() returns a dict {path, n_models_hint, tier, reason},
        # not a path — handing the dict to the pyhmmer loader raised AttributeError('dict' … 'readable').
        _db = resolve_hmm_db()
        hmm_file = (_db.get("path") if isinstance(_db, dict) else _db)
    if not hmm_file:
        return {}, [], "no HMM database available (ship the scanner HMM in Wheelhouse/hmm/ or the addon)"
    try:
        from .bgc_walk import bgc_walk
        genes, hits_by_gene = bgc_walk(region_gbk, hmm_file)
        return hits_by_gene, genes, ""
    except ImportError as exc:
        # #4 (v9.7.216): the real missing dep is often biopython (Bio import in bgc_walk), not pyhmmer —
        # name the actual module rather than always blaming pyhmmer (that mislabel cost real debug time).
        missing = getattr(exc, "name", None) or "a dependency"
        return {}, [], f"{missing} not installed (ship the sapote-addons stack: needs pyhmmer + biopython)"
    except Exception as exc:
        return {}, [], f"HMM walk failed: {type(exc).__name__}: {exc}"


def module_architecture(hits_by_gene, locus_tag):
    """Role 1: the ordered domain grammar for one gene (e.g. 'KS -> AT -> DH -> KR -> ACP'), and a
    module count for PKS/NRPS. Answers 'single module, no chain-extension partners?' — the
    megasynthase-trap discriminator BLASTp can't resolve."""
    doms = [nm for _, nm, _ in sorted(hits_by_gene.get(locus_tag, []))]
    ks_like = sum(1 for d in doms if re.search(r"\bKS\b|ketoacyl|C_KS", d, re.I))
    c_like = sum(1 for d in doms if re.search(r"condensation|\bC\b|Cglyc", d, re.I))
    return {
        "locus_tag": locus_tag,
        "domain_order": doms,
        "n_domains": len(doms),
        "ks_modules": ks_like,
        "c_modules": c_like,
        "single_module": (ks_like <= 1 and c_like <= 1 and len(doms) >= 1),
    }


def adjudicate(hits_by_gene, locus_tag, antismash_call: str, blastp_call: str) -> dict:
    """Role 3: settle a BLASTp-vs-antiSMASH disagreement by the domain signature. Returns which
    call the HMM evidence supports (or NEITHER/INSUFFICIENT), with the supporting domain names.

    verdict:
      SUPPORTS_BLASTP   — HMM carries the signature the BLASTp call implies (β-lactamase→esterase
                          adjudicated: the protein has the α/β-hydrolase motif, not a lactamase fold)
      SUPPORTS_ANTISMASH— HMM backs the original antiSMASH call instead
      AMBIGUOUS         — both or neither signature present at the domain level
      INSUFFICIENT      — no HMM hits on this gene (can't adjudicate; defer to BLASTp %id/cov)"""
    doms = [nm.lower() for _, nm, _ in hits_by_gene.get(locus_tag, [])]
    if not doms:
        return {"locus_tag": locus_tag, "verdict": "INSUFFICIENT",
                "reason": "no HMM domain hits on this gene", "supporting": []}
    as_toks = _tokens_for(antismash_call)
    bp_toks = _tokens_for(blastp_call)
    # v9.7.232 (patch-chat, AS-XXX HMM census, item-2): neither call term maps to ANY dictionary
    # entry -> we have no basis to adjudicate at all. This used to fall through to AMBIGUOUS,
    # which is indistinguishable in output from a genuine both-or-neither disagreement. On AS-XXX
    # this was 16/18 of all adjudicate() calls -- all real agreements the dictionary simply had no
    # vocabulary for (lanthipeptide dehydratase, ABC transporter, etc., before this patch's token
    # additions). Surface it as its own verdict so AMBIGUOUS stops being overloaded.
    if not as_toks and not bp_toks:
        return {"locus_tag": locus_tag, "verdict": "NO_SIGNATURE_DICT", "supporting": [],
                "reason": (f"neither antiSMASH call ({antismash_call!r}) nor BLASTp call "
                           f"({blastp_call!r}) matches any _SIGNATURE_TOKENS entry -- this is not "
                           f"evidence of disagreement, just missing dictionary coverage; extend "
                           f"_SIGNATURE_TOKENS if this class recurs")}
    as_hit = [d for d in doms if any(t in d for t in as_toks)] if as_toks else []
    bp_hit = [d for d in doms if any(t in d for t in bp_toks)] if bp_toks else []
    if bp_hit and not as_hit:
        return {"locus_tag": locus_tag, "verdict": "SUPPORTS_BLASTP", "supporting": bp_hit,
                "reason": f"domain signature matches the BLASTp call ({blastp_call})"}
    if as_hit and not bp_hit:
        return {"locus_tag": locus_tag, "verdict": "SUPPORTS_ANTISMASH", "supporting": as_hit,
                "reason": f"domain signature matches the antiSMASH call ({antismash_call})"}
    if as_hit and bp_hit:
        return {"locus_tag": locus_tag, "verdict": "AMBIGUOUS", "supporting": as_hit + bp_hit,
                "reason": "both signatures present at the domain level"}
    return {"locus_tag": locus_tag, "verdict": "AMBIGUOUS", "supporting": [],
            "reason": "dictionary has an opinion but neither signature was found among this "
                      "gene's actual HMM domains; defer to BLASTp %id/cov"}


def orphan_rescue(hits_by_gene, blastp_hits, as_domains=None) -> list:
    """Role 2: report any HMM family hit that rescues a family assignment where another channel
    came up empty. blastp_hits = {locus_tag: has_hit(bool)}.

    v9.7.232 (patch-chat, AS-XXX HMM census, item-1): originally triggered ONLY on "no BLASTp
    hit" -- but antiSMASH's own sec_met_domain field is scoped to core biosynthetic genes by
    design, so a gene can have a perfectly good BLASTp hit (organism + product name) and STILL
    lack any structured domain-family detail (transporter subfamily, regulator family, RiPP
    chaperone) that only this HMM channel supplies. On AS-XXX (820 CDS, 64 BGCs) this undercounted
    155 genuinely rescuable genes down to whatever subset also happened to lack a BLASTp hit.

    `as_domains` is optional and backward-compatible: pass {locus_tag: has_antismash_domain(bool)}
    to ALSO rescue genes that have a BLASTp hit but no antiSMASH domain call. Omit it (default
    None) to reproduce the original blastp-only behaviour exactly, unchanged.
    """
    rescued = []
    for lt, doms in hits_by_gene.items():
        if not doms:
            continue
        no_blastp = not blastp_hits.get(lt, False)
        no_as_domain = (as_domains is not None) and (not as_domains.get(lt, True))
        if not (no_blastp or no_as_domain):
            continue
        best = max(doms, key=lambda d: d[2])
        if no_blastp and no_as_domain:
            note = "no BLASTp hit and no antiSMASH domain call; HMM is the only functional signal"
        elif no_blastp:
            note = "no BLASTp hit; HMM rescues a family-level assignment"
        else:
            note = ("BLASTp hit present but antiSMASH left the domain field blank (expected for "
                    "non-core genes); HMM adds structured family detail BLASTp free text doesn't")
        rescued.append({"locus_tag": lt, "hmm_family": best[1], "bitscore": best[2], "note": note})
    return rescued


# domain-name regexes for the two catalytic module families the trap check cares about.
_KS_LIKE = re.compile(r"\bks\b|ketoacyl|pks_ks|c_ks", re.I)
_C_LIKE = re.compile(r"condensation|\bc_\b|cglyc|\bc-dom", re.I)
# antiSMASH product tokens that imply a genuine multi-extension assembly line (repeat-module
# expectation). Single-module classes (nrps-like, other, etc.) are deliberately excluded.
_MULTI_MODULE_PRODUCTS = re.compile(r"t1pks|transat-pks|\bnrps\b(?!-like)", re.I)


def region_module_census(region_genes, product_label) -> dict:
    """Role 1, done at the CORRECT scope. v9.7.232 (patch-chat, AS-XXX HMM census, item-3):
    replaces a same-session gene-level attempt that wrongly flagged ordinary single-module NRPS
    proteins (one Condensation-AMP_binding-PP_binding gene is NORMAL biology, not a trap -- most
    multi-module NRPS assembly lines are built from several single-module proteins in series, not
    one giant multi-module protein).

    The real megasynthase-trap question the module's docstring describes is REGION-level: does a
    BGC labelled as a genuine multi-extension polyketide/NRPS assembly line (T1PKS, transAT-PKS,
    or NRPS -- not NRPS-like) actually contain more than one chain-extension catalytic domain
    ANYWHERE in the region, or does the whole locus rest on a single isolated KS/C domain dressed
    up by a misleading product label?

    region_genes: list of {"lt":..., "hmm_domains":[(pos,name,score),...]} for every gene in ONE
    antiSMASH region (not the whole strain -- caller scopes this).
    product_label: the antiSMASH `products` string for that region, e.g. "PKS; T1PKS".

    Returns {"n_genes", "n_ks_domains", "n_c_domains", "expects_multi_module", "trap_suspect",
    "reason"}. trap_suspect is only ever True when expects_multi_module is True AND the region-wide
    catalytic domain count is <=1 -- a single-module NRPS-only region never triggers this by
    construction, unlike the retracted gene-level check.
    """
    n_ks = n_c = 0
    for g in region_genes:
        doms = [nm for _, nm, _ in g.get("hmm_domains", [])]
        n_ks += sum(1 for d in doms if _KS_LIKE.search(d))
        n_c += sum(1 for d in doms if _C_LIKE.search(d))
    expects_multi = bool(_MULTI_MODULE_PRODUCTS.search(product_label or ""))
    total_catalytic = n_ks + n_c
    trap = expects_multi and total_catalytic <= 1
    if trap:
        reason = (f"product label {product_label!r} implies a multi-extension assembly line, but "
                  f"only {total_catalytic} chain-extension domain(s) (KS={n_ks}, C={n_c}) found "
                  f"across the whole region -- possible megasynthase trap (single isolated module "
                  f"with no chain-extension partner), or a genuinely truncated/fragmented locus")
    elif expects_multi:
        reason = f"product label implies multi-extension; {total_catalytic} domain(s) found region-wide, consistent"
    else:
        reason = "product label does not imply a multi-extension assembly line; check not applicable"
    return {"n_genes": len(region_genes), "n_ks_domains": n_ks, "n_c_domains": n_c,
            "expects_multi_module": expects_multi, "trap_suspect": trap, "reason": reason}
