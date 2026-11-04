# Processing service

- **Status:** in progress
- **Type:** feature


## Current situation

* The client (VS Code extension) runs `main.py -a run` over SSH and reads its output line by line.
  The build is bound to that SSH session.
* If the session ends (network, VS Code closed, laptop goes to sleep), the client loses the build: no more progress, no download of the results, no way to reconnect. The build may be stopped together with the session.
* The client only gets the result of the commands (status, stdout, stderr, joblog) after the build, by downloading the build list.
* Nothing stops two builds of the same build list at the same time. They overwrite each other's results.


## Requirements

1. A build keeps running when the client ends or the connection drops
2. The client can reconnect to a running build and continues where it stopped
3. The client gets every change while the build runs: x of y sources built, status of every source and command, with stdout, stderr and joblog
4. Builds wait in a queue. A build list is never built twice at the same time
5. A build whose process died is set to `failed`
6. A queued build can be removed, a running one can be stopped
7. Security first: no network port, no other user profile, no new package
8. `run` and all other actions work exactly as before
9. Clients can show the jobs and their progress: the VS Code extension, other clients later


## Acceptance criteria

* A build started with `submit` keeps running after the SSH connection has been closed
* `watch` reports every change of the build (with stdout, stderr and joblog of each command, and the progress x of y) and ends when the job ends
* After a reconnect, `watch --since <seq>` continues without missing or repeating an event
* `submit` starts the service if it isn't running. The build starts without a noticeable delay
* A second `submit` of the same build list is rejected as long as the first one is queued or running
* At most `max-parallel-jobs` jobs run at the same time. The others wait in the queue
* `cancel` removes a queued job. For a running job, it stops the running commands, starts no further source, still writes the summary and sets the job to `cancelled`
* A job whose process died is set to `failed` within `heartbeat-timeout`. If the service started it, its remaining commands are stopped
* Stopping or restarting the service doesn't affect running jobs
* The service ends by itself after `idle-timeout` without jobs
* The service opens no network port. It refuses to work if its directory belongs to another user or others have access to it
* Without `submit`, nothing changes


## Non-goals

* Changes in the VS Code extension. Own spec: `obi-extension/docs/features/processing-service.md` (`submit` instead of `run`, progress from `watch`, cancel with `cancel`, reconnect with `watch --since`, a view of the jobs)
* A Web GUI. The status view goes into the VS Code extension instead (see [Decisions](#status-view-in-the-vs-code-extension-not-a-web-gui))
* A Web API or any other network access to the service (see [Decisions](#communication-with-the-client-cli-over-ssh))
* One central service that runs the builds of several users
* `create` and `add_source` as jobs. They can be added later as further job types
* Download of compile messages (evfevent) and output files. The client still downloads them via SFTP. With `source_finished` it can do that per source, while the build is still running


## Decisions

Documentation: [Processing service](../processing-service.md)

### Communication with the client: CLI over SSH

The client keeps talking to OBI through SSH commands. There is no Web API for the client (for now).

| | CLI over SSH | Web API (FastAPI) |
|---|---|---|
| Login, encryption | SSH, as today | Own login (IBM i profile, e.g. via ODBC like i-Releaser, or Apache with basic auth) and TLS, or an SSH tunnel |
| Network | Nothing new | Open port on the IBM i, or SSH port forwarding (often disabled: `AllowTcpForwarding no`) |
| Build runs as | The developer's profile | The profile of the server process, also behind a proxy with basic auth. Running as the developer needs a profile switch (see below) |
| Password | Usually SSH keys | Basic auth sends the password with every request. The client has to store the IBM i password |
| New packages on IBM i | None | FastAPI, uvicorn, pydantic (i-Releaser pins `pydantic==1.10.21`, `fastapi==0.115.8`) |
| Live progress | `watch` streams events, one Python start per build | Server-sent events or WebSocket |
| Still needed | SSH and SFTP | SSH and SFTP (upload of sources, download of compile messages) |

* SSH is needed anyway. A Web API would be a second way in, with its own login and its own attack surface, without saving the first one.
* An Apache proxy with basic auth only checks who calls. It forwards the request to the server process, which keeps its own profile and gets at most the user name in a header. The build would run under the server's profile: it owns the created objects, its authorities apply, and the audit journal shows it instead of the developer.
* To run a build as the developer, the server would have to switch profiles:
  * with the password from the basic auth header (`QSYGETPH` + `QWTSETP`): cleartext passwords in the backend, a profile switch inside a multi-threaded process, ILE calls from PASE
  * without the password (`QSYGETPH` with `*NOPWD`, `SBMJOB USER(...)`): the server profile needs `*USE` to every developer profile, so it can act as any of them
* `UserID %%CLIENT%%` of the IBM HTTP Server for i runs CGI programs under the client's profile, but not a proxied application, and only for the time of a request.
* Apache with basic auth fits the Web GUI (information, like i-Releaser), not running builds as the developer.
* `watch` gives the client the same as a push API: it runs as long as the job and writes each event as it happens.
* The job functions (submit, list, events, cancel) are plain Python functions that return JSON-serializable data. The CLI is a thin layer on top. The Web GUI uses the same functions, and the extension could move to them later (e.g. HTTP through an SSH tunnel) without changes in queue or service.

### Status view in the VS Code extension, not a Web GUI

The jobs, their progress and the output of their commands are shown in the VS Code extension (Jobs view), not in a Web GUI.

* The developer already works there. The extension has the SSH connection, the build output, the build history and the Problems view
* No web server, no login, no TLS, no FastAPI on the IBM i: the same reasons as for CLI over SSH
* Fits one service per user. A central Web GUI couldn't read the users' `~/.obi-service`
* `module/jobs.py` returns plain data, so a Web GUI can still be added later, e.g. for people without VS Code or for a view of the whole team

### One service per user

* Each user has their own service. It runs under the user's profile, so a build runs exactly as with `run` today: same authorities, same object owner, same environment.
* The service can't do anything the user can't do. No profile switching, no special authorities.
* Directory: `~/.obi-service` (environment variable `OBI_SERVICE_DIR` to change it). Mode `0700`, owned by the user. The service and all actions refuse to work otherwise.
* Different from i-Releaser, which is one central application.

### How it works

```
client (SSH)                        processing service (~/.obi-service)

main.py -a submit
  1. checks project and build list
  2. adds a job to the queue
  3. starts the service, if needed
  4. wakes it up        ---------->  5. takes the job from the queue
                                     6. starts `main.py -a run --job <id>`
                                        in its own session
main.py -a watch --job <id>
  streams the events   <----------  7. the job writes an event for each change
  until the job ends                    and its heartbeat into the queue
```

* Queue: SQLite (`~/.obi-service/jobs.sqlite`, Python standard library), like i-Releaser. Default journal mode (no WAL), because of the IFS.
* One instance per user: lock file with `fcntl.lockf`. **The lock tells whether the service is running**, not the socket.
* Wake-up: Unix datagram socket `~/.obi-service/service.sock`, like i-Releaser. Its content is ignored: a message only makes the service look into the queue. If its path is too long (about 100 characters), the service runs without it and looks every `poll-interval` seconds.
* `submit` adds the job first, then looks at the lock. An ending service (idle) releases the lock first, then looks into the queue once more and keeps running if it finds a job. So either the service finds the job, or `submit` finds no service and starts a new one. A new service waits up to 10 seconds for the lock.
* The service starts each job as its own process: `main.py -a run -p <project> -c <dir> --job <id>`, working directory = project, `start_new_session=True`, output into `~/.obi-service/jobs/<id>/output.log`. So the job is the same `run` as today, plus events and heartbeat. `--job` is only used by the service.
* The job process checks that the job is `running`, is for this build list and isn't run by another process. It sets its own final status. A heartbeat thread updates the job (and its progress) every `heartbeat-interval` seconds.
* A job is `failed` if its process ended without setting its final status, or if the heartbeat is older than `heartbeat-timeout` (e.g. after a restart of the system, or the pid is used by another process meanwhile). A job process that sees that its job isn't `running` anymore stops its build.
* If a job process of this service ended without final status (e.g. killed), the service kills the rest of its process group (the commands) before it reaps the process. Until then, the id of the process group can't be used by another process. For jobs of an earlier service, this isn't safe, so their commands are left.
* Jobs run with the environment of the service, which is the environment of the command that started it. With the extension, that's the same environment as for `run` today.
* The service keeps no database connection open between its cycles and has only one thread.

### Job

| Field | Content |
|---|---|
| `id` | Number, unique per user |
| `project` | Absolute path of the project folder |
| `compile_list` | Absolute path of the build list |
| `status` | `queued`, `running`, `finished`, `failed`, `cancelled` |
| `build_status` | `success` or `failed`, only if `finished` |
| `error` | Why the job `failed` (OBI error, process died, ...) |
| `progress` | Last progress, see [Events](#events) |
| `queued`, `started`, `ended` | Timestamps |
| `pid`, `heartbeat`, `cancel_requested` | Process (= process group), last sign of life, time of the cancel |

`status` tells whether OBI could do its job, `build_status` whether the build was successful. Same as `status.json` and the build list today: a failed build is still `finished`.
`build_status` is `success` if every source of the build list is ignored, built successfully, or has only successful commands.

A build list (`compile_list`) can only have one job that is `queued` or `running`.

### Events

The job writes them into `~/.obi-service/jobs/<id>/events.jsonl` (one JSON object per line, append only). `run_cmds` gets an optional callback for it. It's called under the existing write lock, so parallel builds don't mix up the order.

```json
{"seq": 7, "time": "2026-11-04T10:15:02.345678", "type": "cmd_finished", "level": 1,
 "source": "mylib/qrpglesrc/order.rpgle.pgm", "cmd_index": 0, "status": "success",
 "exit-code": 0, "stdout": "...", "stderr": "", "joblog": "...",
 "progress": {"sources": 12, "sources_done": 3, "sources_failed": 0, "cmds": 30, "cmds_done": 8}}
```

| Type | When | Content |
|---|---|---|
| `queued` | `submit` | Position in the queue |
| `started` | Job process started | `progress` with the totals |
| `level_started` | Before a level | `level`, number of sources |
| `source_started` | Before the first command of a source | `level`, `source` |
| `cmd_started` | Before a command | `level`, `source`, `cmd_index`, `cmd` |
| `cmd_finished` | After a command | as above, with `status`, `exit-code`, `stdout`, `stderr`, `joblog`, `progress` |
| `source_finished` | After the last command of a source, or after its failure | `level`, `source`, `status`, `hash`, `progress` |
| `ended` | Always the last event | `status`, `build_status`, `error`, `progress` |

* `seq` starts at 1 and has no gaps. With `--since <seq>` the client gets everything after it.
* `progress` only counts what this job builds: sources and commands that are not ignored and were not built successfully before.
* The event file and the build list are written by the same process, after every command. The build list stays the complete result, the events are the changes.

### Command line

```sh
main.py -a submit -p <project> [-c <dir>]              # queue the build, start the service if needed
main.py -a watch  -p <project> -j <id> [--since <seq>] # stream the events until the job ends
main.py -a jobs   -p <project>                         # jobs of this project
main.py -a cancel -p <project> -j <id>                 # remove from the queue, or stop

service.py start | stop | restart | status             # optional: submit starts the service by itself
```

* Output on `stdout`: one JSON object per line, ASCII only. `submit` and `cancel` also write `status.json` as usual, with the job.
* `watch` and `jobs` don't write `status.json`: they run while a job writes it. An error is on `stdout`, exit code 1.
* `jobs`: the last 50 jobs of the project.
* `-j` has to be a job of the project `-p`.
* `cancel` of a running job: sets `cancel_requested` and sends `SIGTERM` to the process group of the job, only if its heartbeat is current. The running commands end and get the status `failed`. The job process only notes the signal, starts no further source or command (the source of a command that didn't start gets `failed`), writes the summary and ends as `cancelled`. The heartbeat thread also sees `cancel_requested`, in case the signal couldn't be sent. After `cancel-timeout` seconds without an end, the service sends `SIGKILL`.
* `service.py stop` only stops the service. Running jobs continue, queued jobs wait for the next start.
* `OBI_BACKEND_VERSION` is increased (new actions).

### Settings

Optional file `~/.obi-service/settings.toml`. These are settings of the user, not of a project.

| Key | Default | Description |
|---|---|---|
| `max-parallel-jobs` | `2` | Jobs that run at the same time. Different build lists only |
| `idle-timeout` | `1800` | Seconds without queued or running jobs until the service ends. `0`: never |
| `poll-interval` | `5` | Seconds between two looks into the queue without a wake-up |
| `heartbeat-interval` | `10` | Seconds between two signs of life of a job |
| `heartbeat-timeout` | `60` | Seconds without a sign of life until a job counts as dead |
| `cancel-timeout` | `30` | Seconds after `cancel` until the job is killed |
| `keep-jobs-days` | `7` | Ended jobs and their files are deleted after this time. `0`: never |

Invalid values fall back to the default, with a warning in the log.

### Security

* No network port. The socket only wakes up, its content is ignored.
* Directory `0700`, database, lock and socket `0600`. Owner and mode are checked before each access to the queue.
* Jobs run under the profile of the user. The commands come from the build list of the project, the same as with `run` today.
* `submit` only takes the project folder and the build list folder. Both are resolved to absolute paths and checked (folder exists, `.obi` exists, build list exists).
* Before a signal is sent to a job, its heartbeat is checked, so a reused pid is never hit.
* No new package: `sqlite3`, `socket`, `subprocess`, `fcntl` are in the standard library.

### Code

| File | Content |
|---|---|
| `service.py` | Start, stop, restart, status of the service |
| `module/service_config.py` | Directory, its check, settings |
| `module/job_queue.py` | Jobs in SQLite: add, claim, heartbeat, cancel request, end (with event `ended`), list, clean up |
| `module/job_events.py` | Event file: write, read after `seq` |
| `module/jobs.py` | For clients (CLI now, Web GUI later): submit, list, follow, cancel |
| `module/job_run.py` | The job process: checks, heartbeat, events, progress, cancel, final status |
| `module/processing_service.py` | The service: lock, wake-up, start jobs, look after their processes, idle end |
| `main.py` | Actions `submit`, `watch`, `jobs`, `cancel`, and `run --job` |
| `module/run_cmds.py` | Optional event callback and cancel |

Tests in `obi-unit-tests`: `test_service_config`, `test_job_events`, `test_job_queue`, `test_job_run`, `test_processing_service`, events and cancel in `test_run_cmds`, and the whole flow with a real service in `test_main` (`TestProcessingService`).


## Open questions

1. Should `create` on the IBM i also run as a job? It can take long for big projects
2. `jobs --all` (the jobs of all projects of the user), if the Jobs view of the extension should show them
