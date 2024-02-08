import logging
import subprocess
from datetime import datetime

from module import properties
from etc import constants
from module import toml_tools
from module import files


default_app_config = properties.get_config(constants.CONFIG_TOML)



def run_build_object_list(target_tree, save_update_2_json_file=None, app_config=default_app_config):
  """Run commands for all source entries

  Args:
      target_tree (dict): List of all sources and the related commands
      save_update_2_json_file (str, optional): If given, every change will update the json file. Defaults to None.

  Raises:
      Exception: If a command fails an exception will be thrown
  """

  # Level 1-n
  for level, level_list in target_tree.items():
    
    logging.info(f"Run {level=}: {len(level_list)} entries")

    # Each entry in a level list
    for level_list_entry in level_list:

      # Level list entry is a dict
      for src_name, cmds in level_list_entry.items():

        logging.info(src_name)
        logging.info(cmds)

        # each source can have multiple commands
        for cmd_item in cmds:
          
          logging.info(cmds)
          logging.debug(f"Execute ({cmd_item['status']}) {cmd_item['cmd']}")
          
          cmd_item['updated'] = datetime.now().isoformat()
          cmd_item['status'] = 'in process'
          files.writeJson(target_tree, save_update_2_json_file)

          result = run_pase_cmd(cmd_item['cmd'])

          cmd_item['updated'] = datetime.now().isoformat()
          cmd_item['status'] = 'failed'
          if result['exit-code'] == 0:
            cmd_item['status'] = 'success'
            update_compiles_object_list(src_name, app_config)
          
          cmd_item.update(result)

          files.writeJson(target_tree, save_update_2_json_file)

          if result['exit-code'] != 0:
            e = Exception(f"Error for '{src_name}': {cmd_item}")
            logging.exception(e)
            raise e




def run_pase_cmd(cmd, app_config=default_app_config):

  s=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=False, executable='/bin/bash')
  stdout = s.stdout
  stderr = s.stderr

  if app_config['general'].get('convert-output', False):
    stdout = stdout.decode(app_config['general'].get('convert-from', 'cp1252'))
    stderr = stderr.decode(app_config['general'].get('convert-to', 'utf-8'))

  # exit-code: 0 = OK
  return {"exit-code": s.returncode, "stdout": stdout, "stderr": stderr}



def update_compiles_object_list(source, app_config=default_app_config):

  compiled_object_list = properties.get_config(app_config['general']['compiled-object-list'])

  compiled_object_list[source] = datetime.now()
  properties.write_config(app_config['general']['compiled-object-list'], compiled_object_list)

