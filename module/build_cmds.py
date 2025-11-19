import logging
import pathlib
import csv


from module import properties
from module import obi_constants
from module import toml_tools, files, app_config_tools
from copy import deepcopy
import re

default_app_config = properties.get_app_properties()



def add_build_cmds(target_tree, app_config=default_app_config):

  object_list = []

  for target_item in target_tree:
    for source_item in target_item['sources']:
      object_list.append(get_object_list(source_item['source'], app_config))
      source_item['cmds'] = get_source_build_cmds(source_item['source'], app_config)

  object_list = "\n".join(list(set(object_list)))
  logging.debug(f"Write object list {len(object_list)=} to {app_config['general']['deployment-object-list']}")
  files.writeText(object_list, app_config['general']['deployment-object-list'], write_empty_file=True)




def get_object_list(source, app_config=default_app_config):
  '''
  This is only needed by the deployment tool
  '''

  variable_dict = properties.get_source_properties(app_config, source)
  logging.debug(f"{source=}")
  logging.debug(f"{variable_dict=}")

  # Add list obj objects for deployment tool
  prod_lib = pathlib.Path(source).parts[0]
  #type=*pgm, attr=rpgle
  obj_type=source.split('.')[-1]
  obj_attr=source.split('.')[-2]
  deploy_obj_list = f"prod_obj|{prod_lib}|{variable_dict['TARGET_LIB']}|{variable_dict['OBJ_NAME']}|{obj_type}|{obj_attr}|{source}"
  
  return deploy_obj_list




def remove_unresolved_cmd_parameters(cmd: str) -> str:

  cmd = cmd.replace('ACTGRP($(ACTGRP))', '')
  cmd = cmd.replace('ACTGRP()', '')
  cmd = cmd.replace('BNDDIR($(INCLUDE_BNDDIR))', '')
  cmd = cmd.replace('BNDDIR()', '')
  cmd = cmd.replace('TGTRLS($(TGTRLS))', '')
  cmd = cmd.replace('TGTRLS()', '')
  cmd = cmd.replace('STGMDL($(STGMDL))', '')
  cmd = cmd.replace('STGMDL()', '')
  cmd = cmd.replace('TGTCCSID($(TGTCCSID))', '')
  cmd = cmd.replace('TGTCCSID()', '')
  cmd = cmd.replace('DBGVIEW($(DBGVIEW))', '')
  cmd = cmd.replace('DBGVIEW()', '')
  cmd = cmd.replace('INCDIR($(INCDIR_SQLRPGLE))', '')
  cmd = cmd.replace('INCDIR()', '')
  cmd = cmd.replace('INCDIR($(INCDIR_RPGLE))', '')
  cmd = cmd.replace('INCDIR()', '')

  return cmd



def get_source_build_cmds(source, app_config=default_app_config):

  logging.debug(f"Check source cmds for {source}")
  cmds = []
  sources_config=properties.get_config(obi_constants.OBIConstants.get("SOURCE_CONFIG_TOML"))
  source_config={}
  if source in sources_config:
    source_config = sources_config[source]


  src_suffixes = pathlib.Path(source).suffixes
  file_extensions = "".join(src_suffixes[-2:]).removeprefix('.')
  logging.debug(f"{file_extensions=}")
  logging.debug(f"{source_config=}")

  steps = app_config_tools.get_steps(source, app_config)
  #steps = app_config['global']['steps'].get(file_extensions, [])

  # Override steps by individual source config
  if 'steps' in source_config.keys() and len(source_config['steps']) > 0:
    steps = source_config['steps']
    logging.debug(f"{steps=}")

  # All properties for this source
  variable_dict = properties.get_source_properties(app_config, source)
  var_dict_tmp = {}
  logging.debug(f"{variable_dict=}")

  # Loop all steps of the source extension
  for step in steps:
    
    logging.debug(f"{step=}")

    if isinstance(step, str):
      cmd = get_cmd_from_step(step, source, variable_dict, app_config, source_config)
      logging.debug(f"1 {cmd=}")
      
    if isinstance(step, dict):
      var_dict_tmp = deepcopy(variable_dict)
      logging.debug(f"{var_dict_tmp=}")
      var_dict_tmp.update(step.get('properties', {}))
      
      cmd = step.get('cmd', None)
      if not cmd:
        cmd = get_cmd_from_step(step.get('step', None), source, var_dict_tmp, app_config, source_config)
        logging.debug(f"2 {cmd=}")
      
    cmd = replace_cmd_parameters(cmd, {**variable_dict, **var_dict_tmp})
    cmds.append({"cmd": cmd, "status": "new"})

  logging.debug(f"Added {len(cmds)} cmds for {source}")

  return cmds



def get_cmd_from_step(step: str, source: str, variable_dict: {}, app_config, source_config) -> str:
  
    logging.debug(f"csv.reader {step=}")
    r=csv.reader([step], quotechar='"', delimiter='.')  # step: e.g. global."compile-cmds"."sqlrpgle.srvpgm"
    step_list = next(r)                                 # --> ['global', 'compile-cmds', 'sqlrpgle.mod']
    #logging.debug(f"{step_list=}")

    #cmd = toml_tools.get_table_element(app_config, step_list)
    logging.debug(f"1: {step_list=}")
    cmd = toml_tools.get_table_element({**app_config, **source_config}, step_list)
    logging.debug(f"2: {cmd=}")
    
    # Find all words starting and ending with %
    percent_words = re.findall(r'%[\w\.]+%', cmd)
    logging.debug(f"Words starting and ending with %: {percent_words}")
    
    for word in percent_words:
        key = word.strip('%')
        r2=csv.reader([key], quotechar='"', delimiter='.')  # step: e.g. global."compile-cmds"."sqlrpgle.srvpgm"
        step_list2 = next(r2)                                 # --> ['global', 'compile-cmds', 'sqlrpgle.mod']
        logging.debug(f"Replace word {word} with key {key}")
        subcmd = toml_tools.get_table_element({**app_config, **source_config}, step_list2)
    
        if subcmd is not None:
          cmd = cmd.replace(word, subcmd)
          logging.debug(f"Replaced {word} with {subcmd} in cmd")

    variable_dict['SET_LIBL'] = properties.get_set_libl_cmd(app_config, variable_dict.get('LIBL', []), variable_dict['TARGET_LIB'])
    
    if cmd is None or cmd == '':
      raise Exception(f"Step '{step}' not found in '{obi_constants.OBIConstants.get("CONFIG_TOML")}' or '{obi_constants.OBIConstants.get("CONFIG_USER_TOML")}'")

    dspjoblog_cmd = app_config['global']['cmds'].get('dspjoblog', None)
    if dspjoblog_cmd is not None:
      joblog_sep = app_config['global']['cmds'].get('joblog-separator', "")
      cmd += dspjoblog_cmd.replace("$(joblog-separator)", joblog_sep)

    return cmd




def replace_cmd_parameters(cmd: str, variable_dict: {}) -> str:
  '''
  Replace all $(...) parameters in the cmd with the values from the variable_dict
  '''
  
  for k, v in variable_dict.items():
    if not isinstance(v, str) and not isinstance(v, int):
      continue
    cmd = cmd.replace(f"$({k})", str(v))

  cmd = remove_unresolved_cmd_parameters(cmd)

  return cmd



def order_builds(target_tree):
  '''
  Order the build commands by the order of the source files
  '''
  ordered_target_tree = {'timestamp': target_tree['timestamp'], 'compiles': []}
  
  for compiles in target_tree['compiles']:
    
    level_list = {'level': compiles['level'], 'sources': []}
    
    for source_entry in compiles['sources']:
      
      if source_entry['source'].split('.')[-1] == 'file':
        level_list['sources'].insert(0, source_entry)
        continue
      
      level_list['sources'].append(source_entry)
      
    ordered_target_tree['compiles'].append(level_list)
  
  return ordered_target_tree