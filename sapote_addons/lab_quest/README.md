# Lab Quest add-on

Lab Quest is a game-style local interface over Sapote-Mamey packages. It is not part of the analysis methods, so from
v9.7.444 it ships as an optional add-on instead of in the core `mamey` package. Its behaviour is unchanged.

Install from the bundle root, into the same environment as the engine:

```bash
pip install ./sapote_addons/lab_quest
python mamey_run.py lab-quest --help
```

It needs `streamlit`. Offline, put a streamlit wheel in the add-on wheel pool and run
`SAPOTE_INSTALL_LAB_QUEST=1 bash bundle_support/install_sapote_addons.sh`.

Without the add-on, `mamey lab-quest` is absent from `--help`, and typing it prints how to install it. The
`lab_quest_outputs/` folder written by the portfolio and project-catalog code stays in core; it is a data location.

Full description: `docs/LAB_QUEST.md`.
