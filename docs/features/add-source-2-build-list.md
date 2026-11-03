# Add a source to the build list

- **Status:** done
- **Type:** feature


## Current situation

* A build list can only be created as a whole (`create`), which deletes the previous one and its results
* To build one more source, the VS Code extension created a separate list for it and merged both itself


## Requirements

1. New action `add_source`, adding a source to an existing `compile-list.json`
2. Consider dependencies and build order
3. Sources with status `success` are reset if they are affected by the new source
4. Consider the extended source processing (ESP)
5. New argument `-c`, `--compile-list-dir`, considered by all actions using the build list


## Acceptance criteria

* The source and all sources depending on it are in the list, with the same levels `create` would give them
* Sources already in the list keep their results, except the reset ones
* An error (e.g. in an ESP rule) leaves all files unchanged
* `status.json` lists the added and the reset sources


## Non-goals

* Removing sources from a build list


## Decisions

* The requested source always gets new build commands and is reset, also if it was already in the list
* Dependent sources that were built successfully keep their commands and output; only the status is reset (all commands `new`, `status` and `hash` removed). Sources that are not `success` are not changed; they will be built anyway
* Levels are calculated again for the whole list: a source gets 1 + the highest level of the sources it depends on that are in the list. Existing sources move up if the new source is one of their dependencies
* Related copybooks (`ALWAYS_TRANSFER_RELATED_COPYBOOKS`) are added on level 0
* All other content of the build list is kept (e.g. `ignore`, `custom_data`)
* `-c` only changes the folder of the build list. The file name stays as configured, and the other output files keep their location
* Documentation: [Command line](../cli.md#add_source), [Adding a source](../build-process.md#adding-a-source)
