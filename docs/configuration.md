[← Back to README](../README.md)

# Configuration

- [Files](#files)
- [Project and user configuration](#project-and-user-configuration)
- [Settings](#settings)
- [Commands and steps](#commands-and-steps)
- [Variables](#variables)
- [Per-source settings](#per-source-settings)
- [Secrets](#secrets)

All configuration is in the `.obi` folder of the project.
This page describes what the OBI backend reads. The VS Code extension has its own [configuration guide](https://github.com/andreas-prouza/obi-extension/blob/main/asserts/docs/configuration.md), with the settings of the extension and the editor.


## Files

| File | Content |
|---|---|
| `.obi/etc/constants.py` | Locations of the other files. Read first |
| `.obi/etc/logger_config.py` | Python logging setup (log file, level) |
| `.obi/etc/app-config.toml` | Project configuration |
| `.obi/etc/.user-app-config.toml` | User configuration |
| `.obi/etc/source-config.toml` | [Per-source settings](#per-source-settings) |
| `.obi/etc/extended-source-processing-config.toml` | [Extended source processing](extended-source-processing.md), project |
| `.obi/etc/.user-extended-source-processing-config.toml` | Extended source processing, user |
| `.obi/etc/workspace-settings.json` | Active profile: `{"current_profile": "<name>"}` |
| `.obi/etc/dependency.json` | [Dependencies](build-process.md#2-dependencies) |
| `.obi/etc/object-builds.json` | Hashes of the built sources ([change detection](build-process.md#1-change-detection)) |
| `.obi/etc/scripts/` | Python scripts for [extended source processing](extended-source-processing.md#scripts) |

All TOML files are read with the Python package [`toml`](https://github.com/uiri/toml), which supports TOML 0.5. For example, a list can't mix strings and tables.
A file that can't be read counts as empty, and the error is only written to the log.

### constants.py

The VS Code extension creates this file. Its values are paths relative to the project folder:

```python
CONFIG_TOML = '.obi/etc/app-config.toml'
CONFIG_USER_TOML = '.obi/etc/.user-app-config.toml'
SOURCE_CONFIG_TOML = '.obi/etc/source-config.toml'
DEPENDEND_OBJECT_LIST = '.obi/tmp/dependend-object-list.json'
CHANGED_OBJECT_LIST = '.obi/tmp/changed-object-list.json'
EXTENDED_SOURCE_PROCESS_CONFIG = '.obi/etc/extended-source-processing-config.toml'
EXTENDED_SOURCE_PROCESS_CONFIG_USER = '.obi/etc/.user-extended-source-processing-config.toml'
ESP_SCRIPT_FOLDER = '.obi/etc/scripts'
UPDATE_OBJECT_LIST = False
WORKSPACE_SETTINGS_JSON = '.obi/etc/workspace-settings.json'
```

`UPDATE_OBJECT_LIST = True` makes `run` store the hash of each built source; see [Change detection](build-process.md#1-change-detection).

> Older projects may have `EXTENDED_SOURCE_PROCESS_CONFIG_TOML` instead of `EXTENDED_SOURCE_PROCESS_CONFIG`. OBI doesn't read that name, so the project rules of the extended source processing are not used. Rename it.


## Project and user configuration

* The **project configuration** holds what the team shares.
* The **user configuration** has the same structure and overrides it, e.g. with your own target library.
  Empty values (`""`, `[]`) do not override; `false` does.
* **Profiles**: if `workspace-settings.json` contains `"current_profile": "test"`, the user configuration is `.user-app-config-test.toml`,
  and the user rules of the extended source processing are in `.user-extended-source-processing-config-test.toml`.


## Settings

### General

Section `[general]`.

| Key | Default | Description |
|---|---|---|
| `local-base-dir` | | Project folder. Usually `.` |
| `source-dir` | | Source directory below `local-base-dir`, e.g. `src` |
| `supported-object-types` | | Last file extensions of the sources to build, e.g. `["pgm", "srvpgm", "file", "module", "cpy"]` |
| `max-parallel-builds` | `1` | Sources built in parallel; see [Parallel builds](build-process.md#parallel-builds) |
| `file-system-encoding` | `utf-8` | Encoding of file names |
| `console-output-encoding` | `utf-8` | Encoding of the command output |
| `compile-list` | `.obi/tmp/compile-list.json` | [Build list](files.md#build-list). The folder can be changed with `-c` |
| `compiled-object-list` | | Hashes of the built sources, e.g. `.obi/etc/object-builds.json` |
| `dependency-list` | | Dependencies, e.g. `.obi/etc/dependency.json` |
| `deployment-object-list` | | [Object list](files.md#object-list), e.g. `.obi/build-output/object-list.txt` |
| `compiled-object-list-md` | `.obi/build-output/compiled-object-list.md` | [Summary document](files.md#summary-document) |
| `build-output-dir` | `.obi/build-output` | Output of the build. Deleted by `create` |
| `source-list` | | Output of `gen_src_list` |

Other keys (e.g. `remote-host`, `max-threads`) are used by the VS Code extension. All keys of `[general]` are also [variables](#variables).

### Compile settings

Section `[global.settings.general]`: values for all build commands, available as [variables](#variables), e.g. `TGTRLS`, `DBGVIEW`, `ACTGRP`, `LIBL`.

| Key | Description |
|---|---|
| `LIBL` | Library list, e.g. `["$(TARGET_LIB)", "QGPL"]`. `$(SET_LIBL)` adds each entry with the command `global.cmds.add-lible` |
| `TARGET_LIB` | Library to build into. `*SOURCE` or empty: the library folder of the source (`mylib` in `mylib/qrpglesrc/order.rpgle.pgm`) |
| `TARGET_LIB_MAPPING` | Replaces the target library, e.g. `{ prodlib = "devlib" }` |
| `ALWAYS_TRANSFER_RELATED_COPYBOOKS` | `true`: add related copybooks on level 0 ([Levels](build-process.md#3-levels)). Default `false` |
| `USE_ESP` | `false`: turn the [extended source processing](extended-source-processing.md) off. Default `true` |

Library names are converted to lower case.

**Language settings** override them per source type, e.g. for all `*.sqlrpgle.pgm`:

```toml
[global.settings.language."sqlrpgle.pgm"]
DBGVIEW = "*SOURCE"
```


## Commands and steps

Commands are shell commands. They run in `bash` (PASE) in the project folder; IBM i commands are called with `cl -v "..."`.

```toml
[global.cmds]
add-lible = "liblist -a '$(LIB)' 2> /dev/null"
chg-src-ccsid = "cl -v \"CHGATR OBJ('$(SOURCE_FILE_NAME)') ATR(*CCSID) VALUE(1208)\""

[global.compile-cmds]
"rpgle.pgm" = "$(SET_LIBL); cl -v \"CRTBNDRPG PGM($(TARGET_LIB)/$(OBJ_NAME)) SRCSTMF('$(SOURCE_FILE_NAME)') DBGVIEW($(DBGVIEW))\""

[global.steps]
"*ALL" = [ "global.cmds.chg-src-ccsid" ]
"rpgle.pgm" = [ "global.compile-cmds.\"rpgle.pgm\"" ]
```

A step names a command by its path in the configuration. Keys that contain dots are quoted: `global.compile-cmds."rpgle.pgm"`.

**Which steps a source gets**, the first that applies:

1. `steps` in the [per-source settings](#per-source-settings)
2. Steps of the [extended source processing](extended-source-processing.md)
3. `[global.steps]` with the exact source name as key
4. `[global.steps]` with a pattern as key that matches the source name, e.g. `"mylib/qsqlsrc/*"`
5. `[global.steps]` with the last two extensions of the source as key: `order.rpgle.pgm` → `"rpgle.pgm"`

The steps under `"*ALL"` always come first, except with 1.

**Inside a command**

* `$(NAME)` is replaced by a [variable](#variables)
* `%global.cmds.xyz%` inserts another command
* If `global.cmds.dspjoblog` is defined, it is appended to every command, with `$(joblog-separator)` replaced by `global.cmds.joblog-separator`.
  The exit code is then the one of that command, so a failed step is only detected by its output on `stderr`
* These parameters are removed if their variable has no value: `ACTGRP`, `BNDDIR` (`INCLUDE_BNDDIR`), `TGTRLS`, `STGMDL`, `TGTCCSID`, `DBGVIEW`, `INCDIR` (`INCDIR_RPGLE`, `INCDIR_SQLRPGLE`)


## Variables

`$(NAME)` can be used in commands and in the values of settings. Variables are replaced recursively; unknown variables stay as they are.

**Built-in**, for the source `src/mylib/qrpglesrc/order.rpgle.pgm`:

| Variable | Value |
|---|---|
| `$(SOURCE)` | `mylib/qrpglesrc/order.rpgle.pgm` |
| `$(SOURCE_FILE_NAME)` | `src/mylib/qrpglesrc/order.rpgle.pgm` |
| `$(SOURCE_BASE_FILE_NAME)` | `order.rpgle.pgm` |
| `$(OBJ_NAME)` | `order` |
| `$(SRC_ATTR)` | `rpgle` |
| `$(SRC_TYPE)` | `pgm` |
| `$(TARGET_LIB)` | Target library, see `TARGET_LIB` |
| `$(TARGET_LIB_ORIG)` | Target library before `TARGET_LIB_MAPPING` |
| `$(SET_LIBL)` | Commands to set the library list from `LIBL` |

**Your own variables**:

```toml
[global.variables]
MY_OPTION = "*YES"
```

**Precedence**, if the same name is defined several times (lowest first):

1. Compile settings `[global.settings.general]`
2. General settings `[general]`
3. Your own variables `[global.variables]`
4. Language settings `[global.settings.language."<type>"]`
5. Commands `[global.cmds]` (as `global.cmds.<name>`)
6. Per-source settings
7. Built-in variables


## Per-source settings

`.obi/etc/source-config.toml`, with the source name relative to `source-dir` as key:

```toml
["mylib/qrpglesrc/order.rpgle.pgm"]
settings = { ACTGRP = "ORDER", TARGET_LIB = "testlib" }
source-cmds = { prepare = "cl -v \"CALL MYLIB/PREPARE\"" }
steps = [ "source-cmds.prepare", "global.compile-cmds.\"rpgle.pgm\"" ]
```

* `settings` override all other settings for this source
* `source-cmds` are commands only for this source
* `steps`, if not empty, replace all other steps of this source (also `*ALL` and the extended source processing)


## Secrets

Variables in `[global.variables]` whose names start with `secret` are not used as variables, so they don't appear in commands or in the build list.

All other values are written into the build list (`variables`), into the object list and into the log.
Don't put passwords or tokens into `[general]` or the settings.
