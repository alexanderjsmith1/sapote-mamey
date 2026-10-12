# Owner consumption of a validated release record

`tools/release_owner_consumer.py` is an explicit owner adapter for the optional
partitioned release workflow. It reads the same hash-bound `workflow.json` that
generates the workflow status pages. It does not infer authorization from tests.
It never describes an external program's zero exit status as a seal or publication.

The operator must supply `--owner-authorized`, the root receipt and its SHA-256,
the current source, a new external evidence directory, an unoccupied seal target,
and an executable external owner consumer with its own pinned SHA-256. Source,
workflow, evidence and target locations must be separate. Existing destinations
are preserved. The adapter never modifies the existing external owner wrapper.

Before the external program can run, the adapter reuses the independent release
workflow verifier, verifies the final source partition receipt in a freshly
admitted environment, checks the complete source import record, and follows the
root's active output inventories to the exact CODE ZIP and extracted-artifact
receipt. It independently verifies the extracted final partition receipt and
complete import record. Root, source, extracted source, archive, receipt and
consumer bindings are rechecked before invocation. Counts or a PASS label alone
are insufficient.

The new consumer interface is:

```text
OWNER_PROGRAM --verified-release-record RECORD.json \
  --verified-release-record-sha256 SHA256 --seal-target TARGET
```

The read-only record includes the original root path/hash, declared build
context, exact archive path/hash, both final-suite and complete-import proofs,
and explicit operator attestation. The external owner program must implement
this interface, validate those record bytes, and retain its existing owner,
identity, placement, seal and publication gates. The historical `.449` wrapper
does not implement this interface and must not be passed unchanged. An external
consumer needs separate owner review; this adapter grants no waiver or adoption.

The adapter records `OWNER_CONSUMER_COMPLETED` only for a clean watched return
with unchanged admitted inputs. `seal_status` remains
`NOT_ESTABLISHED_BY_ADAPTER`; actual seal evidence belongs to the owner program.
Failure or interruption retains the evidence and partial owner outputs. An
unreturned watch records invocation as unknown. It is never automatically retried
or rolled back. Review retained evidence and obtain a new bounded owner decision
before any recovery. Linux/Python 3.12 and release adoption holds remain separate.

The portable unit fixtures use fake verifiers and a fake watched consumer to
exercise this adapter's exact wiring and refusals. They do not replace complete
workflow, partition, import or real owner seal validation.
