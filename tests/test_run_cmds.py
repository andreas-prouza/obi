import unittest
import json
import os
import logging

from etc import logger_config

from etc import constants
from module import dependency
from module import properties
from module import run_cmds
from module import files



class TestRunCmds(unittest.TestCase):

  app_config = properties.get_config('tests/test_run_cmd/config.toml')


  def test_source_build_cmd(self):
    
    all_dependencies = properties.get_config('tests/test_build_cmd/dependency.toml')
    compiled_object_list = properties.get_config(TestRunCmds.app_config['general']['compiled-object-list'])

    targets = dependency.get_build_order(
      all_dependencies, [
        "pl/qsqlsrc/logger.sqltable.file",
        "pl/qrpglesrc/errhdlsql.sqlrpgle.srvpgm", 
        "pl/qrpglesrc/date.sqlrpgle.srvpgm"
        ],
      TestRunCmds.app_config
      )

    logging.error("Run test build")

    files.writeJson(targets, 'tests/test_run_cmd/out/1_target_list.json')
    run_cmds.run_build_object_list(targets, 'tests/test_run_cmd/out/1_target_list.json', TestRunCmds.app_config)

    compiled_object_list_new = properties.get_config(TestRunCmds.app_config['general']['compiled-object-list'])

    print(compiled_object_list.get('pl/qsqlsrc/logger.sqltable.file'))
    print(compiled_object_list_new['pl/qsqlsrc/logger.sqltable.file'])




