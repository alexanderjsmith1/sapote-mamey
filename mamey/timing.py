"""timing.py — machine-readable timing telemetry for Mamey runs (v9.7.81).

Every completed run emits:
  <strain>_timing_breakdown.json   — full schema with monotonic phase durations
  <strain>_timing_breakdown.csv    — flat phase table for spreadsheet analysis
  <strain>_timing_breakdown.md     — human-readable summary table

The TimingRecorder is a context-manager-based recorder that wraps named phases.
It is safe to instantiate before `package_dir` exists; write() is called after.
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

import csv
import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

try:
    import resource as _resource
    _HAS_RESOURCE = True
except ImportError:
    _HAS_RESOURCE = False  # Windows


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PhaseTiming:
    name: str
    start_monotonic_ns: int
    end_monotonic_ns: int | None = None
    elapsed_seconds: float | None = None
    status: str = "RUNNING"
    records_in: int | None = None
    records_out: int | None = None
    notes: str = ""

    def to_csv_row(self) -> dict:
        return {
            "name": self.name,
            "elapsed_seconds": self.elapsed_seconds,
            "status": self.status,
            "records_in": self.records_in,
            "records_out": self.records_out,
            "notes": self.notes,
        }


class TimingRecorder:
    """Records phase durations, process metrics, and emits timing files into a package dir."""

    # Canonical phase names (used in cli.py wrappers; not enforced here)
    PHASE_STARTUP          = "startup_dependency_probe"
    PHASE_ZIP_INVENTORY    = "input_zip_inventory"
    PHASE_ANTISMASH_PARSE  = "antismash_kcb_riq_parse"
    PHASE_BGC_INVENTORY    = "bgc_region_inventory_parse"
    PHASE_GBK_PFAM         = "gbk_pfam_extract"
    PHASE_SOURCE_SCANS     = "source_scans_cctt_cgad_efls_resistance_tfbs"
    PHASE_RGGMCI           = "rggmci_reconstruction"
    PHASE_SCAN_TRIAGE      = "scan_pack_and_triage"
    PHASE_WORKBOOK         = "workbook_write"
    PHASE_PACKAGE_WRITE    = "package_write"
    PHASE_MANIFEST         = "manifest_write"
    PHASE_CHECKSUM         = "checksum_write"
    PHASE_ZIP_SEAL         = "zip_seal"
    PHASE_POST_SEAL        = "post_seal_receipt"
    PHASE_BRIEF_RENDER     = "brief_render"
    PHASE_GENE_BY_GENE     = "gene_by_gene_table"

    def __init__(
        self,
        strain_id: str,
        mode: str,
        mamey_version: str,
        workflow_version: str = "",
        chatgpt_safe: bool = False,
        input_zip_bytes: int | None = None,
    ) -> None:
        self.strain_id = strain_id
        self.mode = mode
        self.mamey_version = mamey_version
        self.workflow_version = workflow_version
        self.chatgpt_safe = chatgpt_safe
        self.input_zip_bytes = input_zip_bytes
        self.start_utc = datetime.now(timezone.utc).isoformat()
        self.start_ns = time.monotonic_ns()
        self.phases: list[PhaseTiming] = []
        self._active: list[PhaseTiming] = []

    @contextmanager
    def phase(self, name: str, notes: str = "", **_meta) -> Iterator[PhaseTiming]:
        """Context manager: records a named phase; marks FAIL on exception."""
        p = PhaseTiming(name=name, start_monotonic_ns=time.monotonic_ns(), notes=notes)
        self.phases.append(p)
        self._active.append(p)
        try:
            yield p
            p.status = "PASS"
        except Exception:
            p.status = "FAIL"
            raise
        finally:
            self._active.remove(p)
            p.end_monotonic_ns = time.monotonic_ns()
            p.elapsed_seconds = round(
                (p.end_monotonic_ns - p.start_monotonic_ns) / 1e9, 6
            )

    def record(self, name: str, elapsed_seconds: float, status: str = "PASS",
                notes: str = "") -> None:
        """Record a pre-timed phase (for phases instrumented externally)."""
        now_ns = time.monotonic_ns()
        start_ns = now_ns - int(elapsed_seconds * 1e9)
        p = PhaseTiming(
            name=name,
            start_monotonic_ns=start_ns,
            end_monotonic_ns=now_ns,
            elapsed_seconds=round(elapsed_seconds, 6),
            status=status,
            notes=notes,
        )
        self.phases.append(p)

    def finish(self, raw_bgcs: int | None = None, corrected_bgcs: float | None = None) -> dict:
        """Return the full timing dict (does not write files)."""
        end_ns = time.monotonic_ns()
        elapsed = round((end_ns - self.start_ns) / 1e9, 6)
        cpu_user = cpu_sys = peak_rss = None
        if _HAS_RESOURCE:
            try:
                usage = _resource.getrusage(_resource.RUSAGE_SELF)
                cpu_user = round(usage.ru_utime, 6)
                cpu_sys = round(usage.ru_stime, 6)
                peak_rss = usage.ru_maxrss
            except Exception:
                pass
        return {
            "strain_id": self.strain_id,
            "mamey_version": self.mamey_version,
            "workflow_version": self.workflow_version,
            "mode": self.mode,
            "chatgpt_safe": self.chatgpt_safe,
            "input_zip_bytes": self.input_zip_bytes,
            "raw_bgcs": raw_bgcs,
            "corrected_bgcs": corrected_bgcs,
            "process": {
                "start_utc": self.start_utc,
                "end_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": elapsed,
                "cpu_user_seconds": cpu_user,
                "cpu_system_seconds": cpu_sys,
                "peak_rss_kb": peak_rss,
            },
            "phases": [asdict(p) for p in self.phases],
        }

    def populate_from_receipts(self, package_dir: str | Path) -> int:
        """v9.7.87 9.7.87-A: if no phases were recorded via the .phase() context manager,
        build the phase table from run_phase_receipts.jsonl. The cli emits a START receipt at
        the head of each phase but (for most phases) no END — so an END-pairing model recovers
        almost nothing. The phases run sequentially, so each phase's elapsed is the gap from its
        START to the NEXT phase's START (the last phase runs to the final/terminal receipt).
        Uses the monotonic timestamp (mono_ns). Returns phases populated. Never raises."""
        if self.phases:
            return 0
        import json as _j
        pdir = Path(package_dir)
        rpath = pdir / "run_phase_receipts.jsonl"
        if not rpath.exists():
            return 0
        try:
            rows = []
            for line in rpath.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    r = _j.loads(line)
                except Exception:
                    continue
                if r.get("mono_ns") is not None and r.get("phase"):
                    rows.append(r)
            if not rows:
                return 0
            rows.sort(key=lambda r: int(r["mono_ns"]))

            # collapse to one entry per phase at its first START (or first sighting), in order;
            # capture an explicit END mono if one exists for the terminal phase.
            TERMINALS = {"terminal", "MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES"}
            phase_starts: list[tuple[str, int, str]] = []   # (phase, mono_ns, status)
            seen = set()
            end_mono_by_phase: dict[str, int] = {}
            last_mono = int(rows[-1]["mono_ns"])
            for r in rows:
                phase = r["phase"]
                status = (r.get("status") or "").upper()
                mono = int(r["mono_ns"])
                if status in ("END", "TIMEOUT", "ERROR", "SKIP", "SKIPPED"):
                    end_mono_by_phase[phase] = mono
                if phase in seen:
                    continue
                seen.add(phase)
                phase_starts.append((phase, mono, status))

            ordered: list[PhaseTiming] = []
            for i, (phase, mono, status) in enumerate(phase_starts):
                # next boundary: the next phase's start, else this phase's own END, else last receipt
                if i + 1 < len(phase_starts):
                    end = phase_starts[i + 1][1]
                else:
                    end = end_mono_by_phase.get(phase, last_mono)
                # if a real END exists and is later than the next-start gap, the END is noise; keep the gap
                elapsed = max(0.0, round((end - mono) / 1e9, 6))
                # skip the synthetic terminal marker row itself as a "phase"
                if phase in TERMINALS or status in TERMINALS:
                    continue
                ordered.append(PhaseTiming(
                    name=phase, start_monotonic_ns=mono, end_monotonic_ns=end,
                    elapsed_seconds=elapsed,
                    status="COMPLETE" if status in ("START", "END") else (status or "COMPLETE"),
                ))
            self.phases = ordered
            return len(ordered)
        except Exception:
            return 0

    def write(
        self,
        package_dir: str | Path,
        raw_bgcs: int | None = None,
        corrected_bgcs: float | None = None,
    ) -> dict:
        """Write JSON + CSV + MD timing files into package_dir. Returns the timing dict."""
        pdir = Path(package_dir)
        # v9.7.87 9.7.87-A: backfill phases from receipts if none were recorded directly,
        # so the breakdown shows real per-phase deltas instead of 100% overhead.
        self.populate_from_receipts(pdir)
        data = self.finish(raw_bgcs=raw_bgcs, corrected_bgcs=corrected_bgcs)
        sid = self.strain_id

        # v9.7.371 fix: all 3 writes below were direct-to-final-path (no tmp+replace), yet
        # cli.py's caller comment says explicitly "write timing breakdown files BEFORE
        # manifest/checksum so they are sealed" -- an interrupted write here (the exact scenario
        # HeartbeatThread later in this file exists to detect) gets hash-pinned into
        # checksums_sha256.txt as a "valid" corrupt file. Same tmp-sibling+replace pattern as
        # judgment_store._atomic_write_text / packaging._atomic_write_text.
        # --- JSON ---
        json_path = pdir / f"{sid}_timing_breakdown.json"
        _json_tmp = json_path.with_name(json_path.name + ".tmp")
        _json_tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _json_tmp.replace(json_path)

        # --- CSV (flat phase table) ---
        csv_path = pdir / f"{sid}_timing_breakdown.csv"
        csv_fields = ["name", "elapsed_seconds", "status", "records_in",
                      "records_out", "notes"]
        _csv_tmp = csv_path.with_name(csv_path.name + ".tmp")
        with open(_csv_tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=csv_fields)
            w.writeheader()
            for p in self.phases:
                w.writerow(p.to_csv_row())
        _csv_tmp.replace(csv_path)

        # --- Markdown ---
        md_path = pdir / f"{sid}_timing_breakdown.md"
        proc = data["process"]
        lines = [
            f"# Timing Breakdown — {sid}",
            f"Mamey v{self.mamey_version} · mode={self.mode} · "
            f"chatgpt_safe={self.chatgpt_safe}",
            f"Start: {proc['start_utc']}  |  Elapsed: **{proc['elapsed_seconds']:.2f}s**",
        ]
        if proc["peak_rss_kb"]:
            lines.append(f"Peak RSS: {proc['peak_rss_kb']:,} KB  |  "
                         f"CPU user: {proc.get('cpu_user_seconds', '?')}s  "
                         f"sys: {proc.get('cpu_system_seconds', '?')}s")
        if raw_bgcs is not None:
            lines.append(f"BGCs: {raw_bgcs} raw / {corrected_bgcs} corrected")
        lines += [
            "",
            "| Phase | Elapsed (s) | Status | Notes |",
            "|-------|-------------|--------|-------|",
        ]
        for p in self.phases:
            el = f"{p.elapsed_seconds:.3f}" if p.elapsed_seconds is not None else "—"
            lines.append(
                f"| {p.name} | {el} | {p.status} | {p.notes[:60]} |"
            )
        # Phase sum vs total
        phase_sum = sum(
            p.elapsed_seconds for p in self.phases if p.elapsed_seconds is not None
        )
        lines += [
            "",
            f"**Phase sum:** {phase_sum:.2f}s  |  "
            f"**Process total:** {proc['elapsed_seconds']:.2f}s  |  "
            f"**Overhead:** {max(0, proc['elapsed_seconds'] - phase_sum):.2f}s",
            "",
        ]
        _md_tmp = md_path.with_name(md_path.name + ".tmp")
        _md_tmp.write_text("\n".join(lines), encoding="utf-8")
        _md_tmp.replace(md_path)

        return data

    def manifest_pointer(self, strain_id: str | None = None) -> dict:
        """Return the manifest timing block to embed in manifest.json."""
        sid = strain_id or self.strain_id
        return {
            "timing_json": f"{sid}_timing_breakdown.json",
            "timing_csv": f"{sid}_timing_breakdown.csv",
            "timing_md": f"{sid}_timing_breakdown.md",
            "external_timer_available": False,
            "canonical_clock": "time.monotonic_ns",
        }


# ---------------------------------------------------------------------------
# ChatGPT-safe heartbeat during quiet finalization
# ---------------------------------------------------------------------------

class HeartbeatThread:
    """Emit periodic progress lines while a potentially quiet block is running.

    Used under --chatgpt-safe for workbook/finalization/package stages where a
    long blocking call can otherwise look stalled in an LLM tool session.
    """

    def __init__(self, label: str, *, enabled: bool = False, seconds: int = 20, stream=None, clock=None):
        self.label = str(label)
        self.enabled = bool(enabled)
        self.seconds = max(1, int(20 if seconds is None else seconds))
        self.stream = stream
        self.clock = clock
        self._stop = None
        self._thread = None
        self.emitted = 0

    def _emit(self) -> None:
        import sys as _sys
        import time as _time
        stream = self.stream or _sys.stderr
        stamp = _time.strftime("%H:%M:%S")
        emit(f"[{stamp}] [heartbeat] {self.label} still running", file=stream, flush=True)
        self.emitted += 1

    def __enter__(self):
        if not self.enabled:
            return self
        import threading
        self._stop = threading.Event()

        def _loop():
            while self._stop is not None and not self._stop.wait(self.seconds):
                self._emit()

        self._thread = threading.Thread(target=_loop, name=f"mamey-heartbeat-{self.label}", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._stop is not None:
            self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=0.2)
        return False


def heartbeat_context(label: str, *, enabled: bool = False, seconds: int = 20, stream=None) -> HeartbeatThread:
    return HeartbeatThread(label, enabled=enabled, seconds=seconds, stream=stream)
