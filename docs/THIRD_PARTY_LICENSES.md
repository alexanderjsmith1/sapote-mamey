# Third-Party Licenses

Sapote–Mamey's own code and documentation are licensed under `LICENSE` (MIT, code) and
`LICENSE-DOCS.txt` (documentation). This file covers third-party components.

## Redistributed in this repository (vendored code)

One third-party library is vendored — its source ships inside this repository, so its license
is retained alongside it:

| Component | Location | License | Copyright |
|---|---|---|---|
| **ijson** | `mamey/_vendor/ijson/` | BSD (2-clause) | © 2010 Ivan Sagalaev |

The full license text is at `mamey/_vendor/ijson/LICENSE.txt` and is preserved unmodified.

## Runtime dependencies (installed separately, not redistributed here)

These packages are declared in `requirements.txt` and the offline companion stack (see
`docs/PREREQUISITES.md`). Their code is **not** included in this repository — it is installed via `pip`
or the companion wheel archive — so their licenses apply per the upstream project, not this repo.
Listed here for transparency; consult each project for authoritative, current license text.

| Package | Upstream license (for reference) |
|---|---|
| numpy | BSD 3-Clause |
| pandas | BSD 3-Clause |
| matplotlib | Matplotlib License (BSD-style, PSF-derived) |
| openpyxl | MIT |
| ijson | BSD (also a pip dependency; vendored copy above) |
| biopython | Biopython License Agreement / BSD 3-Clause |
| pyhmmer | MIT |
| pyfamsa, pyfastani, pyfastx, pyfaidx | MIT / BSD (per project) |
| DendroPy | BSD 3-Clause |
| gffutils, bcbio-gff | MIT / BSD (per project) |
| psutil | BSD 3-Clause |

antiSMASH (the upstream BGC-detection tool this pipeline consumes output from) is not bundled and
carries its own license; cite antiSMASH 8.0 (Blin et al.) when publishing.

*If a license listed here is inaccurate for the version you install, the upstream project's own
license file governs. This notice is a convenience, not a substitute for it.*

## Runtime dependencies added to the inventory (v9.7.381 reconciliation)

These are pip-installed dependencies (not bytes redistributed in this repository); their license
applies to the installed package, which the operator obtains from PyPI.

- **reportlab** — colorful PDF renderer backend (`tools/render_deliverable_pdf.py`). License: BSD-3-Clause. Installed from PyPI; not redistributed here.
- **PyYAML** — YAML parsing (core dependency / `.[dev]` alias). License: MIT. Installed from PyPI; not redistributed here.
- **cairosvg** — optional SVG→PNG for locus-map embedding (`.[render]`, soft-guarded). License: LGPL-3.0-or-later. Installed from PyPI; not redistributed here.

## Runtime dependencies added to the inventory (v9.7.409 reconciliation)

These are pip-installed dependencies (not bytes redistributed in this repository); their license
applies to the installed package, which the operator obtains from PyPI. All are permissive — no
conflict with the MIT bundle. Added here to close the completeness gap flagged in the supply-chain
audit (SC-4).

`documents` extra (`pyproject.toml` — governed DOCX/PDF authoring):

- **python-docx** — DOCX authoring (`export_card_docx`, soft-guarded `SKIPPED_NO_DOCX`). License: MIT. Installed from PyPI; not redistributed here.
- **lxml** — XML backend used by python-docx. License: BSD-3-Clause (libxml2/libxslt it wraps are MIT). Installed from PyPI; not redistributed here.
- **pypdf** — PDF page-count / render verification. License: BSD-3-Clause. Installed from PyPI; not redistributed here.
- **Pillow** — image handling for figure/PDF paths. License: HPND (MIT-CMU style, permissive). Installed from PyPI; not redistributed here.

`figures` extra (soft-guarded figure outputs — added v9.7.409):

- **networkx** — BiG-SCAPE GCF-network figure (`mamey/bigscape_figures.py`); soft-guarded (`SKIPPED_NO_DEPS`). License: BSD-3-Clause. Installed from PyPI; not redistributed here.
- **scipy** — cohort clustermap ordering (`mamey/cohort_figures.py`, `tools/cluster_relate.py`); soft-guarded (falls back to count-ordering). License: BSD-3-Clause. Installed from PyPI; not redistributed here.

## External bioinformatics tools (operator-installed, invoked-only — not bundled, not linked)

These programs are installed by the operator and invoked as separate processes; their source is
not vendored in the core package. Listed for transparency; see `docs/EXTERNAL_TOOL_INVENTORY.md`
for versions and citations. Each project's license governs the copy that is installed, modified,
or redistributed. A person distributing a combined environment or modified tool must review that
tool's upstream terms rather than relying on Sapote-Mamey's MIT license.

| Tool | Role | Upstream license (for reference) |
|---|---|---|
| **BiG-SCAPE 2** | GCF families / networks | AGPL-3.0 |
| **DIAMOND** | fast protein homology (BLAST-like) | GPL-3.0 |
| **GToTree** | core-genome phylogenomics backbone | [MIT](https://github.com/AstrobioMike/GToTree); companion dependencies separately licensed |
| **Prodigal** | gene prediction | GPL-3.0 |
| **trimAl** | alignment trimming | GPL-3.0 |
| **IQ-TREE** | maximum-likelihood trees | GPL-2.0 |
| **FastTree** | fast draft trees | [GPL-3.0 in current upstream](https://github.com/morgannprice/fasttree); verify older distributions separately |
| **HMMER** | profile-HMM search | BSD-3-Clause |
| **MUSCLE** | multiple sequence alignment | GPL-3.0 (v5; verify per installed version) |

The core repository's MIT license does not replace any external tool's license. The separately
tracked GToTree source patch in this tree is a redistribution case and must retain the upstream
license and notices appropriate to that patch.
