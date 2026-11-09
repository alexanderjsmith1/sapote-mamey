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

Each command prints a JSON receipt and exits 0. A successful theme run looks like this:

```json
{
  "status": "PASS",
  "schema_version": "sapote_mamey.figure_theme_gallery.v1",
  "theme_count": 6,
  "output_root": "figure_theme_gallery",
  "html": "figure_theme_gallery/sapote_mamey_figure_theme_gallery.html",
  "svg": "figure_theme_gallery/sapote_mamey_figure_theme_overview.svg"
}
```

The outputs are local, deterministic SVG, JSON and HTML files. No browser, network service, PDF
or DOCX renderer is needed.

## What a PASS means

`PASS` means the gallery files were written. It does not mean a theme or figure is approved. The
galleries use fixed example data, so they do not read a package and do not choose a theme for your
analysis. A theme ID here is not accepted by other renderers.

## If a run fails

If the output folder already exists, even empty, the tool prints `"status": "REFUSED"` with
`OUTPUT_REFUSED` and exits 2. Pick a new output name.

If a run is interrupted, a hidden `.<name>.staging` folder may remain next to the output. While it
exists, the tool refuses that output name. The folder name alone does not show which run made it or
whether a run still uses it, so leave it in place and run again with a new output name. Remove it only
after you have checked that no command is running on that name and you no longer need its contents.
Do not run two commands on the same output name at once.
