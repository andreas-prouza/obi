import logging, os
from datetime import datetime

from . import obi_constants
from . import properties
from . import dependency
from . import build_cmds
from . import files
from . import run_cmds



def add_source_to_compile_list(source: str, compile_list_file: str, app_config: dict) -> dict:
  """Add a source to an existing compile list

  The source and all its (transitive) dependents are added, if they are not in the list yet.
  Sources that were already built successfully get reset, if they are affected by the new source.
  Levels (build order) are recalculated for the whole list.

  Everything is calculated in memory first, so a failure (e.g. in ESP) leaves the compile list untouched.

  Args:
      source (str): Source (relative to source dir) to add
      compile_list_file (str): Path of the existing compile list
      app_config (dict): Application config

  Returns:
      dict: {'compile_list': ..., 'added': [...], 'reset': [...], 'dependents': [...]}
  """

  general_config = app_config['general']
  source_dir = os.path.join(general_config['local-base-dir'], general_config['source-dir'])
  object_types = general_config['supported-object-types']

  # Check input
  if source is None or source.strip() == '':
    raise Exception("Parameter --source is missing")
  if not source.endswith(tuple(object_types)):
    raise Exception(f"Source '{source}' has no supported object type: {object_types}")
  if not os.path.isfile(os.path.join(source_dir, source)):
    raise Exception(f"Source '{source}' doesn't exist in '{source_dir}'")
  if not os.path.isfile(compile_list_file):
    raise Exception(f"Compile list '{compile_list_file}' doesn't exist. Create it first")

  dependency_dict = properties.get_json(general_config['dependency-list'])
  compile_list = files.getJson(compile_list_file)

  merge_result = merge_source(compile_list, source, dependency_dict, app_config)
  compile_list = merge_result['compile_list']

  changed_sources_list, dependend_objects_list = get_result_lists(source, merge_result['dependents'], app_config, source_dir)

  # Write files
  build_cmds.write_object_list(compile_list['compiles'], app_config)
  files.writeJson(changed_sources_list, obi_constants.OBIConstants.get("CHANGED_OBJECT_LIST"))
  files.writeJson(dependend_objects_list, obi_constants.OBIConstants.get("DEPENDEND_OBJECT_LIST"))
  files.writeJson(compile_list, compile_list_file)

  logging.info(f"Added: {merge_result['added']}")
  logging.info(f"Reset: {merge_result['reset']}")

  return merge_result



def merge_source(compile_list: dict, source: str, dependency_dict: dict, app_config: dict) -> dict:
  """Merge a source and its dependents into the compile list (in memory)

  Args:
      compile_list (dict): Existing compile list. Will be modified
      source (str): Source to add
      dependency_dict (dict): All dependencies of all sources
      app_config (dict): Application config

  Returns:
      dict: {'compile_list': ..., 'added': [...], 'reset': [...], 'dependents': [...]}
  """

  copy_related = app_config.get('global', {}).get('settings', {}).get('general', {}).get('ALWAYS_TRANSFER_RELATED_COPYBOOKS', False)

  # Existing entries in list order (level, then position)
  existing = []           # [(level, entry)]
  existing_by_source = {}
  for level_item in sorted(compile_list['compiles'], key=lambda d: d['level']):
    for entry in level_item['sources']:
      existing.append((level_item['level'], entry))
      existing_by_source[entry['source']] = entry

  dependents = sorted(dependency.get_targets_only_depended_objects(dependency_dict, [source]))
  logging.debug(f"{dependents=}")

  added = []
  reset = []
  new_entries = []

  # The requested source; its cmds get always generated (ESP or config may have changed)
  entry = existing_by_source.get(source)
  if entry is None:
    entry = {'source': source}
    new_entries.append(entry)
    added.append(source)
  else:
    reset.append(source)
  build_cmds.set_source_build_cmds(entry, app_config)
  reset_entry(entry)

  # Sources depending on the requested source
  new_dependents = []
  for dependent in dependents:
    entry = existing_by_source.get(dependent)
    if entry is None:
      entry = {'source': dependent}
      build_cmds.set_source_build_cmds(entry, app_config)
      new_entries.append(entry)
      new_dependents.append(dependent)
      added.append(dependent)
    elif is_success(entry):
      reset_entry(entry)
      reset.append(dependent)

  # Sources with a level >= 1. Level 0 are copybooks; they only get a real level if they are the source or a dependent
  leveled = {source, *dependents}
  leveled.update(entry['source'] for level, entry in existing if level > 0)
  leveled.update(entry['source'] for entry in new_entries)

  # Related copybooks
  if copy_related:
    copy_sources = dependency.get_copy_sources(dependency_dict, [source] + new_dependents, set())
    logging.info(f"Found copy sources: {copy_sources}")
    for copy_source in sorted(copy_sources):
      if copy_source in existing_by_source or copy_source in leveled:
        continue
      entry = {'source': copy_source}
      build_cmds.set_source_build_cmds(entry, app_config)
      new_entries.append(entry)
      added.append(copy_source)

  # fixed level 0 for copybooks; None = calculated
  entries = [(None if entry['source'] in leveled else 0, entry) for entry in [e for _, e in existing] + new_entries]

  compile_list['compiles'] = rebuild_levels(entries, calc_levels(dependency_dict, leveled))
  compile_list['timestamp'] = str(datetime.now())

  return {'compile_list': compile_list, 'added': added, 'reset': reset, 'dependents': dependents}



def is_success(entry: dict) -> bool:

  if entry.get('status') == 'success':
    return True

  return len(entry.get('cmds', [])) > 0 and run_cmds.all_cmds_succeeded(entry['cmds'])



def reset_entry(entry: dict) -> dict:
  """Reset a source entry, so it gets built again. Other keys (ignore, ...) are kept"""

  for cmd_item in entry.get('cmds', []):
    cmd_item['status'] = 'new'

  entry.pop('status', None)
  entry.pop('hash', None)

  return entry



def calc_levels(dependency_dict: dict, sources) -> dict:
  """Calculate the build level of each source

  A source gets level 1 + the highest level of its dependencies which are in the list, too.
  Same result as get_targets_by_level + remove_duplicities

  Returns:
      dict: {source: level}
  """

  members = set(sources)
  levels = {}
  visiting = set()

  def get_level(src):
    if src in levels:
      return levels[src]

    visiting.add(src)
    level = 1
    for dep in dependency_dict.get(src, []):
      if dep == src or dep not in members:
        continue
      if dep in visiting:
        logging.warning(f"Circular dependency: {src} <-> {dep}")
        continue
      level = max(level, get_level(dep) + 1)
    visiting.discard(src)

    levels[src] = level
    return level

  for src in members:
    get_level(src)

  return levels



def rebuild_levels(entries: list, levels: dict) -> list:
  """Group entries by level

  Args:
      entries (list): [(fixed_level, entry)]; fixed_level=None means the level is taken from `levels`
      levels (dict): {source: level}

  Returns:
      list: [{'level': 0, 'sources': [...]}, ...] sorted by level; order in a level is kept, but *.file are first
  """

  level_dict = {}
  for fixed_level, entry in entries:
    level = fixed_level if fixed_level is not None else levels[entry['source']]
    level_dict.setdefault(level, []).append(entry)

  return [
    {'level': level, 'sources': sorted(level_dict[level], key=lambda e: e['source'].split('.')[-1] != 'file')}
    for level in sorted(level_dict)
  ]



def get_result_lists(source: str, dependents: list, app_config: dict, source_dir: str) -> tuple:
  """Update the lists used by the result document (new/changed sources; dependend objects)

  Returns:
      tuple: (changed sources list, dependend objects list)
  """

  general_config = app_config['general']

  changed_file = obi_constants.OBIConstants.get("CHANGED_OBJECT_LIST")
  dependend_file = obi_constants.OBIConstants.get("DEPENDEND_OBJECT_LIST")

  changed_sources_list = {'new-objects': [], 'changed-sources': []}
  if os.path.isfile(changed_file):
    changed_sources_list.update(files.getJson(changed_file))

  dependend_objects_list = []
  if os.path.isfile(dependend_file):
    dependend_objects_list = files.getJson(dependend_file)

  # Same check as in `create --source`
  source_changes = files.get_changed_sources(source_dir, general_config['compiled-object-list'], general_config['supported-object-types'], {source: ''})
  known_sources = changed_sources_list['new-objects'] + changed_sources_list['changed-sources']
  for key, sources in source_changes.items():
    changed_sources_list[key] += [src for src in sources if src not in known_sources]

  known_sources = changed_sources_list['new-objects'] + changed_sources_list['changed-sources']
  dependend_objects_list = [src for src in dict.fromkeys(dependend_objects_list + dependents) if src not in known_sources]

  return changed_sources_list, dependend_objects_list
