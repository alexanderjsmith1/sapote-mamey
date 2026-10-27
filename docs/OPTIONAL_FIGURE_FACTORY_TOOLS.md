# Optional Figure Factory tools

Use these galleries to review example themes and components without a package or
analysis table. To make a figure from your data, choose its maintained route in
[Figures start here](FIGURES_START_HERE.md); use the [aggregate coverage guide](FIGURE_FACTORY_NEXT.md)
only when you have counted metrics and a cohort manifest.

The two commands below write static design previews with fixed example data.
They are local tools, not Mamey subcommands; `run`, report compilation,
locus-map generation and package validation do not invoke them. A gallery choice
does not change an analysis renderer's approved palette or settings.

Run each command deliberately from the extracted bundle root. The output path
must not exist: any pre-existing destination, including an empty directory, is
refused before mutation.

```bash
python tools/preview_figure_themes.py --out ./figure_theme_gallery
python tools/preview_figure_components.py --out ./figure_component_gallery --theme evidence-navy
```

After the first command, open
`figure_theme_gallery/sapote_mamey_figure_theme_gallery.html` for the theme gallery
or its `sapote_mamey_figure_theme_overview.svg` for the overview. After the second,
open `figure_component_gallery/sapote_mamey_figure_component_gallery.svg` and inspect
`sapote_mamey_figure_component_manifest.json` in the same folder.

Each successful command prints a machine-readable receipt using portable
logical locators rooted at the new output directory. All outputs are local
deterministic SVG, JSON, or HTML artifacts. No browser, network service, PDF,
or DOCX renderer is required. The galleries remain static prototypes and are
not wired into the Mamey run pipeline.

## Receipt and collision scope

`PASS` confirms the static gallery bundle was written; the printed receipt contains counts and portable output locators, not input/source/artifact hashes or scientific/visual acceptance. These previews use fixed example data and do not consume a real package, establish a scientific theme choice, or issue the Figure Factory's analysis receipt. Theme IDs belong to these galleries; do not assume a gallery theme ID is accepted by a different renderer/export command.

The output writer refuses an already-existing destination and a deterministic hidden `.<name>.staging` sibling. If interrupted, preserve/inspect any leftover staging folder before choosing a new output name; do not merge its contents into a completed gallery. Ordinary `os.replace` publication is atomic but is not the hardened concurrent no-replace transaction used by the review queue. Avoid concurrent writers to the same destination. If a destination appears after preflight, an empty directory can be replaced on POSIX. Bind source and artifact hashes separately if distributing a preview.
