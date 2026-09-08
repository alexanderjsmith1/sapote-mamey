"""npatlas_structure.py — resolve a compound *name* to its known chemical STRUCTURE
(InChIKey / SMILES / formula / NPAID) from the NP Atlas add-on.

Roadmap #10 (additive, freeze-safe). This is the name-keyed companion to
``npatlas_resolver.compound_reference_row`` (which is KCB-label-keyed): a report layer
resolves a BGC's KCB/MIBiG anchor *compound name* to the structure of that KNOWN
neighbour so a card can render the *related* structure for orientation.

CLAIM SAFETY (mandatory, and deliberately tighter than the cohort reference-impl):
  * The anchor is a SIMILARITY hit; the returned structure is the structure of the
    nearest characterised compound, NEVER a claim the BGC makes that molecule.
  * We reuse ``npatlas_resolver.resolve_compound`` — the vetted, EVAL-P01-conservative
    matcher that binds ONLY an unambiguous single molecule — and add slash-candidate
    splitting ("nystatin A1/A2" -> try each real name). We intentionally DROP the
    reference-impl's ``stem``/``token`` fuzzy fallback, which could bind "…polyene A1"
    to a generic "polyene" record. A structure is attached ONLY on an exact / conservative
    / alias / slash-candidate match; anything else returns match_type="none" with empty
    fields — we never fabricate an InChIKey.
  * No bioactivity (NP Atlas carries none); no genus/organism claim.

Degrades to empty (match_type="unavailable") if the NP Atlas add-on is not installed.
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

import json
import os
import warnings
from .workspace_root import workspace_root
import re
import functools
from pathlib import Path
from typing import Any

# ---- Prefer the vetted engine resolver; fall back to a local loader for standalone runs -----------
try:  # in an installed engine
    from mamey import npatlas_resolver as _NR  # type: ignore
except Exception:  # pragma: no cover - standalone
    try:
        from . import npatlas_resolver as _NR  # type: ignore
    except Exception:
        _NR = None  # type: ignore

_REF_FILES = ("all_actinobacteria_npatlas_ref.json", "bacteria_nonactino_npatlas_ref.json")

# NPA-01 (v9.7.405): same unification as mamey/npatlas_resolver.py -- mamey/external_data.py
# documents MAMEY_NPATLAS_DIR as the dataset's env var; this standalone-fallback loader historically
# read SM_NPATLAS_DIR only. Prefer MAMEY_NPATLAS_DIR; keep SM_NPATLAS_DIR as a warned legacy alias.
_NPATLAS_ENV_VAR = "MAMEY_NPATLAS_DIR"
_NPATLAS_ENV_VAR_LEGACY = "SM_NPATLAS_DIR"


def _npatlas_env_dir() -> str | None:
    """Resolve the NP Atlas add-on directory from the environment (MAMEY_NPATLAS_DIR primary,
    SM_NPATLAS_DIR a warned legacy alias). Returns None if neither is set."""
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


def _local_npatlas_dirs() -> list[Path]:
    """Discovery paths for a standalone run (when the engine resolver isn't importable or its add-on
    isn't on the engine paths). Honors MAMEY_NPATLAS_DIR first (SM_NPATLAS_DIR as a warned legacy
    alias), then the documented Tools location."""
    dirs: list[Path] = []
    env = _npatlas_env_dir()
    if env:
        dirs.append(Path(env))
    here = Path(__file__).resolve().parent
    dirs += [
        here / "data" / "npatlas",
        here.parent / "npatlas",
        Path(str(workspace_root()) + "/Tools/databases/npatlas"),
        Path.cwd() / "Tools" / "databases" / "npatlas",
    ]
    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        k = str(d)
        if k not in seen:
            seen.add(k)
            out.append(d)
    return out


@functools.lru_cache(maxsize=1)
def _index() -> dict[str, dict[str, Any]]:
    """name(lower) -> NP Atlas record. Prefer the engine resolver's loaded index; else load locally."""
    if _NR is not None:
        try:
            idx = _NR._load_index()  # type: ignore[attr-defined]
            if idx:
                return idx
        except Exception:
            pass
    idx: dict[str, dict[str, Any]] = {}
    for d in _local_npatlas_dirs():
        for fn in _REF_FILES:
            p = d / fn
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            for c in data.get("compounds", []):
                nm = str(c.get("name", "")).strip().lower()
                if nm and nm not in idx:
                    idx[nm] = c
                syns = c.get("synonyms", "[]")
                try:
                    sl = json.loads(syns) if isinstance(syns, str) else (syns or [])
                    for s in sl:
                        sk = str(s).strip().lower()
                        if sk and sk not in idx:
                            idx[sk] = c
                except Exception:
                    pass
    return idx


def npatlas_available() -> bool:
    return len(_index()) > 0


def _conservative_lookup(name: str) -> dict[str, Any] | None:
    """Use the vetted engine matcher when present (exact + EVAL-P01 unambiguous prefix + alias);
    else a same-shaped local exact-only lookup."""
    if not name:
        return None
    if _NR is not None:
        try:
            rec = _NR.resolve_compound(name)  # type: ignore[attr-defined]
            if rec:
                return rec
        except Exception:
            pass
    return _index().get(name.strip().lower())


def _candidates(anchor: str) -> list[str]:
    """Split an anchor into real compound-name candidates: slash / semicolon variants, most specific
    first, plus the whole string. NO stemming/tokenising (claim-safety)."""
    parts = [p.strip() for p in re.split(r"[/;]", anchor or "") if p.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for c in parts + [anchor.strip()]:
        if c and c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out


def resolve_name_to_structure(anchor: str) -> dict[str, Any]:
    """Resolve a compound name/anchor to a known structure record.

    Returns a dict with keys: match_type (exact|slash|none|unavailable), matched_name, npaid,
    inchikey, smiles, mol_formula, npclassifier_class. Structure fields are empty unless a
    conservative bind succeeded — never a fabricated identifier."""
    empty = {"match_type": "none", "matched_name": "", "npaid": "", "inchikey": "",
             "smiles": "", "mol_formula": "", "npclassifier_class": ""}
    if not anchor:
        return dict(empty)
    if not npatlas_available():
        e = dict(empty)
        e["match_type"] = "unavailable"
        return e
    cands = _candidates(anchor)
    # whole-string / slash candidates, exact-first
    for i, c in enumerate(cands):
        rec = _conservative_lookup(c)
        if rec:
            npc = (rec.get("npclassifier") or {}).get("class") or []
            return {
                # v9.7.371 fix: was "exact" if (i == 0 or c == anchor.strip()). _candidates()
                # orders slash-split PARTS first and the raw whole-anchor string LAST, so a
                # slash-derived first part (e.g. "sporolide A" from "sporolide A/sporolide B")
                # hit i==0 and was mislabeled "exact" even though a slash-split was required to
                # get the match. Only the literal whole-anchor string matching should count as
                # exact; c == anchor.strip() alone already covers the non-slash case too (the
                # single candidate always equals the anchor when there is no slash/semicolon).
                "match_type": "exact" if c == anchor.strip() else "slash",
                "matched_name": rec.get("name", ""),
                "npaid": rec.get("npaid", ""),
                "inchikey": rec.get("inchikey", ""),
                "smiles": rec.get("smiles", ""),
                "mol_formula": rec.get("mol_formula", ""),
                "npclassifier_class": "; ".join(str(x) for x in npc),
            }
    return dict(empty)


# --------------------------------------------------------------------------------------------
# NPA-03 (v9.7.405, punch-card B7 step 3): deterministic RDKit SVG rendering of a bound
# reference structure. Structure-display audit's exact ceiling text is mandatory on every
# rendered/held/unavailable result -- a caller must never strip it before display.
# --------------------------------------------------------------------------------------------
STRUCTURE_CAPTION_CEILING = "structure of a related characterized reference, not the predicted BGC product"


def _looks_wildcard_smiles(smiles: str) -> bool:
    """Cheap pre-check for an R-group/dummy-atom SMILES (e.g. "*", "[*]", "R1") before even
    trying RDKit -- these never render a real, specific structure."""
    s = smiles or ""
    return "*" in s or bool(re.search(r"\bR\d*\b", s))


def render_structure_svg(smiles: str, *, width: int = 400, height: int = 300) -> dict[str, Any]:
    """Render `smiles` to a deterministic SVG via RDKit's MolDraw2D, or return a typed non-render
    state -- never a fabricated or partial structure, and never a bare exception.

    Returns a dict with keys: state ("RENDERED"|"HOLD"|"UNAVAILABLE"), svg (str or None), reason
    (str or None), width, height, rdkit_version (str or None), caption (the mandatory ceiling
    text -- render this alongside the SVG in any UI, never the SVG alone).
      * UNAVAILABLE -- rdkit does not import in this environment. Not an error: this module (and
        NP Atlas provisioning generally) works fully without RDKit; only structure rendering needs it.
      * HOLD -- no SMILES, a wildcard/R-group SMILES, or a SMILES RDKit could not parse. Never
        renders a placeholder or guessed structure for these.
      * RENDERED -- a real, specific, deterministically-drawn structure.
    """
    out: dict[str, Any] = {
        "state": "HOLD", "svg": None, "reason": None,
        "width": width, "height": height, "rdkit_version": None,
        "caption": STRUCTURE_CAPTION_CEILING,
    }
    if not smiles or not smiles.strip():
        out["reason"] = "no SMILES on the resolved record"
        return out
    if _looks_wildcard_smiles(smiles):
        out["reason"] = "wildcard/R-group SMILES -- not a single specific structure"
        return out
    try:
        import rdkit
        from rdkit import Chem
        from rdkit.Chem.Draw import rdMolDraw2D
    except Exception:
        out["state"] = "UNAVAILABLE"
        out["reason"] = "rdkit is not installed in this environment"
        return out
    out["rdkit_version"] = getattr(rdkit, "__version__", None)
    try:
        mol = Chem.MolFromSmiles(smiles)
    except Exception:
        mol = None
    if mol is None:
        out["reason"] = "SMILES did not parse to a valid molecule"
        return out
    if any(atom.GetAtomicNum() == 0 for atom in mol.GetAtoms()):
        out["reason"] = "structure contains a wildcard/dummy atom"
        return out
    try:
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
    except Exception as exc:  # pragma: no cover - RDKit-internal drawing failure, not our contract
        out["reason"] = f"rdkit drawing failed: {exc}"
        return out
    out["state"] = "RENDERED"
    out["svg"] = svg
    return out


if __name__ == "__main__":
    import sys
    for a in (sys.argv[1:] or ["nystatin", "kendomycin B", "sporolide A/sporolide B",
                               "definitely-not-a-real-compound-xyz"]):
        r = resolve_name_to_structure(a)
        emit(f"{a:38s} -> [{r['match_type']:5s}] {r['matched_name'][:24]:24s} {r['inchikey']}")
