[← Back to README](../README.md)

# Branch build

- [When it's active](#when-its-active)
- [Configuration](#configuration)
- [Target library](#target-library)
- [Library list](#library-list)
- [Creating the libraries](#creating-the-libraries)
- [Build list](#build-list)
- [Variables](#variables)
- [Removing branch libraries](#removing-branch-libraries)

With a branch build, every ticket gets its own libraries. A build on the branch `ABC-337-order-rework` goes into `#be_337` instead of the main libraries (e.g. `#h_beobj`). Developers on different tickets don't overwrite each other's objects, and the main libraries keep the state of the main branch.

The feature is **optional**. Without a `[branch-build]` section, OBI builds exactly as before: it doesn't call git, and the build list has no `build_context`. You need neither git nor a `TARGET_LIB_MAPPING` to use OBI.


## When it's active

| Situation | Builds into |
|---|---|
| No `[branch-build]` section, or `enabled = false` | Main libraries, as before |
| Branch name matches `ticket-pattern` | Branch libraries of the ticket |
| Branch name doesn't match (e.g. `main`, `dev-setup`) | Main libraries |
| Detached HEAD, no git repository, git not installed | Main libraries, with a warning in the log and in `build_context` |

The branch comes from `--branch` (the VS Code extension passes it). Without it, OBI runs `git rev-parse --abbrev-ref HEAD` in the project folder.

If the section exists but is incomplete or invalid, `create` and `add_source` stop with an error. OBI never falls back to the main libraries then, because whoever configured branch builds expects the build to be isolated.


## Configuration

In `app-config.toml` (or the user configuration):

```toml
[branch-build]
ticket-pattern = '(?i)\babc[-_](\d+)'     # group 1 is the ticket number
lib-name = "#$(ENV)_$(TICKET)"
no-lib-steps = [ "global.cmds.skip" ]   # optional

[branch-build.env]                       # production library -> ENV
mylib = "BE"
mydta = "BE"
otherlib = "HOL"

[branch-build.settings]                  # optional
INCLUDE_BNDDIR = "$(TARGET_LIB)/GLOBAL"
```

| Key | Mandatory | Description |
|---|---|---|
| `enabled` | | `false` turns the feature off. Default `true` |
| `ticket-pattern` | ✅ | Regular expression for the branch name. Its first group is the ticket. Write it as a literal string (`'...'`): the `toml` package doesn't accept `\\b` in a `"..."` string |
| `lib-name` | ✅ | Name of a branch library. Must contain `$(TICKET)`; `$(ENV)` is optional. At most 10 characters after the replacement |
| `env` | if `lib-name` has `$(ENV)` | ENV for each production library (1-8 letters or digits). Several libraries can share an ENV, e.g. the program and the data library of a tenant. Then their objects go into the same branch library |
| `no-lib-steps` | | Steps that don't build anything into the target library (e.g. a message). They get no branch library, so their library needs no ENV and isn't created |
| `settings` | | Settings only for branch builds. They override all other settings, except the properties of an extended source processing step |

The `crt-branch-lib` command is optional; see [Creating the libraries](#creating-the-libraries).


## Target library

The extended source processing and its scripts still see the main libraries (`TARGET_LIB = "#h_beobj"`). OBI replaces the target library only in the build commands:

1. Target library of a main build, after `TARGET_LIB_MAPPING` and the extended source processing (`#h_beobj`)
2. Back to the production library with `TARGET_LIB_MAPPING` (`h_beobj`). Without a mapping, the library itself
3. ENV from `[branch-build.env]` (`BE`)
4. `lib-name` (`#be_337`)

**Fail-safe:** a command that uses `$(TARGET_LIB)` (also through another variable, e.g. `%global.cmds.chgjob%`) must get a branch library. If its library has no ENV, `create` stops with an error that names the source and the library. Commands that don't use the target library (e.g. copying a copybook to the IFS) and the steps in `no-lib-steps` aren't checked.

Library names are lower case, like all library names in OBI.


## Library list

`$(SET_LIBL)` gets the library list of a main build, plus the branch libraries on top:

* For each library in `LIBL` that has an ENV, its branch library is added.
* The target library is added last. `add-lible` (`liblist -a`) puts each library on top, so it ends up first.
* Branch libraries that don't exist yet are skipped: `add-lible` ignores errors (`2> /dev/null`).

Example: `LIBL = ["#h_beobj", "h_beobj", "#h_holdta", "hjiddm"]` with ENVs BE, HOL and HJI gives `#h_beobj, h_beobj, #h_holdta, hjiddm, #hol_337, #hji_337, #be_337`.


## Creating the libraries

`create` remembers in the build list every branch library a command builds into (`build_context.libs`). Before the first level, `run` creates the missing ones with `global.cmds.crt-branch-lib`. Default:

```toml
[global.cmds]
crt-branch-lib = "cl \"CHKOBJ OBJ($(LIB)) OBJTYPE(*LIB)\" > /dev/null 2>&1 || cl -v \"CRTLIB LIB($(LIB)) TYPE(*TEST) TEXT('$(BRANCH_TEXT)')\""
```

* `$(LIB)`: the library. OBI checks the name before it puts it into the command.
* `$(BRANCH_TEXT)`: `OBI <branch>`, at most 50 characters. Characters other than letters, digits, `.`, `_`, `/` and `-` are replaced by `_`.
* If a library can't be created, no source is built. The error is in `build_context.error` and in the log.

Tables and physical files in a branch library are created empty.


## Build list

`create` writes the context into the build list:

```json
"build_context": {
  "mode": "branch",
  "branch": "ABC-337-order-rework",
  "ticket": "337",
  "libs": ["#be_337", "#hol_337"]
}
```

| Key | Description |
|---|---|
| `mode` | `branch` or `main` |
| `branch`, `ticket` | Branch and ticket; `null` if unknown |
| `libs` | Branch libraries the commands build into |
| `warning` | Why it's a main build although the feature is on (e.g. no git repository) |
| `error` | Set by `run` if a library couldn't be created |

`add_source` checks that the build list was created for the same ticket (or both for the main libraries). Otherwise it stops with "Create a new build list", so one list never builds into the libraries of two tickets.


## Variables

Only while the feature is active (also for main builds):

| Variable | Value |
|---|---|
| `$(TARGET_LIB)` | The branch library in a branch build |
| `$(TARGET_LIB_MAIN)` | The target library of a main build, e.g. `#h_beobj` |
| `$(BUILD_MODE)` | `branch` or `main` |
| `$(BRANCH)` | Branch name |
| `$(TICKET)` | Ticket number, empty in a main build |
| `$(BRANCH_LIBS)` | The branch libraries added to the library list, separated by spaces (branch builds only) |


## Removing branch libraries

Branch libraries stay until they're deleted. The VS Code extension decides which ones (e.g. after the merge) and calls the action `branch_libs` on IBM i:

```sh
main.py -a branch_libs -p <project> --list
main.py -a branch_libs -p <project> --delete=#BE_337,#HOL_337
```

`--list` reads all libraries with `QSYS2.OBJECT_STATISTICS` (the `db2` utility of QShell) and keeps those that are branch libraries:

```json
{"version": 6, "status": "ok", "libs": [
  {"name": "#BE_337", "env": "BE", "ticket": "337", "text": "OBI IBMI-337-order-rework",
   "created": "2026-11-20 10:00:00", "last_used": "2026-11-21", "owner": "PROUZA", "size": 1234567}
]}
```

`--delete` runs `DLTLIB` for each library and reports the result. A library that's in use fails; the others are still deleted:

```json
{"version": 6, "status": "ok", "deleted": ["#BE_337"], "failed": [{"name": "#HOL_337", "message": "CPF2125 ..."}]}
```

**What counts as a branch library**, for both modes:

* The name matches `lib-name`. `$(ENV)` must be one of the ENVs of `[branch-build.env]`, and `$(TICKET)` must match the group of `ticket-pattern` (`\d+` in `(?i)\babc[-_](\d+)`).
* It is none of the libraries of `TARGET_LIB_MAPPING` (keys and values) and of `[branch-build.env]`.

`--delete` checks every name before it deletes anything. If one name isn't a branch library, nothing is deleted. A name that doesn't exist is reported in `failed`.

Deleting can't be undone. The next package build creates the libraries again.
