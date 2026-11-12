# Your first hour: a public antiSMASH result

Practice with the *Streptomyces avermitilis* GCA_000009765 antiSMASH result ZIP; see
[Public datasets](../PUBLIC_DATASETS.md). Save the result ZIP (not a raw genome FASTA)
as `~/Downloads/Streptomyces_avermitilis_GCA_000009765.zip`. Open a terminal in the
program folder and activate your installed Python environment. Change the ZIP path in
both commands if needed; quote paths containing spaces.

```bash
python mamey_run.py doctor
python mamey_run.py inspect ~/Downloads/Streptomyces_avermitilis_GCA_000009765.zip
```

Resolve blocking or missing core dependencies before continuing. For the archive reviewed,
inspect reported antiSMASH 8.0.4, 60 region GBKs and 60 KnownClusterBlast text files.
Counts can differ with another archive; inspection does not guarantee a successful run.

Run the capped command below in a fresh output location. The reviewed command used the
generic taxonomy shown and made no isolation-source assertion.

```bash
python mamey_run.py run \
  --strain Streptomyces_avermitilis_GCA_000009765 \
  --input-zip ~/Downloads/Streptomyces_avermitilis_GCA_000009765.zip \
  --taxonomy "Streptomyces sp." --mode gold --release PRIVATE \
  --capped-session --json-evidence off --brief none
```

Check the exit code before continuing. The reviewed run exited 0 with
`MAMEY_COMPLETE_WITH_ISSUES`; read the issue log and phase receipts.

```bash
python mamey_run.py validate \
  runs/Streptomyces_avermitilis_GCA_000009765/package --workbook-strict
```

The reviewed strict validation exited 0. Validation updates `package_status.json`; validate
a copy to preserve the package as written. Open the package's `OPEN_ME_FIRST.html`, issue
log, triage board and workbook; keep the completed ZIP and input ZIP. The main JSON reader
was off in this run; a separate pass may still read selected JSON evidence. Unread evidence
is not a negative result, and software checks do not establish biological conclusions.
[Your first run](01_FIRST_RUN.md) and [Read one saved package](03_READ_RESULTS.md) explain the next steps.
