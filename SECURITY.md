# Security Policy

## Scope
Sapote-Mamey is a research workflow that reads genome-mining output and emits interpretive,
claim-safe reports. It ships code and small governed reference data only — no third-party
databases, tools, or genomes. It runs locally and makes no outbound network calls in its core
extraction path.

## Reporting a vulnerability
Please report suspected vulnerabilities privately via the repository's security advisory feature
(GitHub → Security → Report a vulnerability) rather than a public issue. Include the version
(`mamey --version` / `BUILD_STAMP.txt`), the affected file, and a minimal reproduction.

We aim to acknowledge within a reasonable window and to coordinate a fix and disclosure timeline.
Because the tool is offline-by-default and processes the operator's own inputs, most risk relates
to parsing untrusted archive/JSON inputs; reports about archive traversal, resource exhaustion, or
unsafe deserialization are especially welcome.

## Supported versions
The latest released bundle is supported. Older cuts are superseded by design (version lineage is
tracked in `RELEASE_MANIFEST.md` / `docs/ENGINE_LINEAGE.md`).
