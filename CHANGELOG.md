# Changelog

All changes that users of the OBI backend notice. For older versions see the git history.

The backend version (`OBI_BACKEND_VERSION`, in `status.json` as `version`) is increased when clients have to know about a change.


## Unreleased

### Added

* `add_source`: add a source to an existing build list. Dependent sources are added, affected successful builds are reset ([docs](docs/build-process.md#adding-a-source))
* `-c`, `--compile-list-dir`: folder of the build list, for all actions
* `max-parallel-builds`: build several sources of a level at the same time ([docs](docs/build-process.md#parallel-builds)). Default 1, as before
* Documentation of the backend in `docs`

### Changed

* Every command writes its joblog into its own temporary file, which is removed afterwards
* A raw `cmd` step of the extended source processing runs once. Before, it ran once for every step of the source type, or not at all without them. The steps of the source type are only added with `add_default_steps = true`

### Fixed

* A command that fails without writing to `stderr` is now `failed`. Before, the exit code of the joblog command was used, so the failure was not detected. This doesn't apply yet if `global.cmds.dspjoblog` is configured
* The status `failed` of a source is saved in the build list
* Nested variables (`$(A)` → `$(B)` → `$(C)`) are resolved completely. Circular variables no longer end in an endless recursion
* `ALWAYS_TRANSFER_RELATED_COPYBOOKS` and `global.cmds.evfevent-export` are optional
* Copybooks found for one build list no longer show up in the next one created by the same process
* After an error in a script of the extended source processing, the output and the log work again
