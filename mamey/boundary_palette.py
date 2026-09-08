"""boundary_palette.py — single source of truth for BGC boundary-tier colours.

Two colour schemes exist in the figure set today for the SAME concept — a BGC's boundary
tier (Interior / Edge / Full-contig):

  - BLUE_GRADIENT  (used by figures_smoke): darker blue = more interior.
  - TRAFFIC_LIGHT  (used by figures_sapote / the reader-facing brief set):
                   green = Interior (trustworthy) → orange = Edge → red = Full-contig.

Before this module the two lived as independent literals in two files, so the same tier was
dark-blue in a smoke figure and green in a brief figure — an accidental house-style drift that
a future palette edit would have to chase across files. Centralising both here makes a colour
update a one-place change and makes the divergence explicit and named rather than hidden.

`CANONICAL` names the recommended scheme for NEW figures — TRAFFIC_LIGHT, because it is the
reader-facing brief scheme and is semantically meaningful (trustworthy → untrustworthy).
Unifying figures_smoke onto CANONICAL would CHANGE smoke's rendered colours, so that is a
deliberate design decision left as a one-line opt-in (`from .boundary_palette import CANONICAL
as _BOUNDARY_COLOURS`), not applied here — this module is a no-op centralisation.

PC-2 decision (v9.7.253 audit — recommended, pending final sign-off): KEEP figures_smoke on
BLUE_GRADIENT. Rationale: smoke figures are internal/diagnostic, not reader-facing; the
reader-facing brief set already uses CANONICAL (TRAFFIC_LIGHT), where the trustworthy→
untrustworthy semantics matter most; and the blue-vs-traffic-light contrast doubles as an
at-a-glance "diagnostic figure vs deliverable figure" signal. Flipping smoke would also change
rendered output that existing smoke tests observe. To flip anyway, replace the import in
figures_smoke.py with `from .boundary_palette import CANONICAL as _BOUNDARY_COLOURS` (one line).
"""

# Blue gradient (figures_smoke): darker = more interior. Includes the underscored/camel
# tolerant variants the smoke reader accepts.
BLUE_GRADIENT = {
    "Interior":    "#1f3a93",
    "Edge":        "#4c6ef5",
    "Full-contig": "#a3bffa",
    "Full_contig": "#a3bffa",
    "FullContig":  "#a3bffa",
}

# Traffic light (figures_sapote / brief): green→orange→red = trustworthy→untrustworthy.
TRAFFIC_LIGHT = {
    "Interior":    "#1b8a5a",
    "Edge":        "#e0902b",
    "Full-contig": "#cf6b5a",
}

# Recommended scheme for new figures (see module docstring). Not force-applied to smoke.
CANONICAL = TRAFFIC_LIGHT
