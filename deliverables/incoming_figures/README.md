# Incoming figure evidence handoff

Treat incoming Markdown and artwork as candidate inputs until reviewed. Keep the Markdown and referenced images together, using resolvable relative image paths. Include:

- Figure ID/version, owner, requested destination and intended audience.
- Input package/bank/table paths, SHA-256, schema/version, exact roster and denominator.
- Complete `strain / full node-or-contig / region / BGC alias` for every individual locus.
- Builder/source version, actual command, output image hashes, transformations and relevant input rows.
- Caption, literal legend, missingness, claim limits, review status and unresolved holds.

Placing files here does not integrate, validate or approve a figure. Review the source/image identity and caption together before copying into a report. Use fresh output names and retain the evidence receipt. Publication/privacy approval must follow the actual package/profile and authorized audience; scrubbing a prefix is not a release check.

For requested single-file conversion, see the [deliverables index](../README.md). `tools/build_all_deliverables.sh` is a bulk regeneration command: it reruns four generators, overwrites the shared status log and converts all eligible Markdown below `deliverables/`, including templates and older files. It is unsuitable as a narrow import/preview operation on the immutable baseline. PDF/Word conversion success does not demonstrate source correctness or visual QA. Markdown-only handoffs need no conversion.
