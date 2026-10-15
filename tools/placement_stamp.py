"""Stamp placement exports with the shared bundle provenance writer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.figure_stamp import stamp_file

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--print-width', type=float)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()
    for name in args.files:
        if args.print_width is not None and Path(name).suffix.lower() == '.pdf':
            # R's PDF device rounds the MediaBox to whole points. Correct only
            # the page boundary; do not scale the content or its type sizes.
            from pypdf import PdfReader, PdfWriter
            reader = PdfReader(name)
            writer = PdfWriter(clone_from=reader)
            for page in writer.pages:
                page.mediabox.upper_right = (args.print_width * 72, float(page.mediabox.top))
                if '/CropBox' in page:
                    page.cropbox.upper_right = page.mediabox.upper_right
            import io
            buffer = io.BytesIO(); writer.write(buffer)
            Path(name).write_bytes(buffer.getvalue())
        stamp_file(name, 'ggtree_rect_heatmap')
