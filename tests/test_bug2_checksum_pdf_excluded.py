"""Bug #2: post-seal presentation PDFs must be excluded from the checksum set.

The matplotlib pdf backend embeds a build timestamp, so `<strain>_8_strain_brief.pdf` and
`package_PRINT_FIGURE_PACK.pdf` are byte-nondeterministic and are rendered AFTER
checksums_sha256.txt is written. Before the fix they fell through is_checksum_excluded()
(which only handled .png/.svg under the figure dirs) and caused a spurious
checksum_integrity FAIL / a blocked `seal-package --strict`.
"""
from mamey.packaging import is_checksum_excluded


def test_post_seal_pdfs_excluded():
    assert is_checksum_excluded("AS-74_8_strain_brief.pdf") is True
    assert is_checksum_excluded("AS-123_8_strain_brief.pdf") is True
    assert is_checksum_excluded("package_PRINT_FIGURE_PACK.pdf") is True


def test_data_bearing_files_still_checked():
    # data/analysis artifacts must stay IN the checksum set
    for keep in ("AS-74_2_inventory.csv", "AS-74_5_workbook.xlsx",
                 "manifest.json", "AS-74_compiled_report.md",
                 "gold_figures/F01_data.csv"):
        assert is_checksum_excluded(keep) is False


def test_existing_png_svg_exclusion_unchanged():
    assert is_checksum_excluded("gold_figures/x.png") is True
    assert is_checksum_excluded("locus_maps/y.svg") is True
    assert is_checksum_excluded("gold_figures/x_data.csv") is False
