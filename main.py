import datetime
import json
import logging
import argparse
import sys, os, pathlib


#################################################################
# Parser settings
#################################################################

parser = argparse.ArgumentParser(
  prog='OBI: Object Builder for i',
  description='Find detailed description in README.md',
  epilog='Example: ...'
)

parser.add_argument('-a', '--action', help='Run action: Create builds (json); Run builds; Get results', choices=['create', 'run', 'results'], required=True)
parser.add_argument('-p', '--set-path', help='Path of the source project directory', required=True)

args = parser.parse_args()

print(vars(args))


#################################################################
# Path settings
#################################################################

sys.path.insert(0, args.set_path)
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


def run_builds(args):

  logging.debug(f"Run build list")

  # Properties
  app_config = properties.get_config(constants.CONFIG_TOML)
  general_config = app_config['general']
  build_list_file_name = general_config.get('compile-list', 'tmp/compile-list.json')

  build_targets = {}
  with open(build_list_file_name, 'r') as f:
        build_targets = json.load(f)

  run_cmds.run_build_object_list(build_targets, build_list_file_name)



def get_results(args):

  logging.debug(f"Get results from build")

  # Properties
  app_config = properties.get_config(constants.CONFIG_TOML)
  general_config = app_config['general']
  build_list_file_name = general_config.get('compile-list', 'tmp/compile-list.json')

  build_targets = {}
  with open(build_list_file_name, 'r') as f:
        build_targets = json.load(f)

  results.save_outputs_in_files(build_targets, app_config)
  results.create_result_doc(build_targets, app_config)



def create_build_list(args):

  logging.debug(f"Create build list")

  # Properties
  app_config = properties.get_config(constants.CONFIG_TOML)
  general_config = app_config['general']
  
  source_dir = os.path.join(general_config['local-base-dir'], general_config['source-dir'])
  build_list = general_config['compiled-object-list']
  object_types = general_config['supported-object-types']
  dependency_list = properties.get_config(general_config['dependency-list'])

  # Get source list
  source_list = files.get_files(source_dir, object_types)
  changed_sources_list=files.get_changed_sources(source_dir, build_list, object_types)
  print(changed_sources_list)
  build_targets = dependency.get_build_order(dependency_list, changed_sources_list['new-objects'] + changed_sources_list['changed-sources'])

  # Write source list to json
  files.writeJson(build_targets, general_config.get('compile-list', 'tmp/compile-list.json'))



action = {
  'create': create_build_list,
  'run': run_builds,
  'results': get_results
}


if __name__ == "__main__":
  
  action[args.action](args)