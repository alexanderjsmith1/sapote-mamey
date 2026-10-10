# Optional bacterial marker-debug fixtures

The historical references here are BGC0002086 and LC529898.1. This inspected .447 directory contains this README only; the two GBK and two matching KnownClusterBlast TXT files required by `tests/test_b2_phase2_bacterial_pks_marker_debug.py:15–29` are absent. Tests needing them explicitly skip; the separate global-detector inactivity assertion can still run (`:32–36`). No marker evidence or positive-control result follows from this directory's presence.

When separately supplied/admitted, these tests inspect annotation/KCB support and caution logic; they do not activate global HMM/DIAMOND/BLASTp backends or establish product identity. Historical reference names are not complete strain/contig/region/BGC identities; retain exact source/hash and identity holds rather than inventing them. This documentation audit supplied no payloads and ran no tests.

See [fixture scope](../../README.md) and [reference source policy](../../../../resources/reference_seed_inputs/README.md).
