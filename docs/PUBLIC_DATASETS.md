# Public antiSMASH datasets

Ready-made antiSMASH result ZIPs for public genomes, mostly actinomycetes, are on Zenodo. Use them to try the program without running antiSMASH yourself, to compare your strains with public genomes of the same genus, or to attempt a published analysis with a source-bound input. Preserve the versioned record, file name and downloaded byte hash, plus the software versions, settings, other inputs and methods needed for reproduction.

Use the ZIPs run with antiSMASH 8.0.4 at `loose` strictness. The recorded inventory lists 1,258 of them (about 45 GB) across 14 records; verify the current record inventory before downloading. Most file names end in `__antiSMASH8.0.4_loose.zip`; nine end in `__antiSMASH8.0.4_loose__2.zip`, so match on `_loose` rather than the exact ending. Cite the record DOI when you use its files. Each record page states its license and lists its files.

| Genus or group | Record DOI | Loose ZIPs | Size |
|---|---|---:|---:|
| *Actinomadura* | [10.5281/zenodo.23736957](https://doi.org/10.5281/zenodo.23736957) | 97 | 3.9 GB |
| *Amycolatopsis* | [10.5281/zenodo.23741370](https://doi.org/10.5281/zenodo.23741370) | 98 | 4.2 GB |
| *Micromonospora* | [10.5281/zenodo.23749249](https://doi.org/10.5281/zenodo.23749249) | 99 | 3.2 GB |
| *Nocardia* | [10.5281/zenodo.23739090](https://doi.org/10.5281/zenodo.23739090) | 95 | 3.7 GB |
| *Pseudonocardia* (1 of 2) | [10.5281/zenodo.23748725](https://doi.org/10.5281/zenodo.23748725) | 99 | 2.4 GB |
| *Pseudonocardia* (2 of 2) | [10.5281/zenodo.23748801](https://doi.org/10.5281/zenodo.23748801) | 66 | 1.8 GB |
| *Saccharopolyspora*, *Saccharothrix* and *Sciscionella* | [10.5281/zenodo.23749560](https://doi.org/10.5281/zenodo.23749560) | 95 | 3.2 GB |
| *Streptomyces* (1 of 4) | [10.5281/zenodo.23748834](https://doi.org/10.5281/zenodo.23748834) | 99 | 3.8 GB |
| *Streptomyces* (2 of 4) | [10.5281/zenodo.23748963](https://doi.org/10.5281/zenodo.23748963) | 99 | 4.0 GB |
| *Streptomyces* (3 of 4) | [10.5281/zenodo.23749043](https://doi.org/10.5281/zenodo.23749043) | 99 | 3.8 GB |
| *Streptomyces* (4 of 4) | [10.5281/zenodo.23749129](https://doi.org/10.5281/zenodo.23749129) | 70 | 1.9 GB |
| *Streptosporangium* | [10.5281/zenodo.23748506](https://doi.org/10.5281/zenodo.23748506) | 99 | 4.4 GB |
| Other actinomycete genera | [10.5281/zenodo.23749643](https://doi.org/10.5281/zenodo.23749643) | 80 | 2.5 GB |
| Other genera, including non-bacteria | [10.5281/zenodo.23748369](https://doi.org/10.5281/zenodo.23748369) | 63 | 2.0 GB |

## What each ZIP is

Each ZIP is one antiSMASH run on one public genome assembly. Its name gives the organism and strain, an NCBI accession (an assembly `GCA_` accession or a sequence accession), the antiSMASH version and the strictness, for example `Genus_sp._EXAMPLE__GCA_000000000.1__antiSMASH8.0.4_loose.zip`.

## Use one

1. Open the record and download a loose ZIP. Each record page lists its files with their sizes and md5 checksums.
2. Check the download against the md5 shown on the record page: `md5 <file>` on macOS, `md5sum <file>` on Linux.
3. Run `inspect` on the ZIP under its original file name. It prints a `--strain` that `run` accepts, and a `Strain name:` line when it had to change the file name. Use that name, or a short name of your own that is not a database accession.
4. Run the command that `inspect` prints, as in [Your first run](reader/01_FIRST_RUN.md). Pass `--taxonomy` and `--source` only from the deposited record, as that page describes.

`run` refuses a database accession as the strain name, with exit 2, when it can read an organism name. It reads the organism from the GenBank header and, when that is blank, from the ZIP file name. So renaming the file can change whether an accession is refused. To keep an accession as the name anyway, add `--allow-accession-strain-id`. `--strain auto` asks the program to derive a name from the archive or filename. If the run refuses that name, choose an explicit safe name of at most 64 characters. Check the resolved organism, its provenance and potential name collisions.

A good run ends with exit code 0 and a results block. How to read it is on the first-run page. A large ZIP takes longer than a small one.

When reporting a result, keep the versioned record DOI, file name, checksum algorithm and observed SHA-256 together. Reuse an input only when its hash matches. Preserve the software versions, settings and other inputs; a DOI or file name alone does not prove byte identity or reproduction.
