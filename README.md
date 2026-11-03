# ![logo](docs/img/Open%20Source%20Logo%20smaller.png) Object Builder for i (OBI)

OBI builds IBM i objects from sources in the IFS (or on your PC).
It finds the sources that changed since the last build, adds every object that depends on them,
puts everything in the right order and runs the build commands in PASE on IBM i.

* **Only what changed**: sources are compared by hash with the last successful build
* **Dependencies**: dependent objects are rebuilt too, in the right order (levels)
* **Configurable commands**: steps per source type, per source, or by rules ([extended source processing](docs/extended-source-processing.md))
* **Parallel builds**: sources that don't depend on each other can be built at the same time
* **Results**: status, spool output, joblog and errors of every command, plus a summary document

OBI is the backend. You usually use it through an IDE:

| Client | How |
|---|---|
| **VS Code** | The [OBI extension](https://marketplace.visualstudio.com/items?itemName=andreas-prouza.obi) does everything for you. Only the build itself runs this backend on IBM i. User documentation: [obi-extension](https://github.com/andreas-prouza/obi-extension) |
| **RDi, Eclipse, Notepad++, ...** | Call OBI from scripts. See [ibm-i-build-obi](https://github.com/andreas-prouza/ibm-i-build-obi) for an example project |
| **Command line** | See [Command line](docs/cli.md) |


## Requirements

* Python 3.12 or higher
* On IBM i: the open source tools (`yum`) with `bash` and Python
* We recommend the [SSH setup](https://github.com/andreas-prouza/obi-extension/blob/main/asserts/docs/ssh.md) for your user profile


## Installation

### On IBM i

Open an SSH session (or QSH) and make sure the open source tools are in your `PATH`:

```sh
export PATH="/QOpenSys/pkgs/bin:$PATH"
git clone https://github.com/andreas-prouza/obi.git
cd obi
./setup3.13.sh
```

Use the setup script that matches your Python version: `setup3.12.sh`, `setup3.13.sh` or `setup3.14.sh`.
`setup.sh` uses the command `python`.

The script creates a virtual environment in `venv`, updates `pip` and installs the packages from `requirements.txt`.
Nothing else is needed.

### On your PC (optional)

OBI can also create the build list on your PC, which is faster than on IBM i. The build itself always runs on IBM i.

* Linux, macOS: same as above
* Windows: `setup.bat`


## Quick start

Run OBI in the folder of your project. The project needs a `.obi` folder with its configuration (the VS Code extension creates it with *Initialize*).

```sh
cd /home/me/my-project
~/obi/venv/bin/python -X utf8 ~/obi/main.py -a create -p .   # Create the build list
~/obi/venv/bin/python -X utf8 ~/obi/main.py -a run -p .      # Build it
```

The results are in `.obi/build-output`. Open `compiled-object-list.md` for a summary.


## Documentation

| Topic | Content |
|---|---|
| [Command line](docs/cli.md) | Actions, arguments, status and exit codes |
| [How a build works](docs/build-process.md) | Change detection, dependencies, levels, parallel builds, errors |
| [Configuration](docs/configuration.md) | Files, settings, steps, variables |
| [Extended source processing](docs/extended-source-processing.md) | Rules that select the build steps for groups of sources |
| [Files](docs/files.md) | Format of the build list and of all other files OBI writes |
| [Development](docs/development.md) | Code structure, tests, guidelines |
| [Changelog](CHANGELOG.md) | Changes per version |


## FAQ

### Python not found

* Python is not installed
* Your Python command needs a version number, e.g. `python3.13`. Use the matching setup script
* The `PATH` is not set: `export PATH="/QOpenSys/pkgs/bin:$PATH"`

### The build failed, but the status is `ok`

`status.json` tells whether OBI itself worked. Whether a source was built is in the build list: check its `status`. See [Status and exit codes](docs/cli.md#status-and-exit-codes).

### Every source is built again

OBI only knows what was built from `.obi/etc/object-builds.json`. The VS Code extension updates it after each build.
Without the extension, see [Change detection](docs/build-process.md#1-change-detection).


## License

[GNU Affero General Public License v3.0](LICENSE)
