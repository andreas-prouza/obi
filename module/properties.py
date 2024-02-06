import toml
import os
import pathlib

from module import toml_tools


def get_config(config):
  with open(config, 'r') as f:
    return toml.load(f)



def write_config(config, content):
  with open(config, 'w') as f:
    toml.dump(content, f)



def get_source_properties(config, source):

  src_suffixes = pathlib.Path(source).suffixes
  file_extensions = "".join(src_suffixes).removeprefix('.')

  global_settings = toml_tools.get_table_element(config, ['global', 'settings', 'general'])
  type_settings = toml_tools.get_table_element(config, ['global', 'settings', file_extensions])

  global_settings.update(type_settings)
  global_settings['SOURCE_FILE_NAME'] = os.path.join(config['general']['remote-dir'], config['general']['source-dir'], source)
  global_settings['TARGET_LIB'] = get_target_lib(source, global_settings.get('TARGET_LIB'), global_settings.get('TARGET_LIB_MAPPING'))
  
  return global_settings



def get_target_lib(source, target_lib=None, lib_mapping=None):

  source_lib = source.split(os.sep)[0].lower()

  if target_lib is not None and target_lib.lower() == '*source':
    return source_lib

  if target_lib is not None:
    return target_lib.lower()

  for k, v in lib_mapping.items():
    k = k.lower()
    if k == source_lib:
      return v.lower()

  return source_lib

