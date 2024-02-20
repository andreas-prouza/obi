import toml
import os
import pathlib

from module import toml_tools
from module import files


def get_config(config):

  if not os.path.exists(config):
    return {}

  with open(config, 'r') as f:
    return toml.load(f)



def write_config(config, content):
  files.writeToml(content, config)



def get_source_properties(config, source):

  src_suffixes = pathlib.Path(source).suffixes
  file_extensions = "".join(src_suffixes).removeprefix('.')

  global_settings = toml_tools.get_table_element(config, ['global', 'settings', 'general'])
  type_settings = toml_tools.get_table_element(config, ['global', 'settings']).get(file_extensions, [])

  global_settings.update(type_settings)
  global_settings['SOURCE_FILE_NAME'] = os.path.join(config['general']['remote-base-dir'], config['general']['source-dir'], source).replace('\\', '/')
  global_settings['TARGET_LIB'] = get_target_lib(source, global_settings.get('TARGET_LIB'), global_settings.get('TARGET_LIB_MAPPING'))
  global_settings['OBJ_NAME'] = pathlib.Path(pathlib.Path(source).stem).stem

  set_libl = ""
  for lib in global_settings.get('LIBL', []):
    lib = lib.replace("$(TARGET_LIB)", global_settings['TARGET_LIB'])
    if len(set_libl) > 0:
      set_libl += '; '
    set_libl += config['global']['cmds']['add-lible'].replace('$(LIB)', lib)
  global_settings['SET_LIBL'] = set_libl

  return global_settings



def get_target_lib(source, target_lib=None, lib_mapping=None):

  source_lib = source.split('/')[0].lower()

  if target_lib is not None and target_lib.lower() == '*source':
    return source_lib

  if target_lib is not None:
    return target_lib.lower()

  for k, v in lib_mapping.items():
    k = k.lower()
    if k == source_lib:
      return v.lower()

  return source_lib

