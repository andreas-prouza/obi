[← Back to README](../README.md)

# Development

- [Code structure](#code-structure)
- [Running OBI locally](#running-obi-locally)
- [Tests](#tests)
- [Guidelines](#guidelines)
- [Features and changes](#features-and-changes)


## Code structure

| File | Content |
|---|---|
| `main.py` | Arguments, actions, status file |
| `module/files.py` | Source files, hashes, reading and writing files |
| `module/dependency.py` | Dependent objects and levels |
| `module/build_cmds.py` | Build commands of a source, object list |
| `module/app_config_tools.py` | Steps of a source, [extended source processing](extended-source-processing.md) |
| `module/properties.py` | Configuration files and variables |
| `module/compile_list.py` | `add_source`: merge into an existing build list |
| `module/run_cmds.py` | Running the build, parallel builds |
| `module/results.py` | Summary document |
| `module/obi_constants.py` | Access to the project's `constants.py`; `OBI_BACKEND_VERSION` |
| `module/toml_tools.py`, `module/dict_tools.py` | Helpers |
| `docs/summary-template.md` | Template of the summary document. Read by `results.py`, don't move it |

Increase `OBI_BACKEND_VERSION` in `module/obi_constants.py` when a client needs to know about a change (e.g. new arguments or file formats). The VS Code extension compares it with the version it needs.


## Running OBI locally

The build list can be created on Linux, macOS or Windows. The build itself needs IBM i (`cl`).

```sh
./setup.sh
venv/bin/python -X utf8 main.py -a create -p <project>
```


## Tests

The tests are in a separate repository: [obi-unit-tests](https://github.com/andreas-prouza/obi-unit-tests).
They need neither IBM i nor `cl`: every test runs in its own temporary project.

```sh
git clone https://github.com/andreas-prouza/obi-unit-tests.git
cd obi-unit-tests
OBI_DIR=../obi ../obi/venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

Add or change tests together with every change of OBI.


## Guidelines

See [architecture.md](architecture.md): security comes first, and new Python packages have to meet the criteria listed there.

Code style: 2 spaces indentation (`app_config_tools.py`: 4), `logging` with f-strings, errors as `Exception` with a clear message. `main.py` turns them into the [status file](cli.md#status-and-exit-codes).


## Features and changes

* Larger changes are described in [`docs/features`](features/README.md) before they are implemented.
* Every change that users notice goes into the [changelog](../CHANGELOG.md).
* Update this documentation together with the code.
