[← Back to feature specifications](README.md)

# Branch build

- **Status:** in progress
- **Type:** feature


## Current situation

All developers build into the same libraries (e.g. `#h_beobj`), whatever branch they are on. A build on one feature branch overwrites the objects of another, and the libraries don't show the state of the main branch.


## Requirements

- A build on a branch with a ticket number goes into libraries of that ticket: `lib-name`, e.g. `#$(ENV)_$(TICKET)` → `#be_337`
- ENV comes from the production library (`[branch-build.env]`), so several libraries of a tenant share one branch library
- A branch without a ticket number, the main branch, a detached HEAD or a project without git builds into the main libraries
- The extended source processing and its scripts keep working unchanged: they see the main libraries
- The branch libraries go on top of the library list, the target library topmost
- `run` creates missing branch libraries; the command is configurable
- Optional: without a `[branch-build]` section nothing changes, and git is never called


## Acceptance criteria

- Without `[branch-build]`, `create` writes the same build list and object list as before (checked with two packages of a real project)
- On a branch with a ticket, no command builds into a main library. A library without ENV stops `create` with an error that names the source
- `add_source` refuses a build list that was created for another ticket
- A library that can't be created stops `run` before the first source
- Unit tests: `obi-unit-tests/tests/test_branch_build.py`


## Non-goals

- Deleting branch libraries (planned: action `branch_libs`, called by the VS Code extension)
- Copying data into branch libraries: tables and physical files are created empty
- Deployment rules: they belong to the client and the deployment tool


## Decisions

- Activation by the section itself; `enabled = false` turns it off. An incomplete section is an error, never a silent fallback to the main libraries
- The branch library is applied after the extended source processing, to the properties of each command. `TARGET_LIB_MAIN` keeps the library of a main build; `TARGET_LIB_ORIG` is unchanged
- Only commands that use `$(TARGET_LIB)` (also indirectly) need a branch library. `no-lib-steps` excludes steps such as messages, so they create no library
- The build list keeps the context (`build_context`): `run` reads the libraries from there, `add_source` checks the ticket
- Backend version 6
