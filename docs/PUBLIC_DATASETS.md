# Public antiSMASH datasets

Ready-made antiSMASH result ZIPs for public genomes, mostly actinomycetes, are on Zenodo. Use them to try the program without running antiSMASH yourself, to compare your strains with public genomes of the same genus, or to repeat a published analysis from the exact same input.

Use the ZIPs run with antiSMASH 8.0.4 at `loose` strictness: their file names end in `__antiSMASH8.0.4_loose.zip`. There are 1,258 of them (about 45 GB) across 14 records. Cite the record DOI when you use its files. Each record page states its license and lists its files.

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

Each ZIP is one antiSMASH run on one public genome assembly. Its name gives the organism and strain, the NCBI assembly accession, the antiSMASH version and the strictness, for example `Genus_sp._EXAMPLE__GCA_000000000.1__antiSMASH8.0.4_loose.zip`.

## Use one

1. Open the record and download a loose ZIP. Each record page lists its files with their sizes and md5 checksums.
2. Check the download against the md5 shown on the record page: `md5 <file>` on macOS, `md5sum <file>` on Linux.
3. Pick a short strain name that is not a database accession, such as `EXAMPLE`. Do not use the `GCA_` accession from the file name. `run` refuses an accession as the strain name when the archive names an organism, and exits 2. To keep the accession as the name anyway, add `--allow-accession-strain-id`. To let the program build a name from the archive, use `--strain auto`.
4. Run the command that `inspect` prints, as in [Your first run](reader/01_FIRST_RUN.md). Pass `--strain EXAMPLE`. Pass `--taxonomy` and `--source` only from the deposited record, as that page describes.

A good run ends with exit code 0 and a results block. How to read it is on the first-run page. A large ZIP takes longer than a small one.

When you report a result, name the input by its record DOI and file name. The DOI and the file will not change, even when the program does.
