# Comparison alignment resource control

`mamey compare` uses one protein-alignment thread by default. Increase it explicitly
when more CPU capacity is available:

```bash
python mamey_run.py compare \
  --strain-a "inputs/query strain.zip" \
  --strain-b "inputs/reference strain.zip" \
  --alignment-threads 2 --out "comparison results"
```

The option must be a positive integer. Zero, negative values, and non-integers are
refused before input extraction or output-directory creation. The previous command
hardcoded zero (backend-selected threading); the new default intentionally favors
shared and resource-constrained machines and may take longer.

DIAMOND receives the setting for database construction and protein search. Each
pyswrd query batch receives the same setting. The Biopython fallback remains serial.
The requested value is recorded as `alignment_threads` in `gemini_summary.json`;
it is not a measurement of active native threads.

This is an alignment setting, not a process-wide CPU or memory limit. Optional ANI
calculations enabled by `--genome-a` and `--genome-b` retain their backend defaults.
It does not change the pyswrd batch size or the alignment scoring/classification
rules. Sequence similarity remains evidence of similarity, not product identity.
