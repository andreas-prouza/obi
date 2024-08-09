import os
import pathlib
import logging
import subprocess
from datetime import datetime
from pathlib import PureWindowsPath

from module import properties
from etc import constants
from module import toml_tools
from module import files
from module import dependency


default_app_config = properties.get_config(constants.CONFIG_TOML)



def save_outputs_in_files(compile_list, app_config=default_app_config):
  """Save outputs to files
    stdout: {source}.splf
    joblog: {source}.joblog
    stderr: {source}.error

  Args:
      compile_list (dict): List of all sources (inkl. status, output, ...)
      app_config (properties, optional): Application config file

  Raises:
      Exception: If a command fails an exception will be thrown
  """

  build_output_dir = app_config['general'].get('build-output-dir', 'build-output')
  
  # Level 1-n
  for level_item in compile_list['compiles']:
    
    logging.info(f"Run {level_item['level']=}: {len(level_item['sources'])} entries; {build_output_dir=}")
    
    # Each entry (source) in a level list
    for level_list_entry in level_item['sources']:

      # Level list entry is a dict
      src_name = level_list_entry['source']
      cmds = level_list_entry['cmds']
      
      sub_folder = os.path.basename(pathlib.Path(src_name).parent)
      src_name = src_name.replace(f"{sub_folder}/", '')

      i=0

      for cmd_results in cmds:

        i += 1
        if cmd_results['status'] == 'new':
          continue

        logging.debug(f"Details: {src_name}, {cmd_results.get('cmd')}")
        logging.debug(cmd_results.keys())

        files.writeText(cmd_results.get('cmd', ''), os.path.join(build_output_dir, src_name, f"command-{i}.cmd"))
        files.writeText(cmd_results.get('stdout', ''), os.path.join(build_output_dir, src_name, f"command-{i}.splf"))
        files.writeText(cmd_results.get('joblog', ''), os.path.join(build_output_dir, src_name, f"command-{i}.joblog"))
        files.writeText(cmd_results.get('stderr', ''), os.path.join(build_output_dir, src_name, f"command-{i}.error"))

  



def create_result_doc(compile_list, app_config=default_app_config, encoding='utf-8'):

  build_output_dir = app_config['general'].get('build-output-dir', 'build-output')
  src_dir = app_config['general'].get('source-dir', 'src')
  dependend_objects_list = files.getJson(constants.DEPENDEND_OBJECT_LIST)
  changed_sources_list = files.getJson(constants.CHANGED_OBJECT_LIST)


  compiled_obj_list_md_file = app_config['general'].get('compiled-object-list-md', 'compiled-object-list.md')
  compiled_obj_list_md_template = files.readText('docs/summary-template.md')
  compiled_obj_list_md_content = ''

  status_color= {
    'new': '<span style="background-color:#adcbe3;color:black">$(status)</span>',
    'error': '<span style="background-color:#f96161;color:black">$(status)</span>',
    'failed': '<span style="background-color:#f96161;color:black">$(status)</span>',
    'success': '<span style="background-color:#76FF03;color:black">$(status)</span>',
    'in process': '<span style="background-color:#0099ff;color:black">$(status)</span>'
  }

  # Level 1-n
  #for level, level_list in compile_list):
  for level_item in compile_list['compiles']:

    compiled_obj_list_md_content += f'\n| **{level_item["level"]}. level** |'
    
    # Each entry (source) in a level list
    for level_list_entry in level_item['sources']:

      # Level list entry is a dict
      #for src_name, cmds in level_list_entry.items():
      src_name = level_list_entry['source']
      cmds = level_list_entry['cmds']
    
      sub_folder = os.path.basename(pathlib.Path(src_name).parent)
      lib_obj_name = src_name.replace(f"{sub_folder}/", '')
      lib = os.path.basename(pathlib.Path(lib_obj_name).parent)
      obj_lib = os.path.basename(pathlib.Path(lib_obj_name).parent)
      obj_name = os.path.basename(src_name)
      lib_obj_name_md_encoded = lib_obj_name.replace('$', '\\$').replace('#', '%23')

      logging.debug(f"{build_output_dir=}, {sub_folder=}, {lib_obj_name=}, {lib_obj_name_md_encoded=}, {obj_name=}, {obj_lib=}")

      last_status = 'new'
      last_timestamp = None

      details = '<table><tr><th>timestamp</th><th>status</th><th>command</th></tr>'

      i=0

      for cmd_results in cmds:

        i += 1
        if cmd_results.get('status') != 'new':
          last_status = cmd_results.get('status')
          last_timestamp = cmd_results.get('updated')

        cmd = cmd_results['cmd'].replace('\\', '\\\\').replace('$', '\\$').replace('#', '\\#')
        cmd_md = cmd.replace('"', '\\"')#.replace('$', '\%24')

        details += f"<tr><td>{cmd_results.get('updated')}</td><td>{status_color[cmd_results['status']].replace('$(status)', cmd_results['status'])}</td><td><details><summary>{cmd_md[:30]}...</summary><code>{cmd}</code></details> </td>"

        if 'joblog' in cmd_results.keys():
          details += f"<td> [Joblog](/{build_output_dir}/{lib_obj_name_md_encoded}/command-{i}.joblog)</td>"
        if 'stdout' in cmd_results.keys():
          details += f"<td> [Spool file](/{build_output_dir}/{lib_obj_name_md_encoded}/command-{i}.splf)</td>"
        if 'stderr' in cmd_results.keys() and len(cmd_results['stderr']) > 0:
          details += f"<td> [Error](/{build_output_dir}/{lib_obj_name_md_encoded}/command-{i}.error)</td>"
          
        details += "</tr>"

      details += '</table>'


      src_name_without_lib = str(pathlib.Path(*pathlib.Path(src_name).parts[1:]))
      if os.path.sep == '\\': # Needed because of Windows file format
        path_file = PureWindowsPath(src_name_without_lib).as_posix()

      src_name_without_lib = src_name_without_lib.replace('\\', '\\\\')
      src_name = src_name.replace('\\', '\\\\')
      obj_lib = obj_lib.replace('\\', '\\\\')
      src_name_md_encoded = src_name.replace('"', '\\"').replace('$', '\\%24').replace('#', '\\%23')
      #obj_name_md_encoded = src_name.replace('"', '\\"').replace('$', '\%24').replace('#', '\\#')
      compiled_obj_list_md_content += f"\n| | {obj_lib} | [{src_name_without_lib}](/{src_dir}/{src_name_md_encoded}) | {status_color[last_status].replace('$(status)', last_status)} | <details><summary>{len(cmds)} commands</summary> {details} </details>|"
  
  logging.debug(dependend_objects_list)
  compiled_obj_list_md_template = compiled_obj_list_md_template.replace('{%date%}', compile_list['timestamp'])
  compiled_obj_list_md_template = compiled_obj_list_md_template.replace('{%new_sources%}', get_html_list(changed_sources_list['new-objects']))
  compiled_obj_list_md_template = compiled_obj_list_md_template.replace('{%changed_sources%}', get_html_list(changed_sources_list['changed-sources']))
  compiled_obj_list_md_template = compiled_obj_list_md_template.replace('{%dependend_objects%}', get_html_list(dependend_objects_list))
  compiled_obj_list_md_content = compiled_obj_list_md_template.replace('{%content%}', compiled_obj_list_md_content)
  files.writeText(compiled_obj_list_md_content, compiled_obj_list_md_file, encoding=encoding)


def get_html_list(obj_list):
  html = '<ul>'
  for obj in obj_list:
    html += f"<li>{obj}</li>"
  html += '</ul>'
  return html