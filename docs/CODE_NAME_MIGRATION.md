# Public-home and historical-label migration

Neutral built-in package homes are `mamey_packages` and `Package Outputs*`.
`MAMEY_PACKAGE_HOMES` remains an explicit os.pathsep-separated list of absolute or
workspace-relative patterns. Defaults remain first; additions retain declared order.
No legacy deployment directory is discovered implicitly, moved, renamed or reconfigured.
Set the variable yourself to existing custom homes when migrating. Inventory/fair-cohort
first-match order and explicit board-glob precedence remain; roster inventory freshness
still outranks home score, and every declared matched home receives the preferred-home
score. Explicit external homes are searched as declared, with version parsing relative
to that selected home rather than an unrelated ancestor. Package authority/flavor/version
and inode-dedup behavior remain. These are behavioral changes, not cosmetic replacements.

The current public inventory routing-policy id is `inventory-bottom-tier-v1`. Its class
lists, numerical policy, source evidence and decision date are unchanged. Historical
private record labels are visibly omitted from public chronology rather than renamed as
if old receipts used this id. The maintainer retains an exact crosswalk outside CODE.
Old source hashes/receipts describe their original bytes and do not validate this changed
source. Regenerate governed metadata and repeat appropriate source/artifact validation.

The claim-safety callback remains advisory. It admits existing report files under the
workspace's exact strain_data home or explicit SAPOTE_DELIVERABLE_ROOT, rejects traversal,
outside-root absolute paths, private payload areas and roster/exclusion leaves, and does
not infer secrecy from strain labels or BGC classes. A syntactically admitted report is
not privacy clearance; content/export checks still apply. No private aliases or encoded
reconstructions are added to CODE. Completion of these migrations alone does not prove
actual source/archive cleanliness or release acceptance.

Editorial scope also includes adapted comments and test-history descriptions in this
proposal and the preceding partial cleanup. Neutral names in those descriptions are
editorial display labels, not assertions that the original folders, card IDs, receipt
IDs or contributor codenames had those values. Exact original changed records remain
in a maintainer-only crosswalk outside CODE. Ordinary color words (including palette
periwinkle), genuine strain labels and BGC classes are not private by association.
Tests read invented transcripts only; generic personal paths and genuine task-packet
payload markers remain forbidden in the portable Methods document set.

Conventional claim-safety admission requires the resolved strain_data home to stay
inside the resolved workspace. A symlink exporting that entire home to an external
location does not grant implicit admission, for either a relative alias path or an
absolute external path. Explicit SAPOTE_DELIVERABLE_ROOT may select an external home,
including a symlink spelling of that home. Admission then requires the resolved file
inside that selected home; file links escaping it still refuse. Exact private selected
home names, private ancestors on the distinct path below the workspace/home common
ancestor, private components below the chosen home, and roster/exclusion leaves refuse.
Shared ancestor components and the macOS OS prefixes /private/tmp and /private/var are
not classified as project payload areas. Lexical and resolved selected-home spellings
are checked, so a neutral alias does not hide private ancestry. File-path traversal is
always refused. This is advisory path selection, not content or privacy clearance.
