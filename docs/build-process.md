[← Back to README](../README.md)

# How a build works

- [1. Change detection](#1-change-detection)
- [2. Dependencies](#2-dependencies)
- [3. Levels](#3-levels)
- [4. Build commands](#4-build-commands)
- [5. Running the build](#5-running-the-build)
- [6. Summary](#6-summary)
- [Adding a source](#adding-a-source)

`create` does steps 1 to 4 and writes the [build list](files.md#build-list). `run` does steps 5 and 6.


## 1. Change detection

OBI computes the MD5 hash of every source in `source-dir` whose last extension is in `supported-object-types`,
and compares it with `compiled-object-list` (`.obi/etc/object-builds.json`):

| Source | Result |
|---|---|
| Not in the list | **new** |
| Different hash, or `null` | **changed** |
| Same hash | not built |

With `create -s <source>` only that source is used, and it is always new or changed.

**Who updates the hashes?**
`run` sets the hash of every source in the build list to `null` before it starts, so these sources count as changed until they are built.

* With the VS Code extension: the extension sets the hashes of the successfully built sources after it downloaded the results.
* Without the extension: set `UPDATE_OBJECT_LIST = True` in `.obi/etc/constants.py`. Then `run` stores the new hash of each successfully built source.

`gen_obj_list` stores the hashes of all sources ("everything is built").


## 2. Dependencies

`dependency-list` (`.obi/etc/dependency.json`) lists, for each source, the sources it uses:

```json
{
  "mylib/qrpglesrc/order.rpgle.pgm": [
    "mylib/qrpglesrc/date.sqlrpgle.srvpgm",
    "mylib/qcpysrc/order.rpgle.cpy"
  ]
}
```

For every new or changed source, OBI adds all sources that use it, and all sources that use those, and so on.
Sources that don't exist in `source-dir` are ignored.

The VS Code extension can maintain this file; see [Dependencies](https://github.com/andreas-prouza/obi-extension/blob/main/asserts/docs/dependencies.md).


## 3. Levels

The build list is ordered in levels. A level is built only after the previous one is finished.

* New and changed sources are on level 1
* An object that uses a source is one level higher than that source
* An object that appears several times is built only once, on its highest level
* Within a level, files (`*.file`) come first

**Copybooks**: with `ALWAYS_TRANSFER_RELATED_COPYBOOKS = true` (in `[global.settings.general]`), all copybooks (`*.cpy`) used directly or indirectly by the sources in the list are added on level 0.
They usually have no build commands; the VS Code extension uses this list to upload them to IBM i.


## 4. Build commands

For each source, OBI selects its build steps and replaces all variables in their commands.
See [Commands and steps](configuration.md#commands-and-steps) and [Extended source processing](extended-source-processing.md).

The resolved variables of each source are stored in the build list as `variables`.


## 5. Running the build

`run` builds the build list level by level. Within a source, the commands always run one after the other.

**Sources that are skipped**

* Sources with `"ignore": true`
* Sources whose commands were all successful
* Commands with `"ignore": true`

So after fixing an error you can run the same build list again: only the remaining sources are built.

**Commands** run in `bash` in the project folder. After each command, OBI collects the joblog with `cl -v "dspjoblog"`.
A command fails if its exit code is not 0 or if it writes anything to `stderr`.
Status, output, joblog and errors are stored in the build list after every command, so a client can show the progress.

### Parallel builds

Sources in the same level don't depend on each other, so they can be built at the same time.
Set the maximum number of sources built in parallel in the configuration:

```toml
[general]
max-parallel-builds = 4
```

* Default is `1`: one source after the other
* Levels are always built one after the other
* Start with a low value. Sources of one level can still lock the same object, e.g. service programs that add entries to the same binding directory
* `max-threads` is a different setting (used by the VS Code extension, e.g. to hash sources) and doesn't change the build

### Errors

When a command fails:

* the remaining commands of that source are not run, and the source gets the status `failed`
* no other source and no other level is started
* sources that are already running (parallel builds) are finished

The build list then contains the result of every command that ran. `run` still ends with the status `ok`; see [Status and exit codes](cli.md#status-and-exit-codes).


## 6. Summary

At the end, OBI writes a Markdown summary (`compiled-object-list-md`) with the new, changed and dependent sources, all levels, and the status and outputs of each command.
See [Summary document](files.md#summary-document).


## Adding a source

`add_source` adds a source to an existing build list without creating it again:

| Source | What happens |
|---|---|
| The added source, not in the list | Added, with new build commands |
| The added source, already in the list | Gets new build commands and is reset, whatever its status was |
| Sources depending on it, not in the list | Added, with new build commands |
| Sources depending on it, already in the list and built successfully | Reset: the status of all commands is set to `new`, the result of the source is removed. The commands and their output are kept |
| Sources depending on it, already in the list, not built successfully | Not changed; they will be built anyway |
| All other sources | Not changed |
| Related copybooks (with `ALWAYS_TRANSFER_RELATED_COPYBOOKS`) | Added on level 0 if missing |

Afterwards, the levels of the whole list are calculated again. If the added source is used by sources already in the list, those move to a higher level.

Other content of the build list (e.g. `custom_data` of the VS Code extension, `ignore`) is kept.
The changed and dependent objects and the object list are updated, and the summary is created again.
