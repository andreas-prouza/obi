import unittest
import json
import os

from etc import logger_config

from etc import constants
from module import dependency
from module import properties
from module import build_cmds
from module import files

class TestBuildCmds(unittest.TestCase):

  app_config = properties.get_config(constants.CONFIG_TOML)


  def test_single_source_build_cmd(self):
    cmds = build_cmds.get_source_build_cmds("prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm")
    self.assertEqual(cmds[0], "CRTSQLRPGI OBJ(prouzat1) SRCSTMF('$HOME/ibm-i-build/src/prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm') OBJTYPE(*MODULE) RPGPPOPT(*LVL2) TGTRLS(*CURRENT) DBGVIEW(*SOURCE) REPLACE(*YES) COMPILEOPT('TGTCCSID(*JOB) INCDIR(''src/prouzalib'' ''src/prouzalib2'')')")




  def test_source_build_cmd(self):
    
    all_dependencies = properties.get_config('tests/test_build_cmd/dependency.toml')

    targets = dependency.get_build_order(
      all_dependencies, [
        "pl/qsqlsrc/logger.sqltable.file",
        "pl/qrpglesrc/errhdlsql.sqlrpgle.srvpgm", 
        "pl/qrpglesrc/date.sqlrpgle.srvpgm"
        ]
      )

    files.writeJson(targets, 'tests/test_build_cmd/out/1_target_list.json')

    for level, target_list in targets.items():
      print(f"{level=}, {target_list=}")




  def test_target_lib(self):

    target_lib = properties.get_target_lib('prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm', 'targetlib')
    self.assertEqual(target_lib, 'targetlib')

    target_lib = properties.get_target_lib('prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm', '*source')
    self.assertEqual(target_lib, 'prouzalib')

    target_lib = properties.get_target_lib('prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm', 'targetlib', lib_mapping={ "prouzalib": "prouzat1", "prouzalib2": "prouzat2"})
    self.assertEqual(target_lib, 'targetlib')

    target_lib = properties.get_target_lib('prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm', lib_mapping={ "prouzalib": "prouzat1", "prouzalib2": "prouzat2"})
    self.assertEqual(target_lib, 'prouzat1')

    target_lib = properties.get_target_lib('prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm', lib_mapping={ "foo": "targetlib1", "bar": "targetlib2"})
    self.assertEqual(target_lib, 'prouzalib')