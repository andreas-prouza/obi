# Changelog

All changes that users of the OBI backend notice. For older versions see the git history.

The backend version (`OBI_BACKEND_VERSION`, in `status.json` as `version`) is increased when clients have to know about a change.


## Unreleased

### Added

* `add_source`: add a source to an existing build list ([docs](docs/build-process.md#adding-a-source))
* `-c`, `--compile-list-dir`: folder of the build list
* `max-parallel-builds`: parallel builds within a level ([docs](docs/build-process.md#parallel-builds))
* Processing service: `submit`, `watch`, `jobs`, `cancel` and `service.py`. Builds keep running when the connection ends, with events for every change ([docs](docs/processing-service.md)). Backend version 4
* Backend documentation in `docs`
* Variables `$(SOURCE_DESCRIPTION)` and `$(OBJ_TEXT)`: the source description from `source-infos`, e.g. for `TEXT('$(OBJ_TEXT)')` ([docs](docs/configuration.md#variables))
* `create --package <name>`: build all sources of a build package (`.obi/build-packages/<name>.json`) and their dependent objects ([docs](docs/cli.md#build-packages)). Backend version 5
* Branch build (optional, `[branch-build]`): builds on a branch with a ticket number go into libraries of the ticket, e.g. `#be_337`. `run` creates them. New argument `--branch`, `build_context` in the build list ([docs](docs/branch-build.md)). Backend version 6

### Changed

* Each command writes its joblog into its own temporary file
* A raw `cmd` step of the extended source processing runs only once. The steps of the source type are only added with `add_default_steps = true`

### Fixed

* JSON files (e.g. `source-infos`) are read as UTF-8, also on Windows

* Commands that fail without writing to `stderr` are detected as `failed` (not yet with `global.cmds.dspjoblog`)
* If the IBM i job of a command ends abnormally (e.g. `CRTPRTF` with `OPTION(*EVENTF)` into a missing library), the error shows the signal and the joblog of the ended job is collected
* The status `failed` is saved in the build list
* Nested variables are resolved completely, circular ones no longer recurse endlessly
* `ALWAYS_TRANSFER_RELATED_COPYBOOKS` and `global.cmds.evfevent-export` are optional
* Copybooks of one build list no longer show up in the next one
* Output and log work again after an error in an extended source processing script
* Numbers and dates in the user configuration no longer cause a `TypeError`
* Empty values in the user configuration are always ignored
