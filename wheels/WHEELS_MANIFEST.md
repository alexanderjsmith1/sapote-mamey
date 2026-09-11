# Bundled build wheels (A-02 — offline editable install)

These pure-Python (`py3-none-any`, all-platform) build-backend wheels and their transitive
dependencies let `pip install -e .`
succeed under build isolation in a fresh no-network environment (Python 3.13 ships no setuptools).
`bootstrap.sh` adds this directory to `--find-links` on every install so `pyproject`'s
`requires = ["setuptools>=68", "wheel"]` and wheel's `packaging>=24.0` dependency resolve locally.

| wheel | version | license | redistributable | source | SHA-256 |
|---|---|---|---|---|---|
| setuptools | 82.0.1 | MIT | yes | pypi.org/project/setuptools | a59e362652f08dcd477c78bb6e7bd9d80a7995bc73ce773050228a348ce2e5bb |
| wheel | 0.47.0 | MIT | yes | pypi.org/project/wheel | 212281cab4dff978f6cedd499cd893e1f620791ca6ff7107cf270781e587eced |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | yes | pypi.org/project/packaging | d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c |

Redistribution is permitted under the licenses shown above. Regenerate/repin by dropping newer
`py3-none-any` wheels here and updating this manifest's versions, licenses, and SHA-256 values.
