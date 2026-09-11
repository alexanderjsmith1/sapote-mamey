# Incoming figure markdowns (from other chats)

Workflow for figures built elsewhere:

1. In the figure chat, have it emit a **markdown file** describing the figure (caption, what it shows, the data
   source) and, where possible, the **figure image** (PNG/SVG) alongside.
2. Drop both here: `incoming_figures/<name>.md` (+ `<name>.png`).
3. Either run `bash tools/build_all_deliverables.sh` (compiles the new md to PDF + Word automatically), or hand
   the markdown back in the analysis chat to be folded into the matching report (e.g. a new panel in the
   size-by-type or ecological-synthesis analysis).

Keep figure markdowns self-contained (relative image paths, a one-line data-source note) so they slot into any
report. Private AS-prefixed identifiers must be scrubbed before a figure enters a public (CODE/SID) release.
