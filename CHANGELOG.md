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

### Changed

* Each command writes its joblog into its own temporary file
* A raw `cmd` step of the extended source processing runs only once. The steps of the source type are only added with `add_default_steps = true`

### Fixed

* Commands that fail without writing to `stderr` are detected as `failed` (not yet with `global.cmds.dspjoblog`)
* The status `failed` is saved in the build list
* Nested variables are resolved completely, circular ones no longer recurse endlessly
* `ALWAYS_TRANSFER_RELATED_COPYBOOKS` and `global.cmds.evfevent-export` are optional
* Copybooks of one build list no longer show up in the next one
* Output and log work again after an error in an extended source processing script
* Numbers and dates in the user configuration no longer cause a `TypeError`
* Empty values in the user configuration are always ignored
