# Optional Figure Factory Tools

> These optional theme/component preview tools are distinct from the **integrated Figure Factory
> deliverable**. The Figure Factory itself is a first-class deliverable, invoked as
> `python mamey_run.py figure-factory --config <json>` and auto-emitted in the run/cohort flow (see
> `docs/FIGURE_FACTORY_NEXT.md`). The commands on this page are *not* that deliverable: they are
> optional galleries for exploring visual directions and remain deliberate, manual, opt-in tools.

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
