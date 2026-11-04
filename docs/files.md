[← Back to README](../README.md)

# Files

- [Build list](#build-list)
- [Changed and dependent objects](#changed-and-dependent-objects)
- [Object list](#object-list)
- [Summary document](#summary-document)
- [Status](#status)
- [Built sources](#built-sources)
- [Temporary files and log](#temporary-files-and-log)
- [Processing service](#processing-service)

The locations are the defaults; most of them can be changed in the [configuration](configuration.md#general).


## Build list

`compile-list` (`.obi/build-output/compile-list.json`): what to build, in which order, and the result of every command.
Written by `create` and `add_source`, updated by `run` after every command.

```json
{
  "timestamp": "2026-11-03 10:15:00.123456",
  "compiles": [
    {
      "level": 1,
      "sources": [
        {
          "source": "mylib/qrpglesrc/order.rpgle.pgm",
          "status": "success",
          "hash": "5d41402abc4b2a76b9719d911017c592",
          "absolute_path": "/home/me/my-project/src/mylib/qrpglesrc/order.rpgle.pgm",
          "variables": { "TARGET_LIB": "mylib", "OBJ_NAME": "order" },
          "cmds": [
            {
              "cmd": "cl -v \"CRTBNDRPG PGM(mylib/order) ...\"",
              "status": "success",
              "properties": {},
              "updated": "2026-11-03T10:15:02.345678",
              "exit-code": 0,
              "stdout": "...",
              "stderr": "",
              "joblog": "..."
            }
          ]
        }
      ]
    }
  ]
}
```

**Source**

| Key | Description |
|---|---|
| `source` | Source name, relative to `source-dir` |
| `cmds` | The commands, in the order they run |
| `variables` | All [variables](configuration.md#variables) of the source |
| `status` | `in process`, `success` or `failed`. Missing until the source was built |
| `hash` | Hash of the source when it was built successfully |
| `absolute_path` | Full path of the source, set by `run` |
| `ignore` | `true`: don't build this source |

**Command**

| Key | Description |
|---|---|
| `cmd` | The shell command |
| `status` | `new`, `in process`, `success` or `failed` |
| `properties` | Variables of this step (see [steps](extended-source-processing.md#steps)) |
| `updated` | Time of the last status change |
| `exit-code`, `stdout`, `stderr`, `joblog` | Result of the command |
| `ignore` | `true`: don't run this command |

Level `0` contains the related copybooks (see [Levels](build-process.md#3-levels)).
Other keys, e.g. those the VS Code extension adds (`config`, `custom_data`, `git`, `change-history`), are kept by OBI.


## Changed and dependent objects

* `CHANGED_OBJECT_LIST` (`.obi/tmp/changed-object-list.json`): `{"new-objects": [...], "changed-sources": [...]}`
* `DEPENDEND_OBJECT_LIST` (`.obi/tmp/dependend-object-list.json`): list of the sources that are built because they depend on a new or changed source

Both are used for the summary document.


## Object list

`deployment-object-list` (`.obi/build-output/object-list.txt`): a JSON list with one entry per source of the build list, for deployment tools.

| Key | Description |
|---|---|
| `level` | Level in the build list |
| `to_prod_lib` | Library folder of the source |
| `from_deploy_lib` | Target library of the build |
| `obj_name`, `obj_type`, `obj_attr` | e.g. `order`, `pgm`, `rpgle` |
| `source` | Source name |
| `cmds` | The commands |
| `data` | All variables of the source |


## Summary document

`compiled-object-list-md` (`.obi/build-output/compiled-object-list.md`): Markdown with the new, changed and dependent sources, and every level with the status and commands of its sources, with links to their outputs.

It is created from the template [`docs/summary-template.md`](summary-template.md) of OBI.


## Status

`.obi/build-output/status.json`: result of the last action. See [Status and exit codes](cli.md#status-and-exit-codes).


## Built sources

`compiled-object-list` (`.obi/etc/object-builds.json`): source name → hash of the last successful build, or `null` if it has to be built. See [Change detection](build-process.md#1-change-detection).

```json
{
  "mylib/qrpglesrc/order.rpgle.pgm": "5d41402abc4b2a76b9719d911017c592",
  "mylib/qrpglesrc/date.sqlrpgle.srvpgm": null
}
```


## Temporary files and log

| File | Content |
|---|---|
| `.obi/tmp/objects_tree.json`, `ordered_target_tree.json`, `new_target_tree.json` | Intermediate results of `create`, for analysis |
| `.obi/log/joblog.txt.<id>` | Joblog of a running command. Removed after the command |
| Log file | As configured in `.obi/etc/logger_config.py`, usually `.obi/log/main.log` |


## Processing service

Not in the project, but in the directory of the user's [processing service](processing-service.md) (`~/.obi-service`, or `OBI_SERVICE_DIR`):
the queue (`jobs.sqlite`), the events and console output of each job (`jobs/<id>/`), the log and the settings.
See [Good to know](processing-service.md#good-to-know).

A build of the service writes the same files in the project as `run`.
