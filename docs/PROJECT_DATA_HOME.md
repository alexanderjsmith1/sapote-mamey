# Portable project data home

Run `python3 tools/init_project_data_home.py --root PATH --project-id NAME` to create a new pointer-first scientific data home.

The home separates authority, strain genomes, phylogeny, antiSMASH and Mamey outputs, bioassays, citations, manuscripts, deliverables, and superseded artifacts. Registers store locators and checksums. Large genome and antiSMASH files may remain in governed external stores; a register entry points to them without silently copying or reclassifying them.

The initializer refuses an existing target. It does not select scientific inputs, approve tree membership, alter evidence, or confer release authority.
