# Portable project data home

Run `python3 tools/init_project_data_home.py --root PATH --project-id NAME` to create a new, empty data home for a project.

The home is pointer-first. Its registers store where each file lives and its checksum. Large genome and antiSMASH files can stay in their existing external stores. A register entry points to them. Nothing is copied or reclassified.

The home has one folder each for incoming files, authority records, strain genomes, phylogeny, antiSMASH and Mamey outputs, bioassays, citations, manuscripts, deliverables and superseded files.

The initializer refuses an existing target. It does not choose scientific inputs, approve tree membership or change evidence. It grants no release authority.

## What initialization actually writes

The initializer creates:
- ten numbered folders, `00_INBOX` to `09_SUPERSEDED`;
- nine TSV registers that hold only a header row;
- `PROJECT_HOME.json`;
- a `README.md`.

It does not fill in locators or compute evidence hashes. It does not check external stores. It does not register existing packages. An empty register does not mean the scientific inventory is complete. Adding rows that point to real source files is a separate task.

Use a new, explicit output root and a plain project identifier. The initializer refuses every existing target, including an empty folder. It creates missing parent folders.

If writing the home fails with an error, the initializer tries to remove the new home. If the process is killed partway, a partial folder can remain. A retry will refuse it. Inspect and keep the failed attempt, or choose a fresh root. Do not quietly merge partial generated files.

The project identifier is written into the generated README heading. Use a plain display label, not a multiline Markdown fragment.

This layout is separate from the project catalog run by `tools/project_catalog.py`, which records file hashes. Creating this home does not add its contents to that catalog. It does not set up a portfolio privacy or evidence configuration.

It is also separate from the Strain Master in [DATA_HOME.md](DATA_HOME.md), which holds byte copies rather than pointers. No bundle command reads this layout; the `strain-master` commands use their own layout.
