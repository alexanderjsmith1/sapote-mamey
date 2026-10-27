# Bundled build wheels (A-02 — offline editable install)

> Scope: these three wheels supply build-backend dependencies, not the full Mamey runtime, test or add-on environment. `bootstrap.sh` selects `${PYTHON:-python3}` and refuses Python below 3.12 before invoking pip. It resolves a caller-relative `--wheels` directory before changing to the directory containing the script, then anchors its editable installation and version-sync smoke test to that selected source. It installs pytest, tries `.[all]`, and falls back to core dependencies on failure. An offline invocation needs all requested compatible runtime/test/extras wheels in its selected pool; these three wheels alone cannot guarantee success. Default setup permits index access; `--wheels <directory>` adds `--no-index`. A successful fallback/smoke test does not establish optional capabilities, a complete fresh installation or full-suite validation.

These pure-Python (`py3-none-any`, all-platform) wheels supply the declared
build backend and wheel's `packaging` dependency. They cover that build-isolation
step; a fresh offline `pip install -e .` also needs compatible wheels for the
core runtime requirements, and requested extras need their own complete dependency sets.
`bootstrap.sh` adds this directory to `--find-links` on every install so `pyproject`'s
`requires = ["setuptools>=68", "wheel"]` and wheel's `packaging>=24.0` dependency resolve locally.

| wheel | version | license | redistributable | source | SHA-256 |
|---|---|---|---|---|---|
| setuptools | 82.0.1 | MIT | yes | pypi.org/project/setuptools | a59e362652f08dcd477c78bb6e7bd9d80a7995bc73ce773050228a348ce2e5bb |
| wheel | 0.47.0 | MIT | yes | pypi.org/project/wheel | 212281cab4dff978f6cedd499cd893e1f620791ca6ff7107cf270781e587eced |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | yes | pypi.org/project/packaging | d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c |

Redistribution is permitted under the licenses shown above. Regenerate/repin by dropping newer
`py3-none-any` wheels here and updating this manifest's versions, licenses, and SHA-256 values.
