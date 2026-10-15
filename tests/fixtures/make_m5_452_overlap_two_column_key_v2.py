"""Generator for tests/fixtures/m5_452_overlap_two_column_key_v2.pdf (card M5_452_overlap_check_columns, v2 fixture).
Same two-column key layout and font size as the failing figure of 13 Oct 2026 (page 7.2 x 9.0 in; 8 pt Arial; columns at
10.4 pt and 259.2 pt; 9 rows 17.6 pt apart). Synthetic text only: labels SYN-01..SYN-18, places "Place A/B/C", date "2000-01".
Lines SYN-02 and SYN-03 run about 2 pt into the right column, as in the original; the check must report exactly 2.
Usage: python make_m5_452_overlap_two_column_key_v2.py <out.pdf>"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FILL = "synthetic location with a long l"   # filler length sets the ~2 pt overlap (old check 0, fixed 2)
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "pdf.fonttype": 42})
row = lambda n, grp, host, place: f"SYN-{n:02d}  {grp}; {host}; {place}; 2000-01"
LEFT = [row(1, "bee/wasp", "Bumblebee", "Place B"), row(2, "moss", "Moss", "Place A, " + FILL), row(3, "moss", "Moss", "Place A, " + FILL)] + \
       [row(n, "bee/wasp", h, "Place B") for n, h in zip(range(4, 10), ["Bumblebee"] * 4 + ["Other bee"] * 2)]
RIGHT = [row(n, g, h, p) for n, g, h, p in zip(range(10, 19), ["bee/wasp", "bee/wasp", "moss"] + ["bee/wasp"] * 6,
         ["Bumblebee", "Bumblebee", "Moss", "Bumblebee", "Bumblebee", "Honeybee", "Bumblebee", "Bumblebee", "Bumblebee"],
         ["Place C", "Place C", "Place C"] + ["Place B"] * 6)]
fig = plt.figure(figsize=(7.2, 9.0)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 518.4); ax.set_ylim(0, 648)
for i, (l, r) in enumerate(zip(LEFT, RIGHT)):
    y = 153.0 - 17.6 * i
    ax.text(10.4, y, l, va="baseline", ha="left"); ax.text(259.2, y, r, va="baseline", ha="left")
fig.savefig(sys.argv[1]); plt.close(fig)
