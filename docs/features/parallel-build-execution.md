# Parallel builds

- **Status:** in progress
- **Type:** improvement


## Current situation

* All commands of a source are executed in sequence
* The order is defined by `level`


## Requirements

1. Source builds should be processed in parallel
2. Add a new config attribute to set the max number of parallel processing
3. All commands within a source should be executed still in sequence


## Acceptance criteria

* With `max-parallel-builds = n`, at most n sources of a level are built at the same time
* Without the setting, the build works exactly as before (one source after the other)
* The commands of a source run one after the other
* A failure stops the build as before: no further source or level is started
* Writes of the build list don't overlap, and every command gets its own joblog


## Non-goals

* Running the commands of one source in parallel
* Detecting object locks between sources of the same level


## Decisions

* Parallelism is per `level`: sources within one level run concurrently, levels run in sequence because a level can depend on the previous one
* New config attribute `general.max-parallel-builds`. Default is 1 (sequential), also if the value is invalid. Parallel builds have to be switched on per project
* `general.max-threads` is not used for this: the extension already uses it (e.g. source hashing, default 20)
* Implemented with the stdlib `concurrent.futures.ThreadPoolExecutor` (no new dependency)
* After a failure no further source and no further level gets started. Sources already running are finished. With `max-parallel-builds = 1` this is the same behaviour as before
* The joblog of `dspjoblog` is written to a unique file per command, which gets removed after reading, so parallel commands don't overwrite each other's joblog
* All changes and writes of the shared compile list and writes of the compiled-object-list happen under one lock
* Documentation: [Parallel builds](../build-process.md#parallel-builds)
