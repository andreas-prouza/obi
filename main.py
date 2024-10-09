import datetime
import json
import logging
import argparse
import sys, os, pathlib
import subprocess
from contextlib import suppress
import shutil


#################################################################
# Parser settings
#################################################################

parser = argparse.ArgumentParser(
  prog='OBI: Object Builder for i',
  description='Find detailed description in README.md',
  epilog='Example: ...'
)

parser.add_argument('-a', '--action', help='Run action: Create builds (json); Run builds; Get results; Open report summary; Generate object list; Generate source list', 
      choices=['create', 'run', 'results', 'open_result', 'gen_obj_list', 'gen_src_list'], required=True)
parser.add_argument('-s', '--source', help='Consider single source', required=False)
parser.add_argument('-p', '--set-path', help='Path of the source project directory', required=True)
parser.add_argument('-e', '--editor', help='Editor to open MD file', required=False)

args = parser.parse_args()


#################################################################
# Path settings
#################################################################

sys.path.insert(0, args.set_path)
sys.path.insert(0, os.path.join( args.set_path, '.obi'))
original_dir=os.getcwd()
#os.chdir(os.path.realpath(os.path.dirname(__file__)))
os.chdir(os.path.realpath(args.set_path))


#################################################################
# Application
#################################################################


from etc import constants
from etc import logger_config

from module import properties
from module import files
from module import dependency
from module import run_cmds
from module import results
from module import toml_tools

logging.info(f"Arguments: {vars(args)}")



def run_builds(args):

  logging.debug(f"Run build list")

  # Properties
  logging.debug("Load configs")
  app_config = properties.get_app_properties()
  general_config = app_config['general']
  build_list_file_name = general_config.get('compile-list', '.obi/tmp/compile-list.json')

  logging.debug("Load compile list")
  build_targets = {}
  with open(build_list_file_name, 'r') as f:
        build_targets = json.load(f)

  logging.debug("Remember sources needed to compile")
  sources = []
  for level_item in build_targets['compiles']:       # Level-List
    for level_list_entry in level_item['sources']:                #   |--> Source-List
      sources.append(level_list_entry['source'])
  files.sources_needs_compiled(sources, app_config)

  logging.debug("Run object builds")
  try:
    run_cmds.run_build_object_list(build_targets, build_list_file_name)
  except Exception as e:
    logging.exception(e)

  get_results(args)



def get_results(args):

  logging.debug(f"Get results from build")

  # Properties
  app_config = properties.get_app_properties()
  general_config = app_config['general']
  build_list_file_name = general_config.get('compile-list', '.obi/tmp/compile-list.json')
  fs_encoding = general_config.get('file-system-encoding', 'utf-8')


  build_targets = {}
  with open(build_list_file_name, 'r') as f:
        build_targets = json.load(f)

  # Extract joblog, spooled file
  results.save_outputs_in_files(build_targets, app_config)

  # Generate document
  # Because it's always executed on IBM i, encoding ist hardcoded UTF-8
  results.create_result_doc(build_targets, app_config, encoding='utf-8')



def create_build_list(args):

  logging.debug(f"Create build list")

  # Properties
  app_config = properties.get_app_properties()
  general_config = app_config['general']
  
  source_dir = os.path.join(general_config['local-base-dir'], general_config['source-dir'])
  build_list = general_config['compiled-object-list']
  object_types = general_config['supported-object-types']
  dependency_list = properties.get_config(general_config['dependency-list'])
  build_output_dir = app_config['general'].get('build-output-dir', '.obi/build-output')
  fs_encoding = app_config['general'].get('file-system-encoding', 'utf-8')

  # Removes old files and dirs
  if len(build_output_dir.strip()) < 3 or build_output_dir.strip() == '/':
    raise Exception(f'Wrong build output dir: {build_output_dir}')
  shutil.rmtree(build_output_dir, ignore_errors=True)

  # Get source list
  if args.source is None:
    source_list = files.get_files(source_dir, object_types, fs_encoding)
    changed_sources_list=files.get_changed_sources(source_dir, build_list, object_types, source_list)

  # Source provided by parameter
  if args.source is not None:
    changed_sources_list=files.get_changed_sources(source_dir, build_list, object_types, {args.source: {"hash": ''}})

  files.writeJson(changed_sources_list, constants.CHANGED_OBJECT_LIST)
  build_targets = dependency.get_build_order(dependency_list, changed_sources_list['new-objects'] + changed_sources_list['changed-sources'])

  # Write source list to json
  files.writeJson(build_targets, general_config.get('compile-list', '.obi/tmp/compile-list.json'))

  # Remove compiled objects from object-list (they need to get compiled)
  # Why remove during build list creation?!?!?!?!
  #toml_tools.remove_compiled_objects(build_targets, app_config)

  # Generate document
  results.create_result_doc(build_targets, app_config, fs_encoding)



def open_doc_in_editor(args):
  # Properties
  app_config = properties.get_app_properties()
  # Generate document
  get_results(args)

  # Open document in editor
  editor = 'code'
  if args.editor is not None:
    editor=args.editor
  s=subprocess.run(f"{editor} {app_config['general'].get('compiled-object-list-md', '.obi/build-output/compiled-object-list.md')}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=False)




def generate_object_list(args):

  logging.debug(f"Generate object list")

  # Properties
  app_config = properties.get_app_properties()
  general_config = app_config['general']
  
  source_dir = os.path.join(general_config['local-base-dir'], general_config['source-dir'])
  build_list = general_config['compiled-object-list']
  object_types = general_config['supported-object-types']
  fs_encoding = app_config['general'].get('file-system-encoding', 'utf-8')

  source_list = files.get_files(source_dir, object_types, fs_encoding, with_time=True)
  files.writeToml(source_list, build_list)



def generate_source_list(args):

  logging.debug(f"Generate source list")

  # Properties
  app_config = properties.get_app_properties()
  general_config = app_config['general']
  
  source_dir = os.path.join(general_config['local-base-dir'], general_config['source-dir'])
  build_list = general_config['source-list']
  object_types = general_config['supported-object-types']
  fs_encoding = app_config['general'].get('file-system-encoding', 'utf-8')

  source_list = files.get_files(source_dir, object_types, fs_encoding, with_time=True)
  files.writeToml(source_list, build_list)



action = {
  'create': create_build_list,
  'run': run_builds,
  'results': get_results,
  'open_result': open_doc_in_editor,
  'gen_obj_list': generate_object_list,
  'gen_src_list': generate_source_list
}


if __name__ == "__main__":
  
  action[args.action](args)