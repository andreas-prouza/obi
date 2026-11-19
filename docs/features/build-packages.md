# Build packages

- **Status:** in progress (implemented and tested; not released)
- **Type:** feature


## Current situation

* `create` builds all changed sources (hash compare with `object-builds.json`) or one source (`--source`), each with its dependent objects
* The VS Code extension introduces build packages: a named list of sources in `.obi/build-packages/<name>.json`, committed with the project ([obi-extension/docs/features/build-packages.md](../../../obi-extension/docs/features/build-packages.md))
* Without the backend, a package can't be built from the command line or a CI job


## Requirements

1. New argument `--package <name>` for `create`, not together with `--source`
2. The package file is `.obi/build-packages/<name>.json`:
   ```json
   {
     "description": "Order entry rework (ABC-123)",
     "sources": ["mylib/qddssrc/orders.pf.file", "mylib/qrpglesrc/order.sqlrpgle.pgm"]
   }
   ```
3. All sources of the package are built, whatever their hash, plus all sources depending on them
4. The build list gets `"package": {"name": "<name>", "description": "..."}`


## Acceptance criteria

* For the same project, the build list is the same as the one of the VS Code extension
* A source counts as new if it is not in `object-builds.json`, otherwise as changed (`changed-object-list.json`), as with `--source`
* These are errors, and no build list is written:
  * a name not matching `^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$`
  * a missing file, a file that is not JSON or not an object, `sources` not a list of strings
  * a source that is absolute, contains `..` or `\`, doesn't exist, or whose type is not in `supported-object-types`


## Non-goals

* Creating or editing packages (done in the VS Code extension or by hand)
* `run` with a package: `run` builds the build list created before


## Decisions

* The name, not a path, is passed: the folder is fixed, and the name can't leave it
* Missing sources are an error, not skipped: a CI build must not silently build less than the package
* `OBI_BACKEND_VERSION` 5
* The package is read before `create` deletes the build output: an invalid package keeps the previous build list. As for other errors of `create`, the exit code is 0 and `status.json` has the error
* The type check uses the last extension of the source (like the VS Code extension), not the suffix match of `files.get_files`
* Documentation: [Command line](../cli.md#build-packages), [Change detection](../build-process.md#1-change-detection)
