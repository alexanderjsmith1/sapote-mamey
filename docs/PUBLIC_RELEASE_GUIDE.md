# Public release — user guide

> **Current-tree status.** This CODE tree is a controlled quality-recheck candidate, not a signed public release. [`pyproject.toml`](../pyproject.toml) and the synced package identity define its canonical bundle version; [`RELEASE_MANIFEST.md`](../RELEASE_MANIFEST.md) defines its current release status.

This is the single starting point for the public (GitHub) release. It covers what the release contains
(code and small governed data; the Pfam HMM is operator-provisioned, not bundled), how the pipeline uses the network, and how to run it in a sensitive
or air-gapped environment with confidence. For the step-by-step setup see `INSTALL.md`; for the HMM's
provenance and an optional rebuild recipe see `docs/PUBLIC_RELEASE_DATA.md`.

## 1. What this release is

The public release ships code and its own small governed data. The curated Pfam HMM is **not bundled** — you provision it yourself (see `docs/EXTERNAL_ASSETS_GUIDE.md`). Every shipped file
is **not bundled** (acquire per `docs/EXTERNAL_ASSETS_GUIDE.md`); test fixtures ship in place, so there are minimal
downloads needed to run the pipeline or the test suite. This is the same content as the code tier. See
`NOTICE` for third-party data attribution (Pfam is CC0; the Micromonospora humida fixture is public
genome data). The engine also runs fine if the HMM is ever removed — the scanner falls back to regex
pattern matching — but you get the full HMM-based scan out of the box.

## 2. Setup in brief

Full numbered steps are in `INSTALL.md`. In short: **Python 3.10+** for the core engine (only the
optional prebuilt add-on wheels need Python 3.12 on Linux x86_64 — see §3), `pip install -r requirements.txt`,
then optionally `pip install '.[render]'` (cairosvg, so compiled-PDF SVG figures embed) and
`pip install '.[all]'` for the figure/bio stack. Run `python -m mamey doctor` to check the
environment, then `python mamey_run.py run --input-zip <antiSMASH_result.zip> --outdir runs/`.

## 3. Data that ships, and the one thing you bring yourself

To run HMM domain scans you must first provision the Pfam HMM yourself (see `docs/EXTERNAL_ASSETS_GUIDE.md`); every shipped data file
is **not bundled** (acquire per `docs/EXTERNAL_ASSETS_GUIDE.md`); test fixtures ship in place. The HMM is rebuildable
if you ever want a newer Pfam-A: `hmmfetch` the 35 accessions in `SCANNER_PFAM_MANIFEST.md` from Pfam-A
(`ftp.ebi.ac.uk`), then `hmmpress` — full recipe in `docs/PUBLIC_RELEASE_DATA.md`. If the HMM is ever
removed, the scanner falls back to regex and HMMER-dependent cells report `NEEDS_HMMER_DOMTBLOUT`.

The one thing the release cannot contain is your **antiSMASH input** — the result ZIP the pipeline
consumes. You produce that with antiSMASH (a local install or the web service at
`antismash.secondarymetabolites.org`) before running Sapote-Mamey; the tool does not fetch it for you.

## 4. What the tool does over the network at runtime

This is the part most relevant to a controlled environment. **The pipeline is offline by default and
makes no network calls of its own.** The deterministic engine (Mamey), the Sapote judgment layer, the
gates, KCB/KnownClusterBlast triage, figures, packaging, and reporting all run entirely locally on
inputs you provide. There is **no telemetry, analytics, or phone-home** — the timing receipts written
into each package are local JSON files, never transmitted, and nothing about your data or usage leaves
the machine.

The **only** feature that touches the network is the **optional online BLASTp panel**, and only when
you explicitly invoke it:

| Command | Endpoint it contacts | Purpose | Zero-network alternative |
|---------|----------------------|---------|--------------------------|
| `mamey blastp-online …` | `blast.ncbi.nlm.nih.gov/Blast.cgi` (NCBI web BLASTp) | Submit a per-BGC protein panel and poll for hits | `ingest-blastp` a pre-run hit-table |
| `mamey blastp-ebi …` | `www.ebi.ac.uk/Tools/services/rest/ncbiblast` (EBI BLAST REST) | Same, via the EBI service | `ingest-blastp` a pre-run hit-table |

If you never run those two subcommands, the tool opens no network connections. The BLASTp evidence
channel is fully available offline: run BLASTp wherever you like (for example the NCBI web UI on a
connected machine), download the **Hit Table (CSV)** and the **Single-file XML2**, and ingest them with
`mamey ingest-blastp --hit-table <hits.csv> --xml <aln.xml> --package <pkg>`, which uses no network at
all. This is the recommended path and the one the exemplar cards are built from.

### A note on the contact email these services request

Both NCBI and EMBL-EBI ask automated users of their BLAST services to identify themselves with a
contact email so they can reach you about heavy or misbehaving usage. **Sapote-Mamey ships with no
email baked in** — the tool never sends an address it invented, and by design there is no default
identity in the code. This is deliberate: the release must not transmit anyone's contact details on
your behalf.

The consequence is that **you supply your own email when you use the online channels**, and it is good
citizenship (and, for EBI, required) to do so:

- `mamey blastp-ebi --submit` **requires** `--email you@example.org`; the command refuses to submit
  without a real address (a placeholder or empty value is rejected before any network call). EBI's Job
  Dispatcher uses it for fair-use contact and caps concurrent jobs, which the command also enforces.
- `mamey blastp-online` (NCBI) runs without an email, but NCBI's URL-API guidance asks programmatic
  users to include one and to keep a courteous request cadence. If you run more than an occasional
  panel, provide your address and stay within NCBI's usage limits so your IP is not throttled.

If you would rather not contact these services at all, use the offline `ingest-blastp` path above — it
needs no email and no network.

## 5. Running fully air-gapped

To run with zero network access:

1. The Pfam HMM is **not bundled** (see `docs/EXTERNAL_ASSETS_GUIDE.md`); acquire or rebuild it before any HMM step for
   HMM-based scanning — it works offline out of the box. (Only if you deliberately removed it would you
   need to carry a copy in, or rely on the regex fallback / antiSMASH `--fullhmmer` output.)
2. Produce your antiSMASH result ZIP(s) on a connected machine or a local antiSMASH install.
3. For BLASTp evidence, run BLASTp externally and bring in the Hit Table (CSV) + XML2, then use
   `ingest-blastp` (no network).
4. Everything else — extraction, boundary/assembly tiering, KCB triage, Mode B cards, figures,
   packaging, gates, and reporting — runs locally with no network.

Under this setup the tool never initiates a connection; the only network use is the fetching you do
yourself, on your terms, ahead of time.

## 6. Graceful degradation summary

| Missing | Effect | Fix |
|---------|--------|-----|
| `scanner_pfam.hmm` — **not bundled (operator-acquired)** | Only if you removed it: scanner uses regex; HMMER cells report `NEEDS_HMMER_DOMTBLOUT` | Nothing needed; rebuild from Pfam-A (§3) only for a newer Pfam |
| cairosvg (`render` extra) | Compiled-PDF SVG figures are dropped, not embedded; render still succeeds | `pip install '.[render]'`, or install a system `rsvg-convert`/`inkscape` |
| figure stack (`matplotlib`/…) | Figure generation is skipped | `pip install '.[figures]'` or `'.[all]'` |

Nothing in this list blocks a run from reaching completion; each is a graceful fallback, not a failure.
