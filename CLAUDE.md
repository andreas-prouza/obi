# Project: OBI (Object Builder for i)

Generates and executes build commands for and on IBM i. This is the Python backend; the main client is the VS Code extension (`../obi-extension`).

- Guidelines and rules: [docs/architecture.md](docs/architecture.md)
- Documentation: [README.md](README.md) and [docs](docs/). Update it together with the code, and add user-visible changes to [CHANGELOG.md](CHANGELOG.md)
- Feature specifications: [docs/features](docs/features/README.md)
- Tests: separate repository `../obi-unit-tests`
  `OBI_DIR=. venv/bin/python -m unittest discover -s ../obi-unit-tests/tests -p "test_*.py"`
