import logging
import toml
import json
import os
import pathlib

from etc import constants
from module import toml_tools
from module import files
from module import dict_tools


config_content = {}




def get_json(config):

  if not os.path.exists(config):
    return {}

  if config in config_content.keys():
    return config_content[config]

  with open(config, 'r') as f:
    try:
      config_content[config] = json.load(f)
    except Exception as e:
      config_content[config] = {}
      logging.exception(e)

    return config_content[config]



def write_json(config, content):
  config_content[config] = content
  files.writeJson(content, config)





def get_config(config):

  if not os.path.exists(config):
    return {}

  if config in config_content.keys():
    return config_content[config]

  with open(config, 'r') as f:
    try:
      config_content[config] = toml.load(f)
    except Exception as e:
      config_content[config] = {}
      logging.exception(e)

    return config_content[config]



def write_config(config, content):
  config_content[config] = content
  files.writeToml(content, config)




def get_app_properties():
  app_project_config = get_config(constants.CONFIG_TOML)
  app_user_config = get_config(constants.CONFIG_USER_TOML)

  app_config = dict(dict_tools.dict_merge(app_project_config, app_user_config))

  return app_config



def get_source_properties(config, source):

  source_config=get_config(constants.SOURCE_CONFIG_TOML)
  src_suffixes = pathlib.Path(source).suffixes
  file_extensions = "".join(src_suffixes[-2:]).removeprefix('.')

  global_settings = toml_tools.get_table_element(config, ['global', 'settings', 'general'])
  type_settings = toml_tools.get_table_element(config, ['global', 'settings', 'language']).get(file_extensions, [])

  # Override source individual settings
  if source in source_config and 'settings' in source_config[source].keys():
    global_settings.update(source_config[source]['settings'])
    logging.debug(f"{source_config[source]['settings']=}")

  global_settings.update(type_settings)
  global_settings['SOURCE_FILE_NAME'] = os.path.join(config['general']['source-dir'], source).replace('\\', '/')
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

  if lib_mapping is not None:
    for k, v in lib_mapping.items():
      k = k.lower()
      if k == source_lib:
        return v.lower()

  return source_lib

