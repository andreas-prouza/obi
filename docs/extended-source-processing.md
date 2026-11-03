[← Back to README](../README.md)

# Extended source processing

- [Rules](#rules)
- [Conditions](#conditions)
- [Several matching rules](#several-matching-rules)
- [Steps](#steps)
- [Scripts](#scripts)
- [Shell commands](#shell-commands)
- [Examples](#examples)

The extended source processing (ESP) selects build steps by rules instead of by source type.
Use it for groups of sources that need other steps, e.g. all sources of one library, or all sources a script selects.
For single sources, the [per-source settings](configuration.md#per-source-settings) are simpler.


## Rules

Rules are read from the user file (`.obi/etc/.user-extended-source-processing-config.toml`, or the one of the active [profile](configuration.md#project-and-user-configuration)).
If it doesn't exist or is empty, the project file `.obi/etc/extended-source-processing-config.toml` is used. The files are not merged.

> ⚠️ A file that is not valid TOML counts as empty: the rules are not used, and the error is only written to the log. If rules have no effect, check the log first.

```toml
[[extended_source_processing]]
steps = [ "global.cmds.chg-src-ccsid", "global.cmds.my-compile" ]
use_regex = false

[extended_source_processing.conditions]
TARGET_LIB = "mylib"
```

| Key | Default | Description |
|---|---|---|
| `steps` | | The [steps](#steps) for the matching sources |
| `conditions` | | The [conditions](#conditions). Without conditions, the rule matches every source |
| `use_regex` | | `true`: the conditions are regular expressions, `false`: patterns like `*.pgm`. Always set it if the rule has conditions |
| `use_script` | | A [script](#scripts) that decides whether the rule matches |
| `use_shell` | | A [shell command](#shell-commands) that decides whether the rule matches |
| `allow_multiple_matches` | `true` | See [Several matching rules](#several-matching-rules) |

A rule matches if its conditions, its script and its shell command all match.
The steps of the matching rules **replace** the steps of the source type. The steps under `"*ALL"` still come first, and the `steps` of the [per-source settings](configuration.md#per-source-settings) still win.

Set `USE_ESP = false` in `[global.settings.general]` to turn the extended source processing off.


## Conditions

The name of a condition is a [variable](configuration.md#variables) of the source, e.g. `TARGET_LIB`, `OBJ_NAME`, `SRC_TYPE` or one of your settings.
All conditions of a rule have to match. A condition with an unknown name doesn't match.

| Value | Compared with | Example |
|---|---|---|
| A string | The value of the variable | `TARGET_LIB = "mylib"`, `OBJ_NAME = "ord*"` |
| A list | **The source name** (e.g. `mylib/qrpglesrc/order.rpgle.pgm`), whatever the name of the condition is. Matches if one entry matches | `SOURCE = ["mylib/*", "otherlib/qrpglesrc/*"]` |

With `use_regex = true`, a value matches if the regular expression is found in it (`re.search`), otherwise it has to match the pattern completely (`fnmatch`: `*`, `?`, `[abc]`).


## Several matching rules

The rules are checked in their order. By default, the steps of all matching rules are added one after the other.

`allow_multiple_matches = false` on a rule means: once this rule matched, no later rule may match the same source.
If one does, the build list is not created and the error names both rules.


## Steps

A step is either the name of a command or a table:

```toml
steps = [
  { step = "global.cmds.chg-src-ccsid", add_default_steps = false },
  { step = "global.compile-cmds.\"rpgle.pgm\"", properties = { DBGVIEW = "*ALL" }, add_default_steps = false },
  { cmd = "cl -v \"CALL MYLIB/AFTER\"" },
]
```

> ⚠️ One `steps` list contains either names or tables, not both: `[ "global.cmds.a", { cmd = "b" } ]` is not valid for the TOML reader of OBI.
> Write names as tables instead: `{ step = "global.cmds.a", add_default_steps = false }`.

| Key | Description |
|---|---|
| `step` | Name of a command |
| `cmd` | A command. Wins over `step` |
| `properties` | Variables for this step only, e.g. another `TARGET_LIB` |
| `add_default_steps` | Also add the steps of the source type after this step, with the same `properties`. Default `true` for `step`, `false` for `cmd` |
| `exit_point_script` | A [script](#exit-point-scripts) that can change the step |

A table with neither `step` nor `cmd` adds the steps of the source type with its `properties`:

```toml
steps = [ { properties = { TARGET_LIB = "otherlib" } } ]
```


## Scripts

Scripts are Python files in `ESP_SCRIPT_FOLDER` (default `.obi/etc/scripts`). They are named as `file.function`, without `.py`, optionally followed by parameters in JSON: `file.function:{"name": "value"}`.

### Match scripts

`use_script` calls the function to decide whether the rule matches:

```toml
[[extended_source_processing]]
steps = [ "global.cmds.my-compile" ]
use_script = 'rules.is_service_program:{"prefix": "srv"}'
```

```python
# .obi/etc/scripts/rules.py
def is_service_program(source: str, prefix: str, **properties) -> bool:
    return properties['OBJ_NAME'].startswith(prefix)
```

The function gets the source name as `source`, all variables of the source and the JSON parameters as keyword arguments.
The rule matches if it returns a true value. An exception stops the build list.

### Exit point scripts

`exit_point_script` on a step is called for each command the step produces (the step itself and its default steps).
It gets the source as `source`, the command as `step` (`{"step": ...}` or `{"cmd": ...}`), the other keys of the step, all variables of the source and the JSON parameters.
It returns a table that replaces the values of the step, e.g. `{"cmd": "..."}`, or `step` to keep it.

```python
def add_trace(source: str, step: dict, **kwargs) -> dict:
    return {'cmd': 'echo "Build ' + source + '"'}
```

If the returned table has `add_default_steps = true`, the steps of the source type of `properties.SOURCE_FILE_NAME` (or of the source) are added before it.


## Shell commands

`use_shell` runs a command with `sh` in the project folder. The rule matches if the exit code is 0.
`$(NAME)` is replaced by the variables of the source. Only use variables with text values; a list such as `LIBL` stops the build list with an error.

```toml
[[extended_source_processing]]
steps = [ "global.cmds.sql-set-target-lib", "global.compile-cmds.\"sqltable.file\"" ]
use_shell = 'grep -qi "create or replace" $(SOURCE_FILE_NAME)'
```


## Examples

All sources of `mylib` are built into `testlib`, with the normal steps:

```toml
[[extended_source_processing]]
steps = [ { properties = { TARGET_LIB = "testlib" } } ]
use_regex = false

[extended_source_processing.conditions]
TARGET_LIB = "mylib"
```

Programs whose name starts with `x` get an extra command before the normal steps:

```toml
[[extended_source_processing]]
steps = [ { cmd = "echo $(OBJ_NAME)" }, { properties = {} } ]
use_regex = true

[extended_source_processing.conditions]
OBJ_NAME = "^x"
SRC_TYPE = "^pgm$"
```

Make sure only one rule applies to the sources in `special`:

```toml
[[extended_source_processing]]
steps = [ "global.cmds.special-build" ]
use_regex = false
allow_multiple_matches = false

[extended_source_processing.conditions]
SOURCE = [ "mylib/special/*" ]
```
