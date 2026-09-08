"""exclusions.py — single source of truth (SSOT) for whole-strain exclusions.

Human record: ``OFFICIAL_DATA/EXCLUSIONS.md`` (workspace root). Machine mirror:
``OFFICIAL_DATA/exclusions.json``. This accessor reads that JSON when it can be
located, else a documented in-module default (``_DEFAULT``) that mirrors it
verbatim — so behaviour is deterministic whether or not OFFICIAL_DATA is bundled
alongside the code tree.

Two exclusion SCOPES — do not conflate them:

  * ``raw_analysis_excluded()`` -> strains whose RAW on-disk antiSMASH package is
    not usable as-is. ``= hard_excluded() | raw_assembly_void() = {STRAIN-X,
    STRAIN-X}``. Report layers that read the raw sealed package / per-gene tables
    (dualpass_ledger, p450_tailoring, compound_family_report, assembly_line,
    interactive_figures/widget_data) use this, because the RAW STRAIN-X assembly is
    still the Nocardia + Micromonospora + Bacillus three-way chimera until the
    decontaminated fraction is ingested.

  * ``governed_excluded()`` -> strains held OUT of GOVERNED conclusions
    ``= hard_excluded() = {STRAIN-X}``. STRAIN-X was RATIFIED into GOVERNED on
    2026-08-05 (the Developer or User) via its decontaminated strain-of-record, and its count was
    RE-RATIFIED 2026-08-14 (the Developer or User) from the projected 38 to the MEASURED 52-region
    decontam antiSMASH run (`STRAIN-X_nocardia_clean.zip`), so it is NOT excluded
    from governed counts. STRAIN-X was OMITTED by the Developer or User ruling 2026-08-09 (duplicate
    of SID-Y; -48 regions), so GOVERNED = 44 strains / 1,753 regions (was 1,739
    under the projected STRAIN-X=38). SID-Y remains distinct and is NOT withdrawn.

  * ``qc_hold_audit_only()`` -> strains held audit-only pending a clean re-run,
    NOT counted in GOVERNED and NOT hard-excluded ``= {STRAIN-X}``. Distinct from
    hard exclusion: the strain is not contaminated-by-ruling, its run is simply
    not admissible yet (STRAIN-X: contamination-suspect + record-limit truncation
    + very-poor assembly, so its BGC count is a FLOOR, not a count).

This dual state is the whole point: STRAIN-X is IN the governed conclusions but its
RAW package is still void. Route every module through these accessors instead of a
local ``EXCLUDE_STRAINS`` literal so a future exclusion change is one edit, not six.

See ``OFFICIAL_DATA/EXCLUSIONS.md`` for the authoritative human-readable record.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Documented default — mirrors OFFICIAL_DATA/exclusions.json verbatim. Used when
# the JSON cannot be located (e.g. a code-only tree with no OFFICIAL_DATA bundled).
# Generic shipped default: EMPTY. A public install excludes nothing until an operator
# binds a cohort pack (OFFICIAL_DATA/exclusions.json via MAMEY_OFFICIAL_DATA / MAMEY_DATA_ROOT,
# or an OFFICIAL_DATA/ dir on the parent walk). Fail-safe: no cohort identifiers ship in code.
_DEFAULT: dict[str, Any] = {
    "hard_excluded": [],
    "raw_assembly_void": [],
    "strain_of_record": {},
    "qc_hold_audit_only": [],
    "governed": {},
}


def _probe_paths(filename: str) -> list[Path]:
    """Ordered probe locations for ``OFFICIAL_DATA/<filename>``.

    An EXPLICIT operator override is AUTHORITATIVE: when ``MAMEY_OFFICIAL_DATA`` (or, next,
    ``MAMEY_DATA_ROOT``) is set, the ``__file__`` parent walk is not consulted behind it.
    Previously all three sources went into one ordered list and the caller loop simply
    continued past a missing override file, so a tree living UNDER a workspace that holds
    its own ``OFFICIAL_DATA/`` silently returned THAT pack's exclusions and denominators
    even though the operator had pointed the override at a different cohort pack. Isolation
    intent defeated by directory nesting is a governed-data provenance risk, not a
    convenience: the wrong exclusion set or denominator can reach a governed conclusion with
    no signal at all.

    1. ``$MAMEY_OFFICIAL_DATA/<filename>`` -- explicit override, exclusive when set.
    2. ``$MAMEY_DATA_ROOT/OFFICIAL_DATA/<filename>`` -- shared root, exclusive when set and
       no explicit override is given.
    3. Otherwise ``OFFICIAL_DATA/<filename>`` walking up from this package: a tree that
       bundles its own OFFICIAL_DATA is honoured; a code-only tree falls through silently.

    An override naming a directory that lacks the file still falls back to the documented
    empty default (with the existing warning) -- the fallback is to the DEFAULT, never to a
    different pack.
    """
    env = os.environ.get("MAMEY_OFFICIAL_DATA")
    if env:
        return [Path(env) / filename]
    data_root = os.environ.get("MAMEY_DATA_ROOT")
    if data_root:
        return [Path(data_root) / "OFFICIAL_DATA" / filename]
    here = Path(__file__).resolve()
    return [parent / "OFFICIAL_DATA" / filename for parent in here.parents]


def _candidate_json_paths() -> list[Path]:
    """Ordered locations to probe for OFFICIAL_DATA/exclusions.json.

    1. ``$MAMEY_OFFICIAL_DATA/exclusions.json`` (explicit operator override).
    2. ``$MAMEY_DATA_ROOT/OFFICIAL_DATA/exclusions.json`` (shared external-data root).
    3. ``OFFICIAL_DATA/exclusions.json`` walking up from this package (a tree that
       bundles its own OFFICIAL_DATA is honoured; a code-only tree falls through).
    """
    return _probe_paths("exclusions.json")


def _warn_official_data_present_but_file_missing(candidates: list[Path], filename: str) -> None:
    """Warn only when an ``OFFICIAL_DATA`` directory is actually present but ``filename``
    isn't in it — distinct from a genuinely code-only tree, where no ``OFFICIAL_DATA``
    directory exists anywhere in the search path and silence is the documented,
    intended fail-safe (no cohort identifiers ship in code). A directory that IS
    present but missing just this one file is much more likely an operator-side
    provisioning gap on a real, otherwise-populated workspace than an intentional
    public/portable install — surfacing it here turns a silent empty-default fallback
    into a visible, one-line signal instead of a quiet loss of real cohort data.
    """
    if any(p.is_file() for p in candidates):
        # v9.7.403: the file IS there, it just could not be parsed — the caller already
        # warned with the real reason. Saying "is not in it" here would name the wrong
        # problem and send an operator looking for a missing file that exists.
        return
    if any(p.parent.is_dir() for p in candidates):
        import warnings
        warnings.warn(
            f"exclusions.py: an OFFICIAL_DATA/ directory is present but {filename} "
            "is not in it; falling back to an EMPTY default. If this workspace has "
            "real cohort data, this file is likely missing rather than intentionally "
            "absent.",
            RuntimeWarning,
            stacklevel=3,
        )


def load_exclusions(*, strict: bool = False) -> dict[str, Any]:
    """Return the parsed exclusions mapping (OFFICIAL_DATA/exclusions.json or _DEFAULT).

    Falls back to the in-module default (mirroring the JSON) and warns if a JSON
    file is present but unreadable/malformed, so a corrupt file can never silently
    drop a strain from an exclusion set — and also warns if an OFFICIAL_DATA/
    directory is present but exclusions.json specifically is missing from it (see
    :func:`_warn_official_data_present_but_file_missing`); a genuinely code-only
    tree with no OFFICIAL_DATA directory anywhere stays silent, as documented.
    """
    candidates = _candidate_json_paths()
    for p in candidates:
        try:
            if p.is_file():
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    if strict:
                        ids = data.get("hard_excluded")
                        if not isinstance(ids, list) or any(
                            not isinstance(value, str) or not value.strip() or value != value.strip()
                            for value in ids
                        ):
                            raise ValueError("hard_excluded must be a list of non-empty strain identifiers")
                    return data
                if strict:
                    raise ValueError("exclusions must be a JSON object")
        except (OSError, ValueError) as exc:  # pragma: no cover - defensive
            if strict:
                raise ValueError("exclusion source is unreadable or malformed") from exc
            import warnings
            warnings.warn(
                f"exclusions.py: could not read {p} ({exc}); "
                "falling back to the in-module default.",
                RuntimeWarning,
                stacklevel=2,
            )
    if strict and (os.environ.get("MAMEY_OFFICIAL_DATA") or os.environ.get("MAMEY_DATA_ROOT")
                   or any(p.parent.is_dir() for p in candidates)):
        raise ValueError("bound exclusion source is missing")
    _warn_official_data_present_but_file_missing(candidates, "exclusions.json")
    return dict(_DEFAULT)


def official_data_json(filename: str, default: Any = None) -> Any:
    """Load ``OFFICIAL_DATA/<filename>`` as parsed JSON, or ``default`` if absent.

    For cohort-specific data that must NOT ship in the public code tier (per-strain
    assembly tiers, comparison-cohort membership, demo rosters). Uses the same env /
    package probing as :func:`load_exclusions`. A code-only tree with no OFFICIAL_DATA
    directory anywhere in the search path falls through to ``default`` silently, so
    the shipped tier stays data-free. But if an OFFICIAL_DATA/ directory IS present
    and ``filename`` simply isn't in it (or is present but unreadable/malformed), this
    warns rather than silently returning ``default`` — matching :func:`load_exclusions`'s
    existing contract, and closing a real gap: prior to this, a missing or corrupt
    file here was indistinguishable from an intentional code-only install.
    """
    if default is None:
        default = {}
    candidates = _probe_paths(filename)
    for p in candidates:
        try:
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:  # pragma: no cover - defensive
            import warnings
            warnings.warn(
                f"exclusions.py: could not read {p} ({exc}); "
                f"falling back to the caller-supplied default for {filename}.",
                RuntimeWarning,
                stacklevel=2,
            )
            continue
    _warn_official_data_present_but_file_missing(candidates, filename)
    return default


def hard_excluded() -> set[str]:
    """Strains out of every governed conclusion. ``{STRAIN-X, STRAIN-X}``.

    STRAIN-X = contaminated assembly. STRAIN-X = omitted by the Developer or User ruling 2026-08-09
    (duplicate of SID-Y). Root cause confirmed 2026-08-10 -- the SID-Y genome
    is labeled as STRAIN-X (identity/label error); SID-Y remains distinct.
    """
    return set(load_exclusions().get("hard_excluded", _DEFAULT["hard_excluded"]))


def raw_assembly_void() -> set[str]:
    """Strains whose RAW on-disk assembly is void (chimera/artifact). {STRAIN-X}.

    IN governed conclusions via a decontaminated strain-of-record, but the RAW
    package must still be skipped by raw-data modules until decontam is ingested.
    """
    return set(load_exclusions().get("raw_assembly_void", _DEFAULT["raw_assembly_void"]))


def raw_analysis_excluded() -> set[str]:
    """Strains RAW-data modules must skip = hard_excluded() | raw_assembly_void().

    == {STRAIN-X, STRAIN-X}. Use this in modules that read the raw sealed package /
    per-gene tables (the raw STRAIN-X assembly is still the chimera).
    """
    return hard_excluded() | raw_assembly_void()


def governed_excluded() -> set[str]:
    """Strains OUT of GOVERNED conclusions = hard_excluded() == {STRAIN-X, STRAIN-X}.

    STRAIN-X is IN GOVERNED (decontaminated strain-of-record, ratified 2026-08-05).
    Strains under a QC hold are ALSO not counted, but they are not hard-excluded --
    see :func:`qc_hold_audit_only`.
    """
    return hard_excluded()


def qc_hold_audit_only() -> set[str]:
    """Strains held audit-only pending a clean re-run. ``{STRAIN-X}``.

    NOT counted in GOVERNED and NOT hard-excluded: the run is inadmissible, not the
    strain. Admit after decontamination + a re-run at a higher record ``--limit``.
    """
    return set(load_exclusions().get("qc_hold_audit_only", _DEFAULT["qc_hold_audit_only"]))


def strain_of_record(strain: str) -> str | None:
    """Return the decontaminated strain-of-record tag for a raw-void strain, if any."""
    return load_exclusions().get("strain_of_record", {}).get(str(strain))


def governed_denominator() -> dict[str, int]:
    """The GOVERNED denominator, e.g. {'strains': N, 'regions': M}, from OFFICIAL_DATA."""
    return dict(load_exclusions().get("governed", _DEFAULT["governed"]))
