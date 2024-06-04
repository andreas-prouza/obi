import logging
import pathlib
import csv


from module import properties
from etc import constants
from module import toml_tools, files


default_app_config = properties.get_config(constants.CONFIG_TOML)


def add_build_cmds(target_tree, app_config=default_app_config):

  object_list = []

  for level, target_list in target_tree.items():
    for i in range(len(target_list)):
      object_list.append(get_object_list(target_list[i], app_config))
      target_list[i] = {target_list[i]: get_source_build_cmds(target_list[i], app_config)}

  object_list = "\n".join(list(set(object_list)))
  files.writeText(object_list, app_config['general']['deployment-object-list'])



def get_object_list(source, app_config=default_app_config):

  variable_dict = properties.get_source_properties(app_config, source)
  logging.debug(variable_dict)

  # Add list obj objects for deployment tool
  deploy_obj_list = f"prod_obj|{source}|{variable_dict['TARGET_LIB']}/{variable_dict['OBJ_NAME']}"
  
  return deploy_obj_list




def get_source_build_cmds(source, app_config=default_app_config):

  cmds = []

  src_suffixes = pathlib.Path(source).suffixes
  file_extensions = "".join(src_suffixes[-2:]).removeprefix('.')
  logging.debug(f"{file_extensions=}")

  steps = app_config['global']['steps'].get(file_extensions, [])

  # All properties for this source
  variable_dict = properties.get_source_properties(app_config, source)
  logging.debug(variable_dict)

  # Loop all steps of the source extension
  for step in steps:
    
    r=csv.reader([step], quotechar='"', delimiter='.')
    step_list = next(r)
    cmd = toml_tools.get_table_element(app_config, step_list)
    
    if cmd is None or cmd == '':
      continue

    for k, v in variable_dict.items():
      if not isinstance(v, str) and not isinstance(v, int):
        continue
      cmd = cmd.replace(f"$({k})", str(v))

    dspjoblog_cmd = app_config['global']['cmds'].get('dspjoblog', None)
    if dspjoblog_cmd is not None:
      joblog_sep = app_config['global']['cmds'].get('joblog-separator', "")
      cmd += dspjoblog_cmd.replace("$(joblog-separator)", joblog_sep)

    cmds.append({"cmd": cmd, "status": "new"})

  logging.debug(f"Added {len(cmds)} cmds for {source}")

  return cmds