# Export a Mode B card to Word and PDF

`modeb-export` turns a finished Mode B card (Markdown) into a Word file and a PDF. It formats the card. It does not verify it. Run `verify-modeb` first; see the [walkthrough](MODE_B_USER_WALKTHROUGH.md), step 5.

## Run it

From the bundle root, with the same `python` you used for `doctor`:

```text
python mamey_run.py modeb-export reviews/EXAMPLE-mode-b.md --outdir reviews/EXAMPLE-export --format both --theme evidence_dossier
```

- `--format` is `docx`, `pdf` or `both` (default).
- `--theme` is `evidence_dossier` (default), `field_notebook`, `dark_lab` or `minimal_clinical`.
- `--outdir` defaults to the card's own folder. Use a new folder: files with the same name are replaced, and nothing is kept or checked for you.
- The input can be a folder instead of one file. Then every top-level `*.md` in it is exported, except `PROVENANCE.md`. The command cannot tell a finished card from a template, so point it at a folder that holds only finished cards.

## What you should see

```text
card: reviews/EXAMPLE-mode-b.md
  docx: reviews/EXAMPLE-export/EXAMPLE-mode-b.docx  (48211 bytes; python-docx 1.2.0)
  pdf: reviews/EXAMPLE-export/EXAMPLE-mode-b.pdf  (91034 bytes; reportlab (via mamey.markdown_pdf))
```

The byte counts and engine names will differ. Each written format gets one line like this. Output files use the card's file name.

| Exit code | Meaning |
|---|---|
| 0 | Every requested format was written. |
| 1 | A requested format was skipped or refused, or a folder held no cards. With `--format both`, both files must be written. |
| 2 | The input file does not exist. |

A skipped format prints `SKIPPED` and a reason on stderr. A refusal prints `REFUSED_CLAIM_SAFETY`; see below. Other read or render errors can stop the command part-way through a folder, leaving earlier files in place. Check each file exists.

## Setup

- PDF needs `reportlab`. Word needs `python-docx` and `lxml`, which come with the `documents` extra (see [prerequisites](PREREQUISITES.md)). To check, run `python -c "import reportlab, docx, lxml"`; it prints nothing when all three import. A missing module gives `SKIPPED` for that format (`SKIPPED_NO_DOCX` or `SKIPPED_NO_REPORTLAB`).
- PDF output comes from the packaged `mamey.markdown_pdf` renderer. No outside PDF toolchain is used.

## If the export is refused

The exporter scans the card for claim-safety problems, such as wording that states a compound or activity as fact. If it finds one, it prints `REFUSED_CLAIM_SAFETY` and writes nothing new for that card. Edit the flagged phrase in the card so it matches the evidence, then run it again.

With a folder as input, each card is checked and exported on its own. A refused card does not stop the others: cards before and after it can still be written, and the command then exits 1. Read the `card:` line and format lines printed for every card, and check which output files exist before you use the folder.

## What the export makes

It writes one DOCX and one PDF per card, nothing else: no manifest, evidence CSV, wide-table companion or thumbnails. The PDF holds the card's own prose, not only its tables. Do not cut a card down to its tables before you export it unless a table-only document is what you want.

## What the export does not do

It does not check sections, the gene roster or package binding. It writes no hash or verifier record. Keep the card's hash, the package and source hashes, your `verify-modeb` command and its report, and the output hashes in your own run record. The embedded assets are separate inputs; bind them too. Open the PDF and look at the pages before you call the layout checked.
