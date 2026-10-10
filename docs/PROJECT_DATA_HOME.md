# Portable project data home

Run `python3 tools/init_project_data_home.py --root PATH --project-id NAME` to create a new pointer-first scientific data home.

The home separates authority, strain genomes, phylogeny, antiSMASH and Mamey outputs, bioassays, citations, manuscripts, deliverables, and superseded artifacts. Registers store locators and checksums. Large genome and antiSMASH files may remain in governed external stores; a register entry points to them without silently copying or reclassifying them.

The initializer refuses an existing target. It does not select scientific inputs, approve tree membership, alter evidence, or confer release authority.

## What initialization actually writes

The initializer creates ten numbered directories, nine TSV registers containing headers only, `PROJECT_HOME.json` and a README. It does not populate locators, compute evidence hashes, validate external stores or register existing packages automatically. A newly initialized empty register is not evidence that a scientific inventory is complete. Add source-bound rows as a separate task.

Use a new, explicit output root and a plain project identifier. The initializer refuses every existing target, including an empty directory. It creates missing parent directories; on a caught failure while writing the home, it attempts to remove the new home, but a process interruption can leave a partial directory that a retry will refuse. Inspect and preserve the failed attempt or choose a fresh root; do not merge partial generated files silently. The project identifier is inserted into generated Markdown, so choose a literal display label rather than a multiline Markdown fragment.

This layout is distinct from the hash-bound project catalog operated by `tools/project_catalog.py`. Initializing this home does not register its contents in that catalog or bind a portfolio privacy/evidence configuration.
