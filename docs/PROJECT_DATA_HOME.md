# Start a project file index

Create folders and empty registers for a project's inputs and results. You need
a new folder location and a project name. Large genome and antiSMASH files can
stay where they are; register their paths and checksums in this index.

Run this from the program folder:

```bash
python3 tools/init_project_data_home.py --root ../EXAMPLE-home --project-id EXAMPLE
```

`--root` chooses the new folder. `--project-id` supplies the name for its README.
The command prints the folder's full path.

## Add your records

Open the new README. The home contains ten numbered folders, nine header-only
TSV registers and `PROJECT_HOME.json`. Add each file's location and available
checksum to the matching register. The initializer leaves those rows empty;
it does not inspect your files or calculate their hashes.

Use a fresh folder: an existing target is refused, even when empty. Each
register and file is created new; an existing file is never truncated.

If the initializer hits an error it can catch, it removes only the folders and
files it created in that run. A file someone else added under the new folder
stays, and so does the folder holding it. A write that fails before its new file is
recorded for cleanup can also leave a partial file. The error note lists retained
tracked paths, which may be parent folders rather than every file; inspect the tree.
A killed process cleans nothing up and can leave a partial home. Keep a partial
home for inspection and choose a new location for the retry.

This file index is separate from [Project catalog](PROJECT_CATALOG.md), which
registers existing packages, and [Strain Master](DATA_HOME.md), which imports
byte copies. Creating the index does not configure either tool.
