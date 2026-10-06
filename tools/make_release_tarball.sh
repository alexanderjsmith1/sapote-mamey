#!/usr/bin/env bash
# make_release_tarball.sh — cut-time packaging artifact (v9.7.400, BC/the phylogeny lane-fork proposal).
#
# Produces a distribution-grade .tar.gz of a sealed bundle directory plus a .sha256 beside it.
# The sealed ZIP + SOURCE_CHECKSUMS_SHA256.txt remain the CANONICAL integrity system — this
# tarball is packaging convenience (preserves exec bits/symlinks; the format GitHub Releases
# and bioinformatics tooling expect). Public-release policy is unchanged: any PUBLIC tarball
# must be cut from the public tier, never the working bundle (HOLD per the owner 2026-08-25).
#
# Usage: tools/make_release_tarball.sh <sealed-bundle-dir> [outdir]
# Emits: <outdir>/<bundle-dir-name>.tar.gz and <bundle-dir-name>.tar.gz.sha256
set -euo pipefail

if [ $# -lt 1 ] || [ ! -d "$1" ]; then
  echo "REFUSED: pass the sealed bundle directory (got: ${1:-<none>})" >&2
  exit 2
fi
src="${1%/}"
outdir="${2:-$(dirname "$src")}"
name="$(basename "$src")"

# Refuse an unsealed-looking tree: the sealed identity files must exist.
for req in BUILD_STAMP.txt SOURCE_CHECKSUMS_SHA256.txt; do
  if [ ! -f "$src/$req" ]; then
    echo "REFUSED: $req missing — $name does not look like a sealed bundle" >&2
    exit 2
  fi
done

mkdir -p "$outdir"
tarball="$outdir/$name.tar.gz"
# COPYFILE_DISABLE stops tar from GENERATING AppleDouble (._*) entries. It does not stop tar from
# archiving ._* files that already exist on disk (a tree copied through exFAT/SMB has thousands),
# and Linux tar extracts those as real files that fail --strict-membership. Exclude them, then check.
COPYFILE_DISABLE=1 tar -czf "$tarball" -C "$(dirname "$src")" \
  --exclude '.DS_Store' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '._*' \
  -- "$name"
if ! python3 - "$tarball" <<'PY'
import sys
import tarfile

try:
    with tarfile.open(sys.argv[1], mode="r|gz") as archive:
        for member in archive:
            if member.name.rsplit("/", 1)[-1].startswith("._"):
                print(f"APPLEDOUBLE_MEMBER: {member.name}", file=sys.stderr)
                sys.exit(2)
except (OSError, tarfile.TarError) as exc:
    print(f"TARBALL_INSPECTION_REFUSED: {exc}", file=sys.stderr)
    sys.exit(2)
PY
then
  rm -f -- "$tarball" "$tarball.sha256"
  echo "REFUSED: AppleDouble (._*) member or unreadable tarball; rebuild from a fresh extraction of the sealed ZIP" >&2
  exit 2
fi
# Relative-name sidecar (BC4 .400 seal-gate review, delta h): an awk-$2 sidecar truncated the
# recorded path at the first space, so `shasum -c` failed on spaced outdirs — which the
# workspace's release folders are. Relative name = space-safe AND portable across machines.
( cd "$outdir" && shasum -a 256 -- "$name.tar.gz" > "$name.tar.gz.sha256" )
echo "tarball: $tarball"
echo "sha256:  $(cut -d' ' -f1 "$tarball.sha256")"
