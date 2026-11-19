"""
Build packages: a named list of sources in .obi/build-packages/<name>.json, committed with the project.
The VS Code extension creates and edits them; `create --package <name>` builds all their sources.
See docs/features/build-packages.md
"""

import json
import os
import re

from module import obi_constants


# Same rules as the VS Code extension (src/shared/BuildPackage.ts, src/shared/ShellQuote.ts)
NAME_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}')
WINDOWS_RESERVED = re.compile(r'(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?', re.IGNORECASE)
SOURCE_PATTERN = re.compile(r'[A-Za-z0-9_$#@.\-/]+')



class BuildPackageError(Exception):
  pass



def is_valid_name(name: str) -> bool:
  """The name becomes a file name: no separators, so it can't leave the folder"""
  return NAME_PATTERN.fullmatch(name) is not None and WINDOWS_RESERVED.fullmatch(name) is None



def is_valid_source(source: str) -> bool:
  """Relative to the source directory, '/'-separated, without '..'"""
  return SOURCE_PATTERN.fullmatch(source) is not None and not source.startswith('/') and '..' not in source.split('/')



def package_file(name: str) -> str:
  if not is_valid_name(name):
    raise BuildPackageError(f"Invalid build package name '{name}'. Allowed: letters, digits, '.', '_', '-' (starting with a letter or digit, max. 100 characters)")
  return os.path.join(obi_constants.OBIConstants.get('BUILD_PACKAGE_DIR'), f'{name}.json')



def has_supported_type(source: str, object_types: list) -> bool:
  if not object_types:
    return True
  suffix = source.rsplit('.', 1)[1] if '.' in source else ''
  return suffix in object_types



def load_package(name: str, source_dir: str, object_types: list) -> dict:
  """
  Build package `name` as {'name', 'description' (if set), 'sources' (sorted, without duplicates)}.
  Raises BuildPackageError if the file is not a valid package, or a source doesn't exist or has an unsupported type.
  """

  file = package_file(name)

  try:
    with open(file, 'r', encoding='utf-8') as f:
      text = f.read()
  except FileNotFoundError:
    raise BuildPackageError(f"Build package '{name}' not found ({file})")

  try:
    data = json.loads(text) if text.strip() else {}
  except json.JSONDecodeError as e:
    raise BuildPackageError(f"{file}: {e}")

  if not isinstance(data, dict):
    raise BuildPackageError(f"{file}: a build package must be a JSON object")

  description = data.get('description')
  if description is not None and not isinstance(description, str):
    raise BuildPackageError(f'{file}: "description" must be a text')

  sources = data.get('sources', [])
  if not isinstance(sources, list) or any(not isinstance(source, str) for source in sources):
    raise BuildPackageError(f'{file}: "sources" must be a list of source names')

  invalid = [source for source in sources if not is_valid_source(source)]
  if invalid:
    raise BuildPackageError(f"{file}: invalid source names (relative to the source directory, '/'-separated): {', '.join(invalid)}")

  sources = sorted(set(sources))

  unsupported = [source for source in sources if not has_supported_type(source, object_types)]
  missing = [source for source in sources if source not in unsupported and not os.path.isfile(os.path.join(source_dir, source))]
  problems = []
  if missing:
    problems.append(f"missing: {', '.join(missing)}")
  if unsupported:
    problems.append(f"type not in supported-object-types: {', '.join(unsupported)}")
  if problems:
    raise BuildPackageError(f"Build package '{name}' contains sources that can't be built ({'; '.join(problems)})")

  package = {'name': name, 'sources': sources}
  if description:
    package['description'] = description
  return package



def package_info(package: dict) -> dict:
  """What the build list records about its package (`package` in compile-list.json)"""
  return {key: package[key] for key in ('name', 'description') if key in package}
