# De novo semantic-validation fixtures

These authored GenBank, FASTA, query-context and configuration inputs are
synthetic constructions. They are not RiPPER results or enzyme/precursor
function evidence. The configuration is symbolic and is not runnable.

The record contains an annotated 300-aa self-query CDS and a deliberately
unannotated 20-aa ORF. Tests check input parsing, translation and coordinate
binding; they do not establish short-ORF detection. Reverse-strand, boundary
and refusal cases are generated from these local files in isolated test roots.
The tests require no external lane folder or empirical reference sequence.
