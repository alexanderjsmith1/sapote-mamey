# Validation records

The two `mibig_reference_kcb_accuracy_v9.7.165*` files record an older KCB family-call exercise
against bundle 9.7.165 / engine 1.9.104. The summary reports 14 clusters, eight with named ground
truth and eight correct named-family calls. Those counts do not measure current-cut whole-card
accuracy, coverage of all clusters, or general scientific validation.

Keep these records as historical evidence. For current software checks, read [tests/README](../tests/README.md)
and the selected cut's test logs and release receipt. A default pytest run and an explicit
slow/network-enabled release run have different scopes.

New validation evidence should identify the evaluated task, input accessions and hashes, exact
software versions, expected outcomes and their provenance, observed outcomes, exclusions, and the
run receipt. Keep raw reference data external where its licensing or size requires it. The
[reference-input policy](../resources/reference_seed_inputs/README.md) and manifest template describe
that boundary. A validation table's presence alone is not a passing result.
