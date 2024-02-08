import pathlib
import csv


from module import properties
from etc import constants
from module import toml_tools


default_app_config = properties.get_config(constants.CONFIG_TOML)


def add_build_cmds(target_tree, app_config=default_app_config):

  for level, target_list in target_tree.items():
    for i in range(len(target_list)):
      target_list[i] = {target_list[i]: get_source_build_cmds(target_list[i], app_config)}



def get_source_build_cmds(source, app_config=default_app_config):

  cmds = []

  src_suffixes = pathlib.Path(source).suffixes
  file_extensions = "".join(src_suffixes).removeprefix('.')

  steps = app_config['global']['steps'].get(file_extensions, [])

  variable_dict = properties.get_source_properties(app_config, source)

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

    cmds.append({"cmd": cmd, "status": "new"})

  return cmds