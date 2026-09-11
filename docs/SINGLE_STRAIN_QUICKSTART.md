# Single-strain quickstart

This is the shortest supported path from one antiSMASH result ZIP to a validated Mamey
package. Run it from the extracted bundle root, which contains `pyproject.toml` and
`mamey_run.py`.

```bash
python mamey_run.py start
python mamey_run.py inspect path/to/antismash_result.zip
python mamey_run.py run --strain EXAMPLE \
  --input-zip path/to/antismash_result.zip \
  --taxonomy 'Genus sp.' --source 'recorded isolation source' \
  --mode gold --outdir runs/
python mamey_run.py validate runs/EXAMPLE/package
python mamey_run.py explain runs/EXAMPLE/package
```

Replace the example values with metadata verified from the input. `inspect` previews the ZIP;
`run` creates the package; `validate` checks the package and its encoded gates. Read the emitted
status and issue files before interpreting results. A validation pass does not establish a
species identification, compound identity, production, bioactivity, or scientific acceptance.

For a time-limited run, add `--capped-session`. It disables JSON evidence and automatically
rendered locus maps, so omit it and use `--json-evidence bounded` when those evidence fields are
needed and sufficient runtime is available.

After validation, use `python mamey_run.py discover <workspace>` to inventory packages and next
actions. Use `render-all-figures` for the applicable figure suite, `phylo-autopilot` for 16S
placement, `phylo-run` for an approved genome tree, and `mode-b` to prepare interpretation
scaffolds. See the [Quick Guide](GUIDE/02_Quick_Guide.md) for those post-seal workflows.
