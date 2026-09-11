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
