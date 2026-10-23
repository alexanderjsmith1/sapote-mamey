# Manuscript revision workflow

This guide covers one revision round of a manuscript kept as Markdown sources, one file per chapter or section.
The author marks up a printed copy, a reviewer reads the same version, and the two sets of comments become one answerable
Word ledger. Answers turn into staged edits. The edits are checked, applied to a new working copy, and recorded.
A before/after change log closes the round.

The tool is `tools/manuscript_revision.py`. Its Word steps need python-docx, which ships in the `documents` extra
(`pip install 'mamey[documents]'`). Without it, the Word subcommands exit 3 with the install hint. The text steps
(`apply`, `check-numbers`, `scan-names`) need only the standard library.

## The steps

1. **Freeze the version.** Copy the sources of the printed version into a new working-copy folder. Never edit the printed
   version. A version is immutable once it is printed or sent; every fix goes forward into the next working copy.
2. **Notes.** Transcribe the author's marks into a notes table (Appendix A). Mark a row `ASK` when it needs the author.
   A word that could not be read is written `[?]`, and the row counts as `ASK`.
3. **Findings.** Triage each reviewer finding into a findings table (Appendix B), typed `FIX`, `CHECK` or `RULE`, each with a
   recommendation. Name in `overlap` any note that covers the same passage.
4. **Ledger.** Build the Word ledger and send it to the author.

   ```bash
   python tools/manuscript_revision.py ledger --notes notes.md --findings findings.tsv --packages packages.tsv \
       --author-label Author --reviewer-label Reviewer --title "Revision ledger, round 1" --out ledger_r1.docx
   ```

   Part A holds the author's notes, Part B the reviewer findings grouped by `group`, and Part C the reviewer's revision
   packages. Where a note and a finding cover the same passage, each row names the other. The last column of each table is
   the answer column. `R` means "take the recommendation". A blank answer on a `FIX` row or a clear note means "go ahead".
5. **Answers.** Read the answered ledger back against the issued copy.

   ```bash
   python tools/manuscript_revision.py read-answers ledger_r1_answered.docx --original ledger_r1.docx --out answers_r1.tsv
   ```

   The tool refuses, and writes nothing, when any cell outside the answer column differs from the issued ledger, or when a
   row or table was added or removed. Ask the author to move the text into the answer column, then read it again.
6. **Asks-only rounds.** Reply to each answer in a responses table (`id | status | text`). Rows whose status contains
   `NEED` still need the author. Build the next round with only the open questions.

   ```bash
   python tools/manuscript_revision.py asks --notes notes.md --findings findings.tsv --packages packages.tsv \
       --answers answers_r1.tsv --responses responses_r1.md --title "Open questions, round 2" --out asks_r2.docx
   ```

   The round keeps responses still marked `NEED`, unanswered `ASK` notes, unanswered `RULE` findings and unanswered packages.
   It drops answered rows, clear notes, and every `FIX` and `CHECK` finding, because those are the reviser's to do.
   `--drop-regex` removes `ASK` notes that match a pattern (for example ink showing through from the other side of a
   page); the dropped ids are listed in the round's opening paragraph. Row ids match the full ledger.
7. **Staged edits.** Draft edit files (Appendix C) and fill record values (Appendix D). Check every edit file before it is
   applied:

   ```bash
   python tools/manuscript_revision.py apply edits_intro.json --root work_v2 --dry-run
   python tools/manuscript_revision.py check-numbers edits_intro.json --root work_v2 --source records/plot_counts.tsv
   python tools/manuscript_revision.py scan-names work_v2/*.md --patterns internal_names.txt
   ```

   The dry run must report `refused 0`. `check-numbers` lists each edit whose replacement holds a number that is in neither
   its find text, its document nor any `--source` file. Each flagged number needs a named source or is removed.
   `scan-names` lists internal names in prose (see "Internal-name patterns" below).
8. **Apply.**

   ```bash
   python tools/manuscript_revision.py apply edits_intro.json --root work_v2
   ```

   Each edit's `find` must occur exactly once in its document. One refused edit holds back every edit to that document, and
   the file is left unchanged. An edit whose `find` is gone and whose `replace` is present is reported as already applied,
   so a rerun is safe. Each applied edit is appended, with a time stamp, to the change record (`<root>/CHANGES.jsonl`, or
   `--record`). The record is append-only.
9. **Change log.**

   ```bash
   python tools/manuscript_revision.py changelog work_v2/CHANGES.jsonl --first 1 --doc-labels doc_labels.tsv \
       --title "Version 1 to version 2 changes" --out changes_v1_to_v2.docx
   ```

   One row per record line from `--first`, with the document label, the changed stretch before and after (shared text
   trimmed to `--context` characters either side), the reason with its ledger row, and the record line number.
10. **Build.** Build the new version from the working copy with the project's usual document build. Then freeze it (step 1).

## The rules

- **Draft, check, apply.** An edit file is drafted first, checked second (`apply --dry-run`, `check-numbers`, `scan-names`),
  and applied last. A drafter never applies its own file.
- **No value without a source.** Every new number, date, count, version or accession names the record it came from in the
  edit's `why`. A value that cannot be found is held, never estimated.
- **Versions are immutable.** Never modify a printed or sent version. Fix forward in a new working copy.
- **Held edits are kept.** An edit that is not applied goes into a held file, one line per row:
  `| row | reason | what is needed |` (record lookup, figure redraw, rerun, new citation, the author's answer).
  Nothing is dropped silently.
- **The author's notes win.** When a reviewer finding touches text the author already changed, keep the author's wording.
- **Keep comments and notes.** `<!-- ... -->` comments and bracketed author notes (`[TAG: ...]`) stay unless the row removes them.

## Input formats

Tables are TSV with a header line, or a Markdown table with a header row (`\|` escapes a pipe inside a cell).
Header names are matched without regard to case. Extra columns are allowed.

| Input | Columns |
|---|---|
| Notes | `id`, `location`, `note`, `action`, `status` (`ASK` or `clear`; `[?]` in note or action counts as `ASK`) |
| Findings | `id`, `group`, `location`, `finding`, `type` (`FIX`, `CHECK`, `RULE`), `recommendation`, `overlap` (note ids) |
| Packages | `id`, `title`, `covers`, `codes`, `recommendation` |
| Answers | `id`, `answer` (written by `read-answers`) |
| Responses | `id`, `status`, `text` |
| Document labels | `prefix`, `label` (a document whose file name starts with `prefix` shows `label` in the change log) |

An edit file is a JSON list:

```json
[{"doc": "01_introduction.md", "find": "<exact current text>", "replace": "<new text>",
  "ledger": "Notes", "row": "N012", "why": "<instruction or source, short>"}]
```

`doc` is relative to `--root`; absolute paths and `..` are refused. Several rows that touch one sentence go into one edit,
with their ids joined by `+`. Keep each `find` as short as uniqueness allows.

## Internal-name patterns

`scan-names` ignores HTML comments, bracketed notes whose tag is upper case (`[TAG: ...]`, narrowed with `--note-tag`) and
Markdown link and image targets. The built-in patterns flag paths, run numbers, version and build strings, data and code
file names, and snake_case identifiers. Project names, such as tool names, build names and the names of assistants that
helped with the revision, go in a patterns file. Each line is either `label<TAB>regex` or one literal name. Lines starting
with `#` are comments. `--patterns` adds to the built-in set; `--replace-defaults` uses only the file.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Clean |
| 1 | Refused edits, flagged numbers or internal-name hits |
| 2 | Bad input, or an answered ledger changed outside the answer column |
| 3 | python-docx missing for a Word step |

## Appendix A. Brief: transcribe handwritten notes

- Read every photo or scan of the marked-up print, in page order. Record the page number printed on the page.
- One row per mark: `id`, `location` (page and place, such as "p12, paragraph 3" or "p40, Figure 2 caption"),
  `note` (the mark as read, quoted), `action` (what will be done), `status`.
- Quote the note as written. Write `[?]` for any word that cannot be read with confidence. Never guess a word silently.
- Use `ASK` when the note asks something, offers a choice, or cannot be read. Start such actions with "Ask:" and give a
  concrete recommendation.
- Flag faint marks that may be ink showing through from the other side of the page. They become `ASK` rows and can be
  dropped later with `asks --drop-regex`.
- Report: photos read, rows written, rows marked `ASK`, rows with `[?]`.

## Appendix B. Brief: triage reviewer findings

- Read only. Do not edit the manuscript or the review.
- One row per finding, every finding included, in review order: `id`, `group` (the document it is about), `location`,
  `finding` (one or two short sentences), `type`, `recommendation`, `overlap`.
- `FIX`: wording, consistency or labeling that can change with no new information. The recommendation gives the exact change.
- `CHECK`: needs a record, table or source looked up first. The recommendation says what to check and where, then what to change.
- `RULE`: a scientific judgment, a scope choice, or something only the author knows. The recommendation starts
  "Recommend:" and takes a concrete position, never a bare question.
- `overlap`: the id of an author note that covers the same passage or figure. Claim an overlap only when it is clearly the same.
- Never recommend new experiments or new analyses. Prefer rewording, qualifying, or reporting what exists.
- Report: rows per review (equal to the findings in it), counts of `FIX`, `CHECK` and `RULE`, overlaps found.

## Appendix C. Brief: draft edits for one document

- Inputs, read only: the current working copy of the document, its findings, the author's answers and the change record.
  Never undo or rework an edit already in the change record.
- Draft every `FIX` row, every `RULE` row the author accepted, every clear author note, and every answered row marked to go
  ahead. Draft a `CHECK` row only when the manuscript text itself answers it (an inconsistency between two places).
- Write one edit file in the format above, and one held file for every row not drafted, with the reason.
- Check the file with `apply --dry-run` (it must report `refused 0`), `check-numbers` and `scan-names`. Never apply it.
- Writing: plain direct sentences, consistent spelling, no filler. No internal tool names, run numbers, build numbers or
  file paths in prose. Never add a citation that is not in the reference list; a missing citation is held. Never invent a
  number; a number that must be looked up is held.
- Report: rows drafted, rows held by reason, the dry-run line.

## Appendix D. Brief: look up record values

- Read only. Never edit the manuscript, a record or a run folder.
- For each held row that needs a value (a count, a date, a version, an accession, a setting), find it in the project's own
  records, in the order the project names.
- A value counts only when the file holding it was opened. Give the path and the line, cell or key in the edit's `why`.
  If two records disagree, report both and draft nothing for that row.
- Never invent, estimate or round a value. "Not found after checking X, Y and Z" is a valid answer. No new analysis, no
  reruns, no downloads. Counting rows in an existing table is fine; say what was counted.
- Write the drafted edits in the edit format and one line per looked-up row: `| row | value or "not found" | source | drafted |`.
  Check the edits as in Appendix C.
