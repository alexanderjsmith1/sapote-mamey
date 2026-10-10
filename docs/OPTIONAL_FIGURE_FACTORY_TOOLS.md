# Optional Figure Factory tools

For analysis figures, start with the [rendering guide](FIGURE_FACTORY_NEXT.md).

These are explicit local tools for reviewing generic visual directions. They
are not Mamey subcommands and are never invoked by `run`, report compilation,
locus-map generation, or package validation.

Run each command deliberately from the extracted bundle root. The output path
must not exist: any pre-existing destination, including an empty directory, is
refused before mutation.

```bash
python tools/preview_figure_themes.py --out ./figure_theme_gallery
python tools/preview_figure_components.py --out ./figure_component_gallery --theme evidence-navy
```

Each successful command prints a machine-readable receipt using portable
logical locators rooted at the new output directory. All outputs are local
deterministic SVG, JSON, or HTML artifacts. No browser, network service, PDF,
or DOCX renderer is required. The galleries remain static prototypes and are
not wired into the Mamey run pipeline.

## Receipt and collision scope

`PASS` confirms the static gallery bundle was written; the printed receipt contains counts and portable output locators, not input/source/artifact hashes or scientific/visual acceptance. These previews use fixed example data and do not consume a real package, establish a scientific theme choice, or issue the Figure Factory's analysis receipt. Theme IDs belong to these galleries; do not assume a gallery theme ID is accepted by a different renderer/export command.

The output writer refuses an already-existing destination and a deterministic hidden `.<name>.staging` sibling. If interrupted, preserve/inspect any leftover staging folder before choosing a new output name; do not merge its contents into a completed gallery. Ordinary `os.replace` publication is atomic but is not the hardened concurrent no-replace transaction used by the review queue. Avoid concurrent writers to the same destination. If a destination appears after preflight, an empty directory can be replaced on POSIX. Bind source and artifact hashes separately if distributing a preview.

Source owners: `mamey/interactive_figures/theme_gallery.py:179–205`; `mamey/interactive_figures/component_gallery.py:269–297`; `mamey/interactive_figures/optional_output.py:20–71`.
