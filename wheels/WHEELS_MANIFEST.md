# Bundled build wheels (A-02 — offline editable install)

These pure-Python (`py3-none-any`, all-platform) build-backend wheels let `pip install -e .`
succeed under build isolation in a fresh no-network environment (Python 3.13 ships no setuptools).
`bootstrap.sh` adds this directory to `--find-links` on every install so `pyproject`'s
`requires = ["setuptools>=68", "wheel"]` resolve locally.

| wheel | version | license | redistributable | source | SHA-256 |
|---|---|---|---|---|---|
| setuptools | 82.0.1 | MIT | yes | pypi.org/project/setuptools | a59e362652f08dcd477c78bb6e7bd9d80a7995bc73ce773050228a348ce2e5bb |
| wheel | 0.47.0 | MIT | yes | pypi.org/project/wheel | 212281cab4dff978f6cedd499cd893e1f620791ca6ff7107cf270781e587eced |

Both MIT-licensed; redistribution permitted. Regenerate/repin by dropping newer `py3-none-any`
wheels here and updating this manifest's versions + SHA-256.
