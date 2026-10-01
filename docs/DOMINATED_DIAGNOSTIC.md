# Experimental dominated diagnostic report

The report appears in parsed antiSMASH evidence when TIGRFAM extraction is requested.
Proposed defaults flag a tier-1 diagnostic with bitscore at most 30 and a different domain on the same CDS
whose E-value is at least 20 orders of magnitude smaller. These values are uncalibrated and report-only.
All tier-1 hits, scores, confidence calls and existing diagnostic extraction remain unchanged.
Unrecognized or ambiguous TIGRFAM region locations are not used as competing evidence.
Missing, zero, non-finite and malformed E-values are unassessable. An empty flag list does not rule out housekeeping.
Different HMM families have different score distributions; this flag invites review rather than identifying function.
Calibrate sensitivity and false warnings on held-out public genomes before any scoring or gate proposal.
