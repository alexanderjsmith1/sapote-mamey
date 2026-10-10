# Use the supplied Mamey bundle in an assistant session

“Standalone” means the local launcher selects the supplied `mamey/` package; it does not supply a Python runtime, storage, external tools or all dependency/data payloads. Confirm actual capabilities before an authorized execution. The launcher prioritizes the bundle package and checks cut/source cache provenance (`mamey_run.py:1–100`); record `BUILD_STAMP.txt` and input hashes rather than treating this filename or a model name as runtime identity.

Follow [the hosted-session route](RUN_MAMEY_IN_CHATGPT.md) and [batch continuation](CHATGPT_BATCH_PROTOCOL.md). Start with one bound input and choose resource limits from measured runtime and output size. Historical “1–3 strains” advice is not a fixed capability guarantee. A repeated placeholder ZIP in a command is not three independent inputs.

Use [the Master Walkthrough](../MASTER_WALKTHROUGH.md) for current commands, prerequisites and expected outputs. An existing master workbook is a separate schema-sensitive destination; preserve it before retrying or updating. Keep original inputs immutable, select a fresh run destination, and save complete packages before an ephemeral session ends. A combined archive is a requested handoff choice, not a guaranteed engine artifact.

## Read status without promoting evidence

`MAMEY_COMPLETE` is the validator's extraction-complete/judgment-pending branch after applicable gates. A depth-floor assignment alone does not guarantee it: identity, RGGMCI, reporting, exclusion, checksum and provenance failures can override the result (`mamey/validate.py:948–978,1003–1083`). Read individual gates and `package_status` alongside the overall status.

`PASS` is a validator result, not universal scientific or publication acceptance; some provenance conditions may be `NOT_EVALUABLE`. `MAMEY_FAILED`, `MAMEY_DEFERRED` and `MAMEY_SKIPPED` in an operator ledger are workflow descriptions, not replacements for the exact validator result. Preserve historical status strings and source versions; do not silently rewrite an old receipt to a current status.

Default package validation writes the mutable package-status receipt (`mamey/validate.py:1085–1106`). Preserve its returned result and any receipt-write failure; validation is not an entirely read-only operation. Mode B authoring, structure checks, evidence review and final adoption remain separate steps. A template does not complete an authored card.

Report actual file paths and counts, command/exit status, input identity/hash, validation findings, available evidence and remaining holds. Never call an unexecuted review a completed extraction. See [deliverable contract](../DELIVERABLE_CONTRACT.md) and [storage/handoff](../FILES_STORAGE_AND_HANDOFF.md).

## Version reference

Version reference: Mamey v1.9.174. Verify the loaded bundle before execution.

An assistant session cannot assume BLAST, HMMER, antiSMASH or their databases are installed or usable. Check the selected command’s actual dependencies and report unavailable execution as a hold.
