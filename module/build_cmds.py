import pathlib
import csv

from module import properties
from module import constants
from module import toml_tools


app_config = properties.get_config(constants.CONFIG_TOML)


def get_source_build_cmds(source):

  cmds = []

  src_suffixes = pathlib.Path(source).suffixes
  file_extensions = "".join(src_suffixes).removeprefix('.')

  steps = app_config['global']['steps'][file_extensions]

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

    cmds.append(cmd)

  return cmds