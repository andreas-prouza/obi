[← Back to README](../README.md)

# Processing service

- [How it works](#how-it-works)
- [Usage](#usage)
- [Events](#events)
- [Jobs](#jobs)
- [Settings](#settings)
- [What happens if ...](#what-happens-if-)
- [Security](#security)
- [Good to know](#good-to-know)

With `run`, the build runs in the SSH session of the client. If the session ends (network, VS Code closed, laptop goes to sleep), the client loses the build.

The processing service runs the build instead. The client only tells it what to build and then follows the progress.

* The build keeps running when the client or the connection ends
* The client can reconnect and continues where it stopped
* The client gets every change while the build runs: x of y sources, each command with stdout, stderr and joblog
* A build list is never built twice at the same time
* A running build can be cancelled

`run` works as before. The service is only used with `submit`.


## How it works

```
client (SSH)                         processing service (~/.obi-service)

main.py -a submit
  1. checks project and build list
  2. adds a job to the queue
  3. starts the service, if needed
  4. wakes it up          -------->  5. takes the job from the queue
                                     6. starts `main.py -a run --job <id>`
                                        in its own session
main.py -a watch -j <id>
  writes the events      <--------   7. the job writes an event for each change
  until the job ends                     and a heartbeat into the queue
```

* **One service per user.** It runs under your user profile, so a build runs exactly as with `run`: same authorities, same owner of the created objects, same environment.
* The job is the normal `run`, so the build list, the summary and `status.json` are written as usual.
* The service starts by itself with the first `submit` and ends by itself after `idle-timeout` without jobs.
* The queue is a SQLite database. Clients, the service and the jobs only communicate through it. The wake-up (a local socket) only makes the build start immediately.


## Usage

```sh
cd /home/me/my-project
~/obi/venv/bin/python -X utf8 ~/obi/main.py -a create -p .
~/obi/venv/bin/python -X utf8 ~/obi/main.py -a submit -p .            # {"status": "ok", "job": {"id": 17, ...}, "service": "started"}
~/obi/venv/bin/python -X utf8 ~/obi/main.py -a watch -p . -j 17       # one event per line, until the job ends
```

| Action | Description |
|---|---|
| `submit` | Adds the build of the build list to the queue and starts the service if needed. Takes `-c` like `run` |
| `watch -j <id> [--since <seq>]` | Writes the events of the job, as they happen, until the job has ended. With `--since`, only the events after this `seq` |
| `jobs` | The last 50 jobs of the project |
| `cancel -j <id>` | Removes a queued job from the queue, or stops a running one |

All of them write JSON to `stdout`, one object per line. See [Command line](cli.md#processing-service) for the details and exit codes.

**After a lost connection**, the client calls `watch` again with the `seq` of the last event it got: `watch -j 17 --since 42`.

The service itself (optional, `submit` starts it):

```sh
~/obi/venv/bin/python ~/obi/service.py status     # running?, queued and running jobs
~/obi/venv/bin/python ~/obi/service.py stop       # running jobs continue
~/obi/venv/bin/python ~/obi/service.py start
~/obi/venv/bin/python ~/obi/service.py restart
```


## Events

`watch` writes one JSON object per line:

```json
{"seq": 8, "time": "2026-11-04T10:15:02.345678", "type": "cmd_finished", "level": 1,
 "source": "mylib/qrpglesrc/order.rpgle.pgm", "cmd_index": 0, "cmd": "cl -v \"CRTBNDRPG ...\"",
 "status": "success", "updated": "2026-11-04T10:15:02.345012",
 "exit-code": 0, "stdout": "...", "stderr": "", "joblog": "...",
 "progress": {"sources": 12, "sources_done": 3, "sources_failed": 0, "cmds": 30, "cmds_done": 8}}
```

(Shown on several lines here. In the output, an event is always one line.)

| Type | When | Content |
|---|---|---|
| `queued` | `submit` | `position` in the queue |
| `started` | The build starts | `progress` with the totals |
| `level_started` | Before a level | `level`, `sources` (number of sources) |
| `source_started` | Before the first command of a source | `level`, `source` |
| `cmd_started` | Before a command | `level`, `source`, `cmd_index`, `cmd` |
| `cmd_finished` | After a command | as above, with `status`, `updated`, `exit-code`, `stdout`, `stderr`, `joblog`, `progress` |
| `source_finished` | After the last command of a source, or after its failure | `level`, `source`, `status`, `hash`, `progress` |
| `ended` | Always the last event | `status`, `build_status`, `error`, `progress` (see [Jobs](#jobs)) |

* `seq` starts at 1 and has no gaps.
* `cmd_index` is the position of the command in `cmds` of the source in the build list.
* `progress` only counts what this job builds: sources and commands that are not ignored and were not built successfully before. `sources_done` and `cmds_done` include the failed ones.
* Sources that are skipped (ignored, built before, or not started after an error) have no events.
* Everything is plain ASCII: line breaks and special characters are escaped (`\n`, `ü`), so the encoding of the connection doesn't matter.
* The build list stays the complete result. Compile messages (evfevent) and output files are downloaded as before. With `source_finished`, a client can already download them per source.


## Jobs

`submit`, `jobs` and `cancel` return jobs:

| Field | Content |
|---|---|
| `id` | Number, unique per user |
| `project` | Project folder |
| `compile_list` | Build list |
| `status` | `queued`, `running`, `finished`, `failed`, `cancelled` |
| `build_status` | `success` or `failed`, only for `finished` |
| `error` | Why the job `failed`, e.g. an OBI error or a process that died |
| `progress` | Last progress (see [Events](#events)). Updated with the heartbeat and at the end |
| `queued`, `started`, `ended` | Timestamps |
| `pid`, `heartbeat`, `cancel_requested` | Process of the job, last sign of life and time of the cancel (seconds since 1970) |

`status` tells whether OBI could do its job, `build_status` whether the build was successful.
Same as with `run`: a failed build is still `finished`, the result of each source is in the build list.

A build list can only have one job that is `queued` or `running`. A second `submit` is rejected.


## Settings

Optional file `~/.obi-service/settings.toml`. These are settings of the user, for all projects.

```toml
max-parallel-jobs = 4
idle-timeout = 3600
```

| Key | Default | Description |
|---|---|---|
| `max-parallel-jobs` | `2` | Jobs (build lists) that run at the same time. The others wait in the queue |
| `idle-timeout` | `1800` | Seconds without queued or running jobs until the service ends. `0`: never |
| `poll-interval` | `5` | Seconds between two looks into the queue without a wake-up |
| `heartbeat-interval` | `10` | Seconds between two signs of life of a job |
| `heartbeat-timeout` | `60` | Seconds without a sign of life until a job counts as dead |
| `cancel-timeout` | `30` | Seconds after `cancel` until a job that didn't end is killed |
| `keep-jobs-days` | `7` | Ended jobs and their files are deleted after this time. `0`: never |

Invalid values are ignored (with a warning in the service log). Restart the service after a change: `service.py restart`.

The directory can be changed with the environment variable `OBI_SERVICE_DIR`.


## What happens if ...

| Situation | Behaviour |
|---|---|
| The client or the SSH connection ends | The build continues. `watch --since <seq>` continues after a reconnect |
| The service is stopped or restarted | Running builds continue. Queued jobs are started with the next start |
| The service isn't running at `submit` | `submit` starts it. If that fails, the job waits in the queue and `submit` returns a `warning` |
| A build list is submitted twice | The second `submit` is rejected as long as the first job is queued or running |
| More jobs than `max-parallel-jobs` | They wait in the queue and start one after another |
| `cancel` of a queued job | It's removed from the queue (`cancelled`) |
| `cancel` of a running job | The running commands are stopped and get the status `failed`. No further source is started. The summary is written, the job ends as `cancelled`. If it doesn't end within `cancel-timeout`, it's killed |
| The job process dies (killed, system restart) | Its remaining commands are stopped, the job is set to `failed` with the reason in `error`. Run it again: only what's left is built |
| No sign of life for `heartbeat-timeout` | The job is set to `failed`. If its process still exists, it stops its build by itself |
| No jobs for `idle-timeout` | The service ends. The next `submit` starts it again |


## Security

* No network port. The socket only wakes the service up, its content is ignored.
* The directory `~/.obi-service` is only accessible for you (`700`). The service and all actions refuse to work if it belongs to another user or others have access to it.
* Jobs run under your own profile. The service can't do anything you can't do: no other profile, no special authorities.
* The commands come from the build list of the project, as with `run`.
* A signal is only sent to a job whose heartbeat is current, so a process that got the same pid later is never hit.
* No additional Python package.


## Good to know

* **Environment**: jobs run with the environment of the service, which is the environment of the command that started it (usually the first `submit`). With the VS Code extension, that's the same as for `run`. After you changed your environment (e.g. `PATH`), restart the service.
* **Files**: `~/.obi-service/`

  | File | Content |
  |---|---|
  | `jobs.sqlite` | The queue |
  | `jobs/<id>/events.jsonl` | Events of the job |
  | `jobs/<id>/output.log` | Console output of the job process |
  | `log/service.log` | Log of the service. `log/service-output.log`: errors during its start |
  | `settings.toml` | [Settings](#settings) |
  | `service.lock`, `service.pid`, `service.sock` | Lock, process id and wake-up of the running service |

  The log of the build itself is in the project, as with `run`.
* **Long path**: the path of the socket is limited to about 100 characters. With a longer service directory the service runs without wake-up: a job starts within `poll-interval` seconds. Use a shorter `OBI_SERVICE_DIR` to avoid it.
* **Windows**: the service only runs on IBM i and other Unix systems. OBI on Windows (e.g. `create` locally) is not affected.
* **Updates of OBI**: running jobs keep the code they started with. Restart the service after an update.
