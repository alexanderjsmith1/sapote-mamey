# Scanner recipe: historical plan with an interface hold

Retired in v9.7.458 and kept as a record. Settings and commands may be out of date. Current guide: [Wheelhouse README](../../../Wheelhouse/README.md).

The earlier recipe supplied `--proteome`, `--registry` and `--hmm` to `Wheelhouse/engine/pyhmmer_scanner_engine.py`. That command is unsupported by the shipped implementation. Its main block only prints “pyHMMER scanner engine loaded” and does not parse arguments, scan proteins, apply registry gates or write an AB/AF profile. A normal exit would not prove any scanner ran.

The module imports pyhmmer and Biopython, extracts translated CDS of at least 40 amino acids from matching `*.region*.gbk` files, collects annotated domain sequences and constructs HMMs, using pyfamsa for multiple sequences. The extractor is not a whole-genome proteome reader and can encounter the same CDS in multiple overlapping region files. A `.faa` path is not accepted by this extractor.

Hold: there is no implemented registry-scan/profile dispatcher here. Do not fabricate an output profile or promote registry `test_status` after loading the helper. Find the selected task's actual supported pipeline interface and source-bound evidence route before authorizing a run. Dependencies, HMM payloads, input identities and gate validation are separate prerequisites; input FASTA alone does not clear this hold.

Capacity hypotheses remain distinct from product or activity evidence. This source review did not run the helper, build models or execute searches. See [Wheelhouse inventory and writes](../../../Wheelhouse/README.md) and [external-data routes](../../EXTERNAL_DATA.md).
