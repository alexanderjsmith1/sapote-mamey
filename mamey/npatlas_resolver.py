"""NP Atlas compound-reference resolver (v9.7.186 — NP Atlas incorporation).

Purpose
-------
Enrich the compound names that KnownClusterBlast/ClusterBlast already extract per BGC with
reference-grade chemistry: npclassifier compound CLASS, molecular formula, exact mass, [M+H]+/[M+Na]+
adducts, InChIKey, and the primary literature reference (DOI/PMID).

Design rationale (why this shape, not a genus-context panel)
------------------------------------------------------------
NP Atlas records *isolation provenance*, not *taxonomic distribution*. A compound like HSAF is made
by both Lysobacter and Streptomyces, but appears under a single origin genus in NP Atlas — so a
"genus precedent / cross-genus" signal built on the origin field manufactures false novelty/caution
flags and does NOT hold up (confirmed: only 3/7749 compounds even show >1 genus, an artifact of
single-origin recording). This resolver therefore makes NO genus-restriction or precedence claim.

It resolves the *compound the KCB reference already names* to its molecule-level properties, which are
organism-independent and 100% populated in the source (SMILES/InChIKey/formula/DOI = 100%, PMID = 86%).
This is immune to the HSAF problem: it enriches a similarity reference; it never asserts the BGC makes
the compound.

Claim safety
------------
- evidence_tier = INVENTORY_ONLY; claim_ceiling = "reference enrichment; compound named by the KCB
  similarity hit, NOT a product-identity claim for the BGC".
- No BGC->compound identity. No genus provenance field. No bioactivity (NP Atlas has none).
- KCB = similarity not identity — this layer enriches that reference, it does not upgrade it.
"""
from __future__ import annotations
import json, re, os, functools, warnings
from pathlib import Path
from typing import Any

# NP Atlas references ship as an ADD-ON (alongside the wheels + HMM add-on data), not inside the
# core engine zip — the full NP Atlas download is 454 MB; these phylum-filtered slices are ~15 MB
# but still belong with the optional stack. Discovery mirrors wheelhouse.resolve_hmm_database:
# env override first, then documented side-by-side add-on layouts, then a bundle-local fallback for
# self-contained cuts. If none resolve, the layer degrades to empty (no B6 rows) — never an error.
_REF_FILES = ("all_actinobacteria_npatlas_ref.json", "bacteria_nonactino_npatlas_ref.json")

# NPA-01 (v9.7.405): external_data.py documents MAMEY_NPATLAS_DIR as the dataset's env var, but this
# resolver historically read SM_NPATLAS_DIR only -- a user following the documented provisioning
# contract got an unavailable resolver. Unify on MAMEY_NPATLAS_DIR; keep SM_NPATLAS_DIR as a warned
# legacy alias for one compatibility cycle (never silently dropped -- callers who set it still work,
# they just get told to migrate).
_NPATLAS_ENV_VAR = "MAMEY_NPATLAS_DIR"
_NPATLAS_ENV_VAR_LEGACY = "SM_NPATLAS_DIR"


def _npatlas_env_dir() -> str | None:
    """Resolve the NP Atlas add-on directory from the environment. Prefers MAMEY_NPATLAS_DIR (the
    documented name in mamey/external_data.py); falls back to the legacy SM_NPATLAS_DIR with a
    one-time DeprecationWarning so an operator relying on the old name still works but is told to
    migrate. Returns None if neither is set."""
    env = os.environ.get(_NPATLAS_ENV_VAR)
    if env:
        return env
    legacy = os.environ.get(_NPATLAS_ENV_VAR_LEGACY)
    if legacy:
        warnings.warn(
            f"{_NPATLAS_ENV_VAR_LEGACY} is a deprecated alias for {_NPATLAS_ENV_VAR} and may be "
            f"removed in a future release; please set {_NPATLAS_ENV_VAR} instead.",
            DeprecationWarning, stacklevel=2,
        )
        return legacy
    return None


def _npatlas_dirs() -> list[Path]:
    """Candidate directories holding the NP Atlas add-on refs, in resolution order.

    Mirrors bundle_support/install_sapote_addons.sh's flexible wheel discovery: the add-on can arrive in several
    shapes (combined dir, split core/figures dirs, a future-renamed dir), so we (1) honor an explicit
    env override, (2) check documented fixed layouts, and (3) glob for any `npatlas/` folder under the
    add-on staging roots — so `sapote_addons_core/npatlas/`, `sm_addons/*/npatlas/`, or any addon
    `<newname>/npatlas/` are all found without another code change. Bundle-local is the last fallback.
    """
    here = Path(__file__).parent
    dirs: list[Path] = []
    env = _npatlas_env_dir()
    if env:
        dirs.append(Path(env))
    roots = [here.parent, here, here.parent.parent,
             Path("/mnt/user-data/uploads"), Path.cwd()]
    # fixed documented layouts (fast path)
    for root in roots:
        for sub in ("npatlas", "sm_addons/npatlas"):
            dirs.append(root / sub)
    # flexible glob: any addon dir carrying an npatlas/ folder (sapote_addons*, gemini_stack* back-compat, sm_addons/*)
    for root in roots:
        try:
            for cand in root.glob("*/npatlas"):
                if cand.is_dir():
                    dirs.append(cand)
            for cand in root.glob("*stack*/npatlas"):
                if cand.is_dir():
                    dirs.append(cand)
        except Exception:
            continue
    # bundle-local fallback (a self-contained cut that chose to carry the refs)
    dirs.append(here / "data" / "npatlas")
    # de-dup preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        k = str(d)
        if k not in seen:
            seen.add(k)
            out.append(d)
    return out


@functools.lru_cache(maxsize=1)
def _load_index() -> dict[str, dict[str, Any]]:
    """name(lower) -> compound record. Union of the shipped NP Atlas add-on references.

    Searches the add-on discovery paths; returns an empty index (graceful no-op) if the add-on
    isn't installed. A compound may appear under multiple origin organisms; we keep one molecule
    record per name (structure/formula/class/reference are organism-independent, so any serves).
    """
    idx: dict[str, dict[str, Any]] = {}
    seen_files: set[str] = set()
    for d in _npatlas_dirs():
        for fn in _REF_FILES:
            p = d / fn
            key = str(p.resolve()) if p.exists() else ""
            if not key or key in seen_files:
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            seen_files.add(key)
            for c in data.get("compounds", []):
                nm = str(c.get("name", "")).strip().lower()
                if nm and nm not in idx:
                    idx[nm] = c
    return idx


def npatlas_available() -> bool:
    """True if the NP Atlas add-on resolved any references (for status reporting / receipts)."""
    return len(_load_index()) > 0


# --- LQ-NPATLAS-01: npclassifier CLASS-frequency grounding for the Mode B §13 / strain S6
#     "class in Actinobacteria" sub-question. ------------------------------------------------------
# HARD claim-safety boundary (documented on this resolver): NP Atlas records isolation PROVENANCE,
# not taxonomic distribution, and carries NO bioactivity. So this exposes ONLY the organism-
# independent, aggregate npclassifier CLASS frequency across the actinobacterial records — it must
# NEVER be used for genus-precedence / "novel for this genus" claims, nor for any antifungal/
# antibacterial status. Those stay Sapote literature reasoning (confidence-tagged) and Mamey DAPR.
@functools.lru_cache(maxsize=1)
def _class_counts() -> tuple[dict[str, int], int]:
    """(-> {npclassifier_class -> n_records}, total_records) across the loaded NP Atlas index."""
    from collections import Counter
    idx = _load_index()
    c: Counter = Counter()
    for rec in idx.values():
        for cls in ((rec or {}).get("npclassifier") or {}).get("class") or []:
            if cls:
                c[str(cls)] += 1
    return dict(c), len(idx)


def class_frequency(class_name: str) -> dict | None:
    """Aggregate npclassifier CLASS frequency for `class_name` across the NP Atlas actino records,
    or None if the add-on is not installed. Organism-independent; NOT a genus or bioactivity claim."""
    if not class_name:
        return None
    counts, total = _class_counts()
    if not total:
        return None
    key = next((k for k in counts if k.lower() == class_name.strip().lower()), None)
    n = counts.get(key, 0) if key else 0
    return {
        "class": class_name,
        "n_records": n,
        "total_actino_records": total,
        "pct": round(100.0 * n / total, 2) if total else 0.0,
        "found": key is not None,
        "boundary": ("aggregate npclassifier class-frequency across NP Atlas actinobacterial "
                     "records; organism-independent; NOT genus precedence, NOT bioactivity"),
    }


def class_in_actinobacteria_sentence(class_name: str) -> str:
    """A claim-safe one-liner for the §13 / S6 'class in Actinobacteria' sub-question."""
    f = class_frequency(class_name)
    if f is None:
        return (f"_Class-in-Actinobacteria frequency unavailable_ (NP Atlas add-on not installed) "
                f"for class '{class_name}'.")
    if not f["found"]:
        return (f"Compound class '{class_name}' is **not represented** among the {f['total_actino_records']} "
                f"NP Atlas actinobacterial records (npclassifier). Aggregate class-frequency only — "
                f"not a genus or bioactivity statement.")
    return (f"Compound class '{class_name}' accounts for **{f['n_records']} of {f['total_actino_records']}** "
            f"({f['pct']}%) NP Atlas actinobacterial records (npclassifier class-frequency, organism-"
            f"independent). Not a genus-precedence or bioactivity claim.")


@functools.lru_cache(maxsize=1)
def _load_label_aliases() -> dict[str, str]:
    """Curated KCB-label -> canonical-name aliases (v9.7.187). Recovers compounds that ARE in NP
    Atlas but whose KCB label is a functional description (e.g. "heat-stable antifungal factor" ->
    "dihydromaltophilin"/HSAF). Read from the same add-on discovery paths as the index; empty dict
    if absent (graceful, no regression). Underscore-prefixed keys (notes) are ignored."""
    for d in _npatlas_dirs():
        p = d / "kcb_label_aliases.json"
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return {k.strip().lower(): str(v).strip().lower()
                        for k, v in data.items() if not k.startswith("_")}
            except Exception:
                return {}
    return {}


def _extract_compound_name(kcb_top: str) -> str | None:
    """Pull the compound name from a KCB label like 'BGC0000609.3 | nocathiacin | knowncluster'."""
    if not kcb_top or "|" not in kcb_top:
        return None
    parts = [p.strip() for p in kcb_top.split("|")]
    if len(parts) < 2:
        return None
    # the compound name is the middle field; take the first of any 'A/B' variant list
    name = parts[1].split("/")[0].strip()
    # drop trailing tokens like '(knownclusterblast)' if they leaked in
    name = re.sub(r"\(.*?\)\s*$", "", name).strip()
    return name or None


def resolve_compound(name: str) -> dict[str, Any] | None:
    """Resolve a compound name to its NP Atlas molecule record. Exact match, then conservative
    prefix match (handles 'nocobactin NA' vs catalog 'nocobactin'). Returns None if unresolved."""
    if not name:
        return None
    idx = _load_index()
    k = name.strip().lower()
    rec = idx.get(k)
    if rec is None and len(k) >= 6:
        # EVAL-P01: conservative + UNAMBIGUOUS prefix match. Both sides must be >=6 chars so a short
        # catalog name can never prefix-bind a long query (the old `k.startswith(n)` let 'actin'
        # capture 'actinomycin d'), and first-match-in-arbitrary-dict-order is gone: bind ONLY when
        # the surviving candidates are a single distinct molecule. Any ambiguity resolves to nothing —
        # never attach a different molecule's formula/mass/InChIKey to this label (claim-safety).
        matches = [r for n, r in idx.items()
                   if len(n) >= 6 and (n.startswith(k) or k.startswith(n))]
        if len(matches) == 1:
            rec = matches[0]
        elif matches:
            mol_ids = {(r.get("npaid", "") or r.get("inchikey", "")) for r in matches}
            if len(mol_ids) == 1 and next(iter(mol_ids)):  # all the same identified molecule
                rec = matches[0]
    if rec is None:
        # v9.7.187: curated KCB-label alias (functional label -> canonical chemical name). Exact
        # only; alias targets are canonical names verified present in the ref (test-enforced).
        alias = _load_label_aliases().get(k)
        if alias:
            rec = idx.get(alias)
    return rec


def compound_reference_row(strain: str, bgc_id: str, kcb_top: str, kcb_score: Any) -> dict[str, Any] | None:
    """Build one B6_Compound_Reference row for a BGC whose KCB hit names a compound.

    Returns None when the KCB label carries no compound name (nothing to resolve).
    """
    cname = _extract_compound_name(kcb_top or "")
    if not cname:
        return None
    rec = resolve_compound(cname)
    npc = (rec or {}).get("npclassifier") or {}
    ref = (rec or {}).get("reference") or {}
    return {
        "strain": strain,
        "BGC_ID": bgc_id,
        "kcb_named_compound": cname,
        "kcb_score": kcb_score if kcb_score is not None else "",
        "resolved": "YES" if rec else "NO",
        "npclassifier_pathway": "; ".join(npc.get("pathway") or []),
        "npclassifier_class": "; ".join(npc.get("class") or []),
        "mol_formula": (rec or {}).get("mol_formula", ""),
        "exact_mass": (rec or {}).get("exact_mass", ""),
        "m_plus_h": (rec or {}).get("m_plus_h", ""),
        "m_plus_na": (rec or {}).get("m_plus_na", ""),
        "inchikey": (rec or {}).get("inchikey", ""),
        "npaid": (rec or {}).get("npaid", ""),
        "primary_doi": ref.get("doi", ""),
        "primary_pmid": ref.get("pmid", ""),
        "primary_year": ref.get("year", ""),
        "evidence_tier": "INVENTORY_ONLY",
        "claim_ceiling": "reference enrichment of KCB similarity hit; NOT a BGC product-identity claim",
    }


B6_HEADERS = [
    "strain", "BGC_ID", "kcb_named_compound", "kcb_score", "resolved",
    "npclassifier_pathway", "npclassifier_class", "mol_formula", "exact_mass",
    "m_plus_h", "m_plus_na", "inchikey", "npaid",
    "primary_doi", "primary_pmid", "primary_year",
    "evidence_tier", "claim_ceiling",
]
