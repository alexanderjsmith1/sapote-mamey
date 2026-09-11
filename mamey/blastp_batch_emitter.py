"""BlastpBatchEmitter — sequential NCBI BLASTP batch FASTA emitter (v9.7.145).

Emits NCBI-web-safe FASTA batches for manual BLASTP submission.

Rules enforced here:
- Default batch size: 3 proteins per batch (not 5, not 10)
- Top 10 hits recommended (not NCBI default of 100)
- Batch numbering: always sequential integers, no letter suffixes
- SIGXFSZ recovery: on failure, re-emit as next batch number reprioritised by value
- Each batch emits a companion _README.txt with submission instructions
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Sequence


DEFAULT_BATCH_SIZE = 3          # proteins per batch
RECOMMENDED_MAX_HITS = 10       # tell user to set this in NCBI web UI
NCBI_WEB_HARD_CAP = 100_000    # residue cap for NCBI web BLASTP


@dataclass
class BatchEntry:
    header: str
    sequence: str

    @property
    def residues(self) -> int:
        return len(self.sequence)

    def fasta(self) -> str:
        lines = [self.header]
        seq = self.sequence
        lines += [seq[i:i+70] for i in range(0, len(seq), 70)]
        return "\n".join(lines)


@dataclass
class BlastpBatch:
    batch_number: int
    entries: list[BatchEntry] = field(default_factory=list)

    @property
    def total_residues(self) -> int:
        return sum(e.residues for e in self.entries)

    @property
    def fasta_text(self) -> str:
        return "\n".join(e.fasta() for e in self.entries) + "\n"

    def readme_text(self, strain: str = "", bgc_context: str = "") -> str:
        ctx = f"  Context: {bgc_context}\n" if bgc_context else ""
        strain_line = f"  Strain: {strain}\n" if strain else ""
        return dedent(f"""\
            # BLASTP submission — batch {self.batch_number}
            {strain_line}{ctx}
            # NCBI settings (required):
            #   Database:  nr
            #   Algorithm: blastp
            #   Max hits:  {RECOMMENDED_MAX_HITS}  (change from default 100)
            #
            # Contents ({len(self.entries)} sequences, {self.total_residues:,} residues):
            """ + "\n".join(
                f"#   {e.header.lstrip('>')[:80]}: {e.residues} aa"
                for e in self.entries
            ) + f"""
            #
            # Submit all sequences in this file in a single BLASTP run.
            # If NCBI returns a SIGXFSZ or process-size error, report it and
            # a new batch will be emitted with the failed sequences reprioritised.
            #
            # Save results as:  Alignment XML2 + Hit Table (CSV)
            # Name files:   batch{self.batch_number}-Alignment.xml
            #               batch{self.batch_number}-Alignment-HitTable.csv
            """)


class BlastpBatchEmitter:
    """Emit sequential BLASTP batches from a list of (header, sequence) pairs.

    Usage::

        emitter = BlastpBatchEmitter(batch_size=3, strain="AS-XXX", bgc_context="polyene megacluster")
        emitter.add("BGC028|NODE_32|ctg32_1|...", "MSTEG...")
        emitter.add("BGC028|NODE_32|ctg32_2|...", "MQLAN...")
        emitter.add("BGC028|NODE_32|ctg32_3|...", "MSSTE...")
        batches = emitter.print(start_batch=7)   # emit as batch 7, 8, 9...
    """

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        strain: str = "",
        bgc_context: str = "",
    ) -> None:
        if not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError(f"batch_size must be a positive integer, got {batch_size!r}")
        self.batch_size = batch_size
        self.strain = strain
        self.bgc_context = bgc_context
        self._pending: list[BatchEntry] = []

    def add(self, header: str, sequence: str) -> None:
        """Add a protein to the emission queue."""
        if not header.startswith(">"):
            header = ">" + header
        self._pending.append(BatchEntry(header=header, sequence=sequence))

    def add_sigxfsz_recovery(self, failed_entries: list[BatchEntry]) -> None:
        """Re-queue sequences from a failed SIGXFSZ batch, prepended to the queue."""
        self._pending = failed_entries + self._pending

    def emit(self, start_batch: int = 1) -> list[BlastpBatch]:
        """Split pending entries into batches and return them.

        Batch numbers are sequential integers starting at start_batch.
        No letter suffixes. No gaps.
        """
        batches: list[BlastpBatch] = []
        entries = list(self._pending)
        batch_num = start_batch
        while entries:
            chunk = entries[:self.batch_size]
            entries = entries[self.batch_size:]
            batches.append(BlastpBatch(batch_number=batch_num, entries=chunk))
            batch_num += 1
        return batches

    def write_batches(
        self,
        outdir: str | Path,
        start_batch: int = 1,
        prefix: str = "blastp",
    ) -> list[Path]:
        """Write FASTA + README for each batch to outdir. Returns list of FASTA paths."""
        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        batches = self.emit(start_batch=start_batch)
        written: list[Path] = []
        for batch in batches:
            fasta_path = outdir / f"{prefix}_batch{batch.batch_number}.fasta"
            readme_path = outdir / f"{prefix}_batch{batch.batch_number}_README.txt"
            # Atomic write (.tmp sibling + Path.replace): a killed process (SIGKILL/OOM/power
            # loss) must never leave a truncated batch overwriting a previously-valid one —
            # this path is re-run on every SIGXFSZ retry per this module's own docstring.
            _fasta_tmp = fasta_path.with_name(fasta_path.name + ".tmp")
            _fasta_tmp.write_text(batch.fasta_text, encoding="utf-8")
            _fasta_tmp.replace(fasta_path)
            _readme_tmp = readme_path.with_name(readme_path.name + ".tmp")
            _readme_tmp.write_text(
                batch.readme_text(strain=self.strain, bgc_context=self.bgc_context),
                encoding="utf-8",
            )
            _readme_tmp.replace(readme_path)
            written.append(fasta_path)
        return written


# ── SIGXFSZ detection helper ────────────────────────────────────────────────

SIGXFSZ_PATTERNS = re.compile(
    r"SIGXFSZ|process.?size.?limit|search.?problem|ncbi.?error|"
    r"unable.?to.?run|service.?unavailable|request.?failed",
    re.IGNORECASE,
)


def is_sigxfsz_report(text: str) -> bool:
    """Return True if the text describes a NCBI SIGXFSZ or equivalent error."""
    return bool(SIGXFSZ_PATTERNS.search(text))
