# Offline paper reference audit

`tools/paper_reference_audit.py` checks explicit citation and caption keys in supplied
DOCX files. It reads the cached visible text from paragraphs, table cells, text boxes,
footnotes, endnotes, headers and footers. It never changes documents, updates Word
fields, resolves a DOI or contacts a service.

```bash
python tools/paper_reference_audit.py main.docx supplement.docx --style author-year
python tools/paper_reference_audit.py main.docx --style numbered --strict
python tools/paper_reference_audit.py main.docx supplement.docx --reference-scope document
```

The tool prints JSON on stdout. Redirect it to a file outside your original evidence. The JSON
holds each input's absolute path, SHA-256 and scope (main or supplementary). It can also hold excerpts
from your files, so keep it with the manuscript.

## Read the result

Look at `status`, `parsing_holds`, `missing_references`, `uncited_references`, `undefined_callouts`
and `uncalled_captions`. This is the output for a document with no reference list (shortened):

```text
"status": "INCOMPLETE",
"references_parsed": 0,
"missing_references": [],
"parsing_holds": [
  {"code": "NO_REFERENCE_SECTION", "detail": "No recognized references in supplied documents."}
]
```

Empty finding lists do not mean a clean manuscript here. A hold means the tool could not read part of
the text, so read `parsing_holds` first. Each finding has a `confirmed` flag. Confirmed means the key
is absent from the files you supplied, in the syntax this tool reads. It does not show that a
reference exists in the literature or supports the sentence.

| Exit code | Meaning |
|---|---|
| 0 | The report was written. Without `--strict`, this holds even when it lists findings or holds. |
| 1 | `--strict` only: confirmed findings. |
| 2 | Parsing holds (`--strict`), or an input was refused (any mode). |

By default the reference scope combines all supplied files. Use `--reference-scope document` when
numbered lists restart in each document. S-prefixed figure and table numbers stay separate from main
numbers. Citations found only in a supplementary file count toward the list if you supply that file.

## Supported syntax

Use a `References`, `Bibliography` or `Literature cited` heading, optionally prefixed
with `Supplementary` or `Supporting`, and one reference per paragraph. A subsequent
Word Heading style, `Supplementary information`, `Supplementary material`,
`Supporting information`, `Supporting material`, `Figure legends` or `Table legends`
ends that reference section. Other plain-text headings require manual inspection.
Only the main document part supplies a reference list; notes and headers are citation
sources. Reference list headings are recognized by their visible text.

Author-year reference paragraphs use surname-first author lists or full corporate
names before the first 1800–2099 year. `Aylward FO, ... 2012`, `Aylward, F. O. (2012)`,
`Van Arnam EB ... 2018`, `van der Waals, J. D. (1873)` and
`World Health Organization. (2020)` retain the surname or full corporate name.
Trailing initials are removed from the first author; particles, apostrophes and
Unicode letters are preserved. Keys are Unicode-normalized and case-insensitive.
A parenthetical citation is read when it has a letter in any script and a year, as in
`(王 2020)`. A year joined to a name with no space, as in `(王2020)`, is held as
`UNSUPPORTED_CITATION` for manual review.
Initial-first references are held. A corporation containing an ampersand or a comma,
an abbreviated corporation, and different spellings need manual reconciliation.
The parser does not infer author aliases or interpret reference identity.

Parenthetical citations accept `(Aylward et al., 2012; Van Arnam, 2018)` and
`(Aylward, 2012a, 2012b)`. Narrative citations such as `Aylward et al. (2012)` use
an exact known surname or corporate suffix before the year. Unmatched narrative
authors remain parsing holds, because preceding prose does not establish a surname.
Two-author narrative forms, `ibid.`, `n.d.`, page locators, unusual nested groups,
parenthesized numbered citations and superscript citations need manual review.
Numeric square-bracket citations accept `[1, 2–3]`; bibliography entries use literal
`[1]`, `1.` or `1)`. Explicit `--style` avoids guessing from mixed reference lists.
Automatic Word numbering is held because list labels may be absent from visible XML.

Definitions begin with singular `Figure`, `Fig.` or `Table`, an explicit number and a
period or colon: `Figure S19. Caption` or `Table 1: Caption`. Callouts accept singular,
plural, lists and ascending ranges, including `Figs. S19, S20 and S21` and
`Tables 1–3`. A definition does not call itself out; citations to other figures in its
caption do count. Panel letters, uncertain caption syntax, descending ranges and
ranges of more than 200 numbers remain holds; a range containing exactly 200 numbers is accepted. List items need their own S prefix;
within `S19–21` the range carries the prefix. Chapter-style numbers are unsupported.
Definitions/callouts share the supplied document set, independently of reference scope.

## What makes a finding provisional

Unparseable reference rows downgrade missing-reference findings in that reference
scope to `UNRESOLVED_CITATION`. Duplicate reference keys are ambiguous. Unparseable
citation syntax prevents confirming uncited-reference findings in the affected scope.
Tracked changes, Word fields using cached text, superscripts, automatic numbering
and embedded altChunk content make absence findings provisional across the audit.
Unsupported figure syntax similarly makes figure/table absence findings provisional.
This is a bounded text parser; a clean supported-syntax result is not a general
proof of manuscript correctness or exhaustive recognition of every citation style.

## Limits

The tool reads each input once. If a file changes while it is read, the tool stops with
`SOURCE_CHANGED_DURING_READ`. Files are not locked against other writers. `xml_parts_sha256` lists
the XML parts it read. Each XML part may be up to 8 MiB and all parts together up to 32 MiB.
Duplicate ZIP members, DTD or entity declarations and non-UTF-8 XML are refused. ZIP content is never
extracted and external links are never followed. Unsupported or corrupt inputs are incomplete evidence.
