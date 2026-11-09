"""R renderers must not write PDFs with grDevices::pdf(): it draws every ASCII hyphen with the /minus glyph, so an ID such as
AS-441 reads as AS−441 in the text layer and a search for it fails."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF_TO_FILE = re.compile(r"""device\s*=\s*['"]pdf['"]|grDevices::pdf\((?!\s*(NULL|file\s*=\s*NULL)\s*[,)])""")


def test_no_plain_pdf_device_for_figure_files():
    hits = []
    for f in sorted((ROOT / "tools").glob("*.R")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if PDF_TO_FILE.search(line) and "pdf = function()" not in line:   # sapote_pub_layout.R's last-resort fallback warns
                hits.append(f"{f.name}:{n}")
    assert hits == []
