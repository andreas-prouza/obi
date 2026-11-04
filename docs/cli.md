[← Back to README](../README.md)

# Command line

- [Usage](#usage)
- [Arguments](#arguments)
- [Actions](#actions)
- [Processing service](#processing-service)
- [Status and exit codes](#status-and-exit-codes)
- [Examples](#examples)


## Usage

```sh
<obi>/venv/bin/python -X utf8 <obi>/main.py -a <action> -p <project> [options]
```

* `-X utf8` makes Python use UTF-8 for files and output. Use it on IBM i.
* OBI changes into the project folder (`-p`). All paths in the configuration are relative to it.
* The project needs `.obi/etc/constants.py` and `.obi/etc/logger_config.py` (see [Configuration](configuration.md#files)).


## Arguments

| Argument | Mandatory | Description |
|---|---|---|
| `-a`, `--action` | ✅ | The [action](#actions) to run |
| `-p`, `--set-path` | ✅ | Project folder |
| `-s`, `--source` | | A source, relative to the source directory (e.g. `mylib/qrpglesrc/order.rpgle.pgm`). Used by `create` and `add_source` |
| `-c`, `--compile-list-dir` | | Folder of the build list. The file name stays as configured in `compile-list`. Relative to the project folder. Used by all actions that read or write the build list |
| `-e`, `--editor` | | Command to open the summary with (`open_result`). Default `code` |
| `-j`, `--job` | | Job of the [processing service](#processing-service) (`watch`, `cancel`) |
| `--since` | | Only the events after this `seq` (`watch`). Default `0` |


## Actions

| Action | Description |
|---|---|
| [`create`](#create) | Create the build list |
| [`add_source`](#add_source) | Add a source to an existing build list |
| [`run`](#run) | Build the build list |
| [`results`](#results) | Create the summary document again |
| [`open_result`](#open_result) | Create the summary and open it |
| [`gen_obj_list`](#gen_obj_list) | Mark all sources as built |
| [`gen_src_list`](#gen_src_list) | Write the list of all sources |
| [`submit`](#submit) | Build the build list with the processing service |
| [`watch`](#watch) | Follow a job of the processing service |
| [`jobs`](#jobs) | Jobs of the project |
| [`cancel`](#cancel) | Remove a job from the queue, or stop it |

### create

Creates the build list (`compile-list`) for all new and changed sources and their dependent objects.
See [How a build works](build-process.md) for the details.

* Without `-s`: all sources in the source directory with a supported type
* With `-s`: only this source (always, even if it didn't change) and its dependent objects

> ⚠️ `create` first **deletes** the folder `build-output-dir` (default `.obi/build-output`), including the results of the last build.

Writes: build list, [changed and dependent objects](files.md#changed-and-dependent-objects), [object list](files.md#object-list), [summary](files.md#summary-document).

### add_source

Adds a source (`-s`, mandatory) to the existing build list, e.g. to build one more source together with the current changes.

* The source and all objects depending on it are added, with new build commands
* Sources already in the list keep their results. If one of them depends on the new source and was built successfully, it is reset to be built again
* The levels of the whole list are calculated again
* Nothing is deleted. If something fails (e.g. a rule of the extended source processing), no file is changed

See [Adding a source](build-process.md#adding-a-source) for the rules.
In `status.json`, `added` lists the sources that were added and `reset` the sources that will be built again.

### run

Builds the build list, level by level. Sources that were already built successfully are skipped,
so after fixing an error you can simply run it again.
See [Running the build](build-process.md#5-running-the-build).

At the end, the summary document is created.

### results

Creates the [summary document](files.md#summary-document) from the build list again.

### open_result

Like `results`, then opens `compiled-object-list-md` with the editor command (`-e`, default `code`).

### gen_obj_list

Writes the hash of every source into `compiled-object-list` (`.obi/etc/object-builds.json`).
This means "everything is built": the next `create` only finds sources that change afterwards.
Use it after setting up a project with existing objects.

### gen_src_list

Writes the hash of every source into `source-list`.


## Processing service

These actions build with the [processing service](processing-service.md): the build keeps running when the connection ends.
They write their result to `stdout` as JSON, one object per line.

### submit

Adds the build of the build list to the queue, like `run` would build it (`-c` for another folder of the build list).
Starts the service if it isn't running.

```json
{"status": "ok", "job": {"id": 17, "status": "queued", ...}, "service": "started"}
```

* `service`: `running` (was already running), `started`, or `not running` (couldn't be started; then there is a `warning`, and the job waits in the queue)
* Also written to `status.json`
* Rejected if the build list has already a job that is queued or running

### watch

Writes the [events](processing-service.md#events) of the job (`-j`, mandatory) as they happen, and ends after the last one (`ended`).
With `--since <seq>`, it starts after this event, e.g. after a lost connection.

### jobs

The last 50 jobs of the project, the newest first: `{"status": "ok", "jobs": [...]}`. See [Jobs](processing-service.md#jobs).

### cancel

Stops the job (`-j`, mandatory): a queued job is removed from the queue, a running job is stopped. `{"status": "ok", "job": {...}}`, also written to `status.json`.
The job ends with the status `cancelled`; `watch` shows it with the event `ended`.

`-j` must be a job of the project `-p`.


## Status and exit codes

Every action writes `.obi/build-output/status.json`:

```json
{
  "version": 4,
  "status": "ok"
}
```

| Key | Content |
|---|---|
| `version` | Version of the OBI backend. Clients use it to detect an outdated backend |
| `status` | `ok` or `error` |
| `message`, `details` | Error message (only for `error`) |
| `added`, `reset` | Sources added and reset (only `add_source`) |
| `job`, `service`, `warning` | The job (only `submit` and `cancel`) |

`watch` and `jobs` don't write `status.json`, because a job may write it at the same time. Their result, also an error, is only on `stdout`.

`status` only tells whether OBI could do its job. **A failed build is still `ok`**: the result of every source and command is in the [build list](files.md#build-list).

| Situation | Exit code | `status.json` |
|---|---|---|
| Action done, also if a build failed | 0 | `ok` |
| Error in the action (e.g. invalid source, invalid configuration) | 0 | `error` with message |
| Python older than 3.12 | 1 | `error` with message |
| Missing `.obi/etc/constants.py` or `logger_config.py` | 1 | not written (Python error on the console) |
| Invalid arguments | 2 | not written (usage on the console) |
| Error in `watch` or `jobs` (e.g. unknown job) | 1 | not written (`{"status": "error", ...}` on `stdout`) |

`create` deletes the build output at the beginning and writes no new `status.json` on success, so there is none afterwards.

Details are in the log, configured in `.obi/etc/logger_config.py` (usually `.obi/log/main.log`).


## Examples

Build only one source and the objects depending on it:

```sh
python -X utf8 ~/obi/main.py -a create -p . -s mylib/qrpglesrc/order.rpgle.pgm
python -X utf8 ~/obi/main.py -a run -p .
```

Add another source to the current build list and build again:

```sh
python -X utf8 ~/obi/main.py -a add_source -p . -s mylib/qrpglesrc/invoice.rpgle.pgm
python -X utf8 ~/obi/main.py -a run -p .
```

Keep the build list in a separate folder:

```sh
python -X utf8 ~/obi/main.py -a create -p . -c .obi/my-build
python -X utf8 ~/obi/main.py -a run -p . -c .obi/my-build
```

Run on IBM i from your PC:

```sh
ssh my-ibmi 'cd ~/projects/my-project && ~/obi/venv/bin/python -X utf8 ~/obi/main.py -a run -p .'
```

Build with the processing service, so the build continues if the connection ends:

```sh
ssh my-ibmi 'cd ~/projects/my-project && ~/obi/venv/bin/python -X utf8 ~/obi/main.py -a submit -p .'
ssh my-ibmi 'cd ~/projects/my-project && ~/obi/venv/bin/python -X utf8 ~/obi/main.py -a watch -p . -j 17'
# Connection lost after the event with seq 42:
ssh my-ibmi 'cd ~/projects/my-project && ~/obi/venv/bin/python -X utf8 ~/obi/main.py -a watch -p . -j 17 --since 42'
```
