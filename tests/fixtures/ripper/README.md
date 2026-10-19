# Synthetic adapter fixtures

These IDs, sequences, columns, score, configuration, revision and completion declarations were authored for adapter tests. They are not authentic RiPPER output, NCBI accessions, real BGCs, a model benchmark, or a live tool success. The zero commit placeholder is deliberately restricted to the synthetic provenance example. Never submit these IDs. The second query has no retained row to exercise the scoped no-candidate state.

The COMPLETE fixture also binds the exact queries.json and columns.json bytes.
Imported fixture outputs use ADMITTED_SYNTHETIC and NOT_EXECUTED_SYNTHETIC, while
all candidate BGC membership remains UNVERIFIED. Tests that fabricate an operator
receipt exercise OPERATOR_DECLARED_UNATTESTED only; they are not live evidence.
