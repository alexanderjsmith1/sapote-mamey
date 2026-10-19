# Offline paper reference audit

`tools/paper_reference_audit.py` checks explicit citation and caption keys in supplied
DOCX files. It reads the cached visible text from paragraphs, table cells, text boxes,
footnotes, endnotes, headers and footers. It never changes documents, updates Word
fields, resolves a DOI or contacts a service. No Crossref option is implemented.

```bash
python tools/paper_reference_audit.py main.docx supplement.docx --style author-year
python tools/paper_reference_audit.py main.docx --style numbered --strict
python tools/paper_reference_audit.py main.docx supplement.docx --reference-scope document
```

JSON goes to stdout. Redirect it to a selected output path outside original evidence.
Each input has its absolute requested path, SHA-256 and main/supplementary scope
in the JSON. The reader opens each input once and hashes that descriptor before
and after parsing. A pathname or symlink replacement does not retarget the open
reader; the hash still describes the selected bytes. An observed in-place change
refuses with `SOURCE_CHANGED_DURING_READ`. `xml_parts_sha256` binds the exact XML
parts consumed. Archive hashing uses 1 MiB chunks and no full archive snapshot
is made. Each inspected XML part is bounded to 8 MiB and their total to 32 MiB;
parsed text/XML and ZIP metadata remain materialized.
Inputs are not locked against concurrent writers; these checks do not certify an
immutable historical source generation or exclude adversarial transient changes. The default
reference scope combines all supplied files. Use `--reference-scope document` when
numbered reference lists restart independently in separate documents. S-prefixed
figure/table numbers remain distinct from main numbers. Supplying a supplementary
file makes citations found only there count toward the applicable reference list.
Unsupplied files cannot establish whether a reference was cited elsewhere.

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

## Interpreting results

`missing_references`, `uncited_references`, `undefined_callouts` and
`uncalled_captions` carry a `confirmed` boolean. Confirmation means absence of the
parsed key within the supplied inputs and supported syntax. It does not establish
whether a reference exists in literature, supports a statement or has been correctly
interpreted. Check `parsing_holds` and `status` before using any absence finding.

Unparseable reference rows downgrade missing-reference findings in that reference
scope to `UNRESOLVED_CITATION`. Duplicate reference keys are ambiguous. Unparseable
citation syntax prevents confirming uncited-reference findings in the affected scope.
Tracked changes, Word fields using cached text, superscripts, automatic numbering
and embedded altChunk content make absence findings provisional across the audit.
Unsupported figure syntax similarly makes figure/table absence findings provisional.
This is a bounded text parser; a clean supported-syntax result is not a general
proof of manuscript correctness or exhaustive recognition of every citation style.

With `--strict`, exit 1 means confirmed findings, exit 2 means parsing holds or an
input refusal, and exit 0 means neither was found. Without `--strict`, a readable
report exits 0 even when it contains findings/holds; input refusal still exits 2.
XML reads are bounded to 8 MiB per part and 32 MiB across inspected parts. Duplicate
ZIP members, DTD/entity declarations and non-UTF-8 XML are refused. ZIP content is
never extracted and external relationships are never followed. Unsupported/corrupt
inputs remain incomplete evidence. JSON can contain excerpts from supplied files;
retain it within the same authorized evidence boundary.
