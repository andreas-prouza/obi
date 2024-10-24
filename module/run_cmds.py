import logging
import subprocess
from datetime import datetime

from module import properties
from etc import constants
from module import toml_tools
from module import files


default_app_config = properties.get_app_properties()


def all_cmds_succeeded(cmds:[]) -> bool:
  for cmd_item in cmds:
    if 'status' not in cmd_item or cmd_item['status'] != 'success':
      return False
  return True



def run_build_object_list(target_tree, save_update_2_json_file=None, app_config=default_app_config):
  """Run commands for all source entries

  Args:
      target_tree (dict): List of all sources and the related commands
      save_update_2_json_file (str, optional): If given, every change will update the json file. Defaults to None.
      app_config (properties, optional): Application config file

  Raises:
      Exception: If a command fails an exception will be thrown
  """

  # Level 1-n
  for level_item in target_tree['compiles']:
    
    logging.info(f"Run {level_item['level']=}: {len(level_item['sources'])} entries")

    # Each entry in a level list
    for level_list_entry in level_item['sources']:

      src_name = level_list_entry['source']
      cmds = level_list_entry['cmds']
      
      logging.info(level_list_entry['source'])
      logging.info(cmds)

      # Skip this if object was successfully build
      if all_cmds_succeeded(level_list_entry['cmds']):
        continue

      level_list_entry['status'] = 'in process'

      # each source can have multiple commands
      for cmd_item in cmds:
        
        logging.debug(f"Execute ({cmd_item['status']}) {cmd_item['cmd']}")
        
        cmd_item['updated'] = datetime.now().isoformat()
        cmd_item['status'] = 'in process'
        target_tree['timestamp'] = str(datetime.now())
        files.writeJson(target_tree, save_update_2_json_file)

        result = run_pase_cmd(cmd_item['cmd'])

        joblog_sep = app_config['global']['cmds'].get('joblog-separator', None)
        if joblog_sep is not None and len(result['stdout'].split(joblog_sep)) > 0:
          result['joblog'] = result['stdout'].split(joblog_sep)[1]
          result['stdout'] = result['stdout'].split(joblog_sep)[0]

        cmd_item['updated'] = datetime.now().isoformat()
        cmd_item['status'] = 'failed'
        if result['exit-code'] == 0 and result['stderr'] == '':
          cmd_item['status'] = 'success'
        
        cmd_item.update(result)
        target_tree['timestamp'] = str(datetime.now())
        files.writeJson(target_tree, save_update_2_json_file)

        if result['exit-code'] != 0 or result['stderr'] != '':
          level_list_entry['status'] = 'failed'
          e = Exception(f"Error for '{src_name}': {result['stderr']}")
          logging.exception(e)
          raise e
    
      level_list_entry['status'] = 'success'
      level_list_entry['hash'] = files.get_file_hash(f"{app_config['general']['source-dir']}/{src_name}")
      files.writeJson(target_tree, save_update_2_json_file)
      files.update_compiles_object_list(src_name, app_config)




def run_pase_cmd(cmd, app_config=default_app_config):

  s=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=False, executable='/usr/bin/bash')

  encoding = app_config['general'].get('console-output-encoding', 'utf-8')
  stdout = str(s.stdout, encoding)
  stderr = str(s.stderr, encoding)

  # exit-code: 0 = OK
  return {"exit-code": s.returncode, "stdout": stdout, "stderr": stderr}

