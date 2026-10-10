# Scanner recipe: historical plan with an interface hold

The earlier recipe supplied `--proteome`, `--registry` and `--hmm` to `Wheelhouse/engine/pyhmmer_scanner_engine.py`. That command is unsupported by the shipped implementation. Its main block only prints “pyHMMER scanner engine loaded” (`:54–55`) and does not parse arguments, scan proteins, apply registry gates or write an AB/AF profile. A normal exit would not prove any scanner ran.

The module imports pyhmmer and Biopython (`:2–5`), extracts translated CDS of at least 40 amino acids from matching `*.region*.gbk` files (`:8–22`), collects annotated domain sequences (`:24–38`) and constructs HMMs (`:40–52`), using pyfamsa for multiple sequences. The extractor is not a whole-genome proteome reader and can encounter the same CDS in multiple overlapping region files. A `.faa` path is not accepted by this extractor.

Hold: there is no implemented registry-scan/profile dispatcher here. Do not fabricate an output profile or promote registry `test_status` after loading the helper. Find the selected task's actual supported pipeline interface and source-bound evidence route before authorizing a run. Dependencies, HMM payloads, input identities and gate validation are separate prerequisites; input FASTA alone does not clear this hold.

Capacity hypotheses remain distinct from product or activity evidence. This source review did not run the helper, build models or execute searches. See [Wheelhouse inventory and writes](../README.md) and [external-data routes](../../docs/EXTERNAL_DATA.md).
