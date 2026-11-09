# Figure QA on a completed render packet

A completed render packet is a folder of finished figures (PNG, SVG and caption files) with a
`render_receipt.json` beside them that lists every output and its SHA-256 hash. This page checks such a
packet. For checking figures that have no receipt, and for the general figure checks, see
[locus map and PCoA tools](LOCUS_AND_PCOA_TOOLS.md#page-artwork-and-checks).

## Run the check

Get the receipt hash, then run the check into a new folder:

```bash
shasum -a 256 packet/render_receipt.json
python tools/figure_render_qc.py packet \
  --render-receipt-sha256 <64-character hash> --out packet/qa
```

Use the hash you were given with the packet if there is one. A hash you compute from the same
folder shows only that the packet matches its own receipt, not that the receipt is the one you
were sent.

You should see one line such as `checked 6; errors 0, warnings 0, text not checked 0, notes 1 -> packet/qa/RENDER_QC.md`,
and exit 0. The folder then holds `RENDER_QC.md` and `RENDER_QC.tsv`.

## Read the result

- Every file the receipt lists must match its recorded size and hash; an edited or missing listed
  file is an error. The check also looks under the packet folder for PNG, SVG and PDF files and
  caption Markdown (a name containing `CAPTION`) that the receipt does not list, and refuses the
  packet when it finds one. The `--out` folder, its OCR cache and macOS `._` files are skipped.
  Other added files, such as a stray `.json` or `.txt`, are not looked for.
- Exit 2 with no reports means the check refused to run. Causes: a bad receipt or hash, a
  symlink, a file changed during the run, or a report file that already exists. Fix the cause
  and use a new `--out` folder.
- The reports are create-only. Choose a new folder inside the packet or beside it. The packet
  root itself is refused.
- The check is a point-in-time test. It does not lock the files afterward, and it does not show
  who made the packet.
- Do not delete a receipt to make a packet look unreceipted.

## Platform

The check needs a Python that supports directory-handle file opens. It is tested on macOS. It
has not been run on Linux, and standard Windows Python cannot run it.

On macOS, PNG text checking (OCR) needs a writable compiler cache and access to the system
Vision framework. If the sandbox blocks recognition, the report says "text not checked". Treat
that as unchecked, and run again where recognition is allowed. SVG text checking does not need
OCR.
