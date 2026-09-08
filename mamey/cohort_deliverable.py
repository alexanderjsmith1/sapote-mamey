"""cohort_deliverable.py -- the `mamey cohort` front-door.

THE GAP THIS FILLS
------------------
The single-strain path (`mamey run --mode gold`) has a *mandatory-deliverable gate*
(cli.py): a completed run is guaranteed to hand the user a human-readable compiled
report, not just a sealed package. The cross-strain layer had all the *capabilities*
(cohort_synthesis, cohort_figures, bigscape_figures) but no single front-door that
triggers them together and *guarantees* a cohort deliverable is emitted. A user who
ran a whole cohort could end up with figures in one dir, a master workbook in another,
and no single "cross-strain results" deliverable unless they knew to ask.

`run_cohort_deliverable` closes that: one call over a runs directory produces a cohort
deliverable bundle -- the cross-strain synthesis report (the methods-paper "cross-strain
results" prose) plus the cohort figure suite -- and a mandatory-deliverable gate that
REFUSES to report success while emitting zero human-readable deliverables, mirroring the
single-strain promise.

CLAIM DISCIPLINE
----------------
This module orchestrates existing writers; it does not compute new capacity claims. The
synthesis writer (cohort_synthesis) is capacity-level throughout and traces every claim
to a named master sheet -- this module does not relax that. GCF/BiG-SCAPE is similarity,
not identity, and is only included when an external BiG-SCAPE db is supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CohortDeliverableResult:
    """What the cohort front-door produced. `deliverables` is the human-readable set;
    `ok` reflects the mandatory-deliverable gate (COH-03) AND the engine-uniformity gate (COH-01)."""
    out_dir: Path
    deliverables: list[Path] = field(default_factory=list)
    figures_dir: Optional[Path] = None
    figure_count: int = 0
    strains: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    synthesis_report: Optional[Path] = None
    engine_uniform: bool = True

    @property
    def ok(self) -> bool:
        # COH-03: the mandatory cohort deliverable is the actual CROSS_STRAIN_SYNTHESIS.md, NOT
        # figure captions. A cohort run that produced only figure_captions.md (no master, or a
        # stale/empty master) has not met the single-strain-parity promise and must flip the exit
        # non-zero so the missing synthesis is surfaced rather than masked by captions counting as
        # "a deliverable".
        # COH-01: even a written synthesis is invalid if the cohort spans more than one scoring
        # engine — a mixed-engine cross-strain comparison is a wrong answer, so the gate fails too.
        return self.synthesis_report is not None and self.engine_uniform


def _locate_master(runs_dir: Path, explicit: Optional[str]) -> Optional[Path]:
    """Find the verified cohort master workbook the synthesis writer reads. Prefer an
    explicit path; else look for a conventional master under the runs dir. Returns None
    if none is found (caller records a warning -- we never fabricate a master)."""
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    # conventional locations, newest-looking last. Case-INSENSITIVE: the master-workbook
    # step names its output with a capital "Master" (e.g. Mamey_Master.xlsx,
    # Mamey_v1.9.111_Master_After_<strain>.xlsx), so a lowercase "*master*" glob silently
    # misses the very file it is meant to find. Match on a case-folded stem instead.
    def _is_master(path: Path) -> bool:
        return "master" in path.stem.casefold() and not path.name.startswith("~$")
    candidates = (
        {p for p in runs_dir.glob("*.xlsx") if _is_master(p)}
        | {p for p in runs_dir.glob("**/*.xlsx") if _is_master(p)}
    )
    if not candidates:
        return None
    # Pick the MOST COMPLETE master (max A2_Strain_Registry data rows), tie-break newest
    # mtime. The previous sorted()[-1] returned the ALPHABETICALLY-last file, not the newest
    # or fullest -- a partial per-append snapshot (e.g. Mamey_..._Master_After_AS-XXX.xlsx)
    # sorts after the canonical Mamey_Master.xlsx, so the cohort silently ran on a subset of
    # strains. Completeness, not filename order, decides.
    def _strain_rows(path: Path) -> int:
        try:
            from openpyxl import load_workbook
            from .xlsx_determinism import guard_workbook_size as _guard_xlsx  # v9.7.410
            _guard_xlsx(path)
            wb = load_workbook(path, read_only=True)
            try:
                if "A2_Strain_Registry" in wb.sheetnames:
                    return max(wb["A2_Strain_Registry"].max_row - 1, 0)
            finally:
                wb.close()
        except Exception:
            return -1   # behavior-identical to the prior `pass; return -1`; keeps silent_swallow under ceiling
        return -1
    return max(candidates, key=lambda p: (_strain_rows(p), p.stat().st_mtime))


def _load_version_gate():
    """Load tools/cohort_scoring_version_gate.py by path (the `tools` dir is not an importable
    package). Returns the module, or None if it cannot be located (caller degrades gracefully)."""
    import importlib.util
    gate_path = Path(__file__).resolve().parents[1] / "tools" / "cohort_scoring_version_gate.py"
    if not gate_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("cohort_scoring_version_gate", gate_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # cohort_scoring_version_gate
    return mod


def _collect_engine_versions(master: Path) -> dict[str, str]:
    """{strain: raw version field} for the cohort, from A3_Run_Manifest.version (preferred) or,
    if that sheet/column is absent, from B1_BGC_Master.engine_version. Best-effort, read-only.

    This is the per-strain provenance the engine-uniformity gate (COH-01) certifies before any
    cross-strain aggregation: engine 1.9.114 moved capacity calls, so aggregating strains scored
    under different engines is a live wrong answer."""
    from openpyxl import load_workbook
    versions: dict[str, str] = {}
    from .xlsx_determinism import guard_workbook_size as _guard_xlsx  # v9.7.410
    _guard_xlsx(master)
    wb = load_workbook(master, read_only=True, data_only=True)
    try:
        def _hdr(ws):
            row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
            return [str(x) if x is not None else "" for x in row]
        if "A3_Run_Manifest" in wb.sheetnames:
            ws = wb["A3_Run_Manifest"]; h = _hdr(ws)
            if "strain" in h and "version" in h:
                sidx, vidx = h.index("strain"), h.index("version")
                for r in ws.iter_rows(min_row=2, values_only=True):
                    if r and sidx < len(r) and r[sidx]:
                        versions[str(r[sidx])] = str(r[vidx]) if vidx < len(r) and r[vidx] is not None else ""
        if not versions and "B1_BGC_Master" in wb.sheetnames:
            ws = wb["B1_BGC_Master"]; h = _hdr(ws)
            if "strain" in h and "engine_version" in h:
                sidx, vidx = h.index("strain"), h.index("engine_version")
                for r in ws.iter_rows(min_row=2, values_only=True):
                    if r and sidx < len(r) and r[sidx]:
                        # one row per strain is enough; keep the first seen version per strain
                        versions.setdefault(str(r[sidx]),
                                            str(r[vidx]) if vidx < len(r) and r[vidx] is not None else "")
    finally:
        wb.close()
    return versions


def _check_engine_uniformity(master: Path) -> tuple[bool, Optional[str]]:
    """Run the cohort engine-uniformity gate (COH-01). Returns (uniform, banner_text).

    banner_text is None when the cohort is uniform (or the gate could not be evaluated), else a
    one-line MIXED-ENGINE message to prepend to the synthesis and surface as a loud warning."""
    gate = _load_version_gate()
    if gate is None:
        return True, None
    strain_versions = _collect_engine_versions(master)
    if not strain_versions:
        # no provenance to certify — leave the synthesis/other warnings to speak; don't fabricate a pass claim
        return True, None
    from collections import Counter
    parsed = [gate.parse_engine_version(v) for v in strain_versions.values()]
    parsed = [p for p in parsed if p]
    # certify against the dominant engine present; any strain differing (or unstamped) trips the gate
    dominant = Counter(parsed).most_common(1)[0][0] if parsed else "unknown"
    try:
        gate.assert_uniform_scoring_engine(strain_versions, dominant)
        return True, None
    except gate.CohortVersionError as exc:
        return False, str(exc)


def run_cohort_deliverable(
    runs_dir: str | Path,
    out: str | Path = "cohort_deliverable",
    strains: Optional[list[str]] = None,
    master_path: Optional[str] = None,
    novelty_basis: str = "fully_dark",
    with_figures: bool = True,
    figure_series: str = "all",
    public_only: bool = False,
) -> CohortDeliverableResult:
    """Produce a cohort deliverable bundle from a runs directory.

    Orchestrates, in order: (1) locate the verified cohort master workbook; (2) emit the
    cross-strain synthesis report via cohort_synthesis.write_synthesis; (3) emit the
    cohort figure suite via cohort_figures.generate. The mandatory-deliverable gate lives
    in CohortDeliverableResult.ok: the caller treats ok=False as a non-zero exit.

    Every step is best-effort and records a warning rather than aborting the whole bundle,
    EXCEPT that the gate fails if the net result is zero human-readable deliverables.
    """
    runs_dir = Path(runs_dir)
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    res = CohortDeliverableResult(out_dir=out_dir)

    if not runs_dir.exists():
        res.warnings.append(f"runs_dir {runs_dir} does not exist")
        return res

    # (1) locate master
    master = _locate_master(runs_dir, master_path)
    if master is None:
        res.warnings.append(
            "no verified cohort master workbook found (looked for *master*.xlsx under "
            f"{runs_dir}); cross-strain synthesis needs one. Build it with the master "
            "workbook step first, or pass --master-path."
        )

    # (1b) COH-01 engine-uniformity gate: certify the cohort was scored under ONE engine BEFORE
    # aggregating. A mixed-engine cross-strain comparison is invalid; we still emit the synthesis
    # (so the numbers are inspectable) but stamp it with a MIXED-ENGINE banner and fail the gate.
    mixed_engine_banner: Optional[str] = None
    if master is not None:
        uniform, banner = _check_engine_uniformity(master)
        res.engine_uniform = uniform
        if not uniform:
            mixed_engine_banner = banner
            res.warnings.append(
                "MIXED-ENGINE COHORT — cross-strain comparison INVALID: " + (banner or "")
            )

    # (2) synthesis report (the primary deliverable)
    if master is not None:
        try:
            from .cohort_synthesis import write_synthesis
            report_path = out_dir / "CROSS_STRAIN_SYNTHESIS.md"
            # write_synthesis returns the synthesis markdown as a string (raises on a
            # stale/unverified/empty master); we own writing it to disk.
            md = write_synthesis(master, novelty_basis=novelty_basis)
            if mixed_engine_banner:
                md = ("> **⚠ MIXED-ENGINE COHORT — cross-strain comparison INVALID.**  \n"
                      f"> {mixed_engine_banner}  \n"
                      "> The numbers below are NOT comparable across strains; re-score the whole "
                      "cohort under one engine before using this synthesis.\n\n") + md
            if md and md.strip():
                # v9.7.371 fix: was a plain write_text(). This is CROSS_STRAIN_SYNTHESIS.md, the
                # single mandatory file this module exists to guarantee (COH-03 gate) -- an
                # interrupted write can leave a truncated file that res.synthesis_report/.ok still
                # treat as present/successful. Same tmp-sibling+replace pattern as packaging.py.
                _tmp = report_path.with_name(report_path.name + ".tmp")
                _tmp.write_text(md, encoding="utf-8")
                _tmp.replace(report_path)
                res.synthesis_report = report_path
                res.deliverables.append(report_path)
        except Exception as exc:  # writer raises on stale/empty master -- record, don't abort
            res.warnings.append(f"cross-strain synthesis not emitted: {type(exc).__name__}: {exc}")

    # (3) cohort figures
    if with_figures:
        try:
            from .cohort_figures import generate as _gen
            figs = _gen(runs_dir=str(runs_dir), out=str(out_dir / "figures"),
                        strains=strains, public_only=public_only, series=figure_series)
            if isinstance(figs, dict):
                res.figures_dir = Path(figs.get("out", out_dir / "figures"))
                res.figure_count = int(figs.get("figures", 0) or 0)
                res.strains = list(figs.get("strains", []) or [])
                # a figure suite with captions is itself a human-readable deliverable
                caps = res.figures_dir / "figure_captions.md" if res.figures_dir else None
                if caps and caps.exists():
                    res.deliverables.append(caps)
        except Exception as exc:
            res.warnings.append(f"cohort figures not emitted: {type(exc).__name__}: {exc}")

    return res
