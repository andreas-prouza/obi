import datetime
import json
import logging
import argparse
import sys, os, pathlib

from etc import constants
from etc import logger_config

from module import properties
from module import files
from module import dependency
from module import run_cmds


#################################################################
# Parser settings
#################################################################

parser = argparse.ArgumentParser(
  prog='OBI: Object Builder for i',
  description='Find detailed description in README.md',
  epilog='Example: ...'
)

parser.add_argument('-a', '--action', help='Run action: Create builds (json); Run builds', choices=['create', 'run'], required=True)

args = parser.parse_args()

print(vars(args))



def run_builds(args):

  logging.debug(f"Run build list")

  # Properties
  app_config = properties.get_config(constants.CONFIG_TOML)
  general_config = app_config['general']
  build_list = general_config.get('compile-list', 'tmp/compile-list.json')

  build_targets = {}
  with open(build_list, 'r') as f:
        build_targets = json.load(f)

  run_cmds.run_build_object_list(build_targets, build_list)



def create_build_list(args):

  logging.debug(f"Create build list")

  # Properties
  app_config = properties.get_config(constants.CONFIG_TOML)
  general_config = app_config['general']
  
  source_dir = os.path.join(general_config['project-dir'], general_config['source-dir'])
  build_list = general_config['compiled-object-list']
  object_types = general_config['supported-object-types']
  dependency_list = properties.get_config(general_config['dependency-list'])

  # Get source list
  source_list = files.get_files(source_dir, object_types)
  changed_sources_list=files.get_changed_sources(source_dir, build_list, object_types)
  build_targets = dependency.get_build_order(dependency_list, changed_sources_list['new-objects'] + changed_sources_list['changed-sources'])

  # Write source list to json
  files.writeJson(build_targets, general_config.get('compile-list', 'tmp/compile-list.json'))



action = {
  'create': create_build_list,
  'run': run_builds
}


if __name__ == "__main__":
  
  action[args.action](args)