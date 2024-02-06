import unittest
import json
import os

from module import dependency
from module import properties
from module import build_cmds

class TestBuildCmds(unittest.TestCase):



    def test_source_build_cmd(self):
      
      cmds = build_cmds.get_source_build_cmds("prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm")

      self.assertEqual(cmds[0], "CRTSQLRPGI OBJ(prouzat1) SRCSTMF('$HOME/ibm-i-build/src/prouzalib/qrpglesrc/logger.sqlrpgle.srvpgm') OBJTYPE(*MODULE) RPGPPOPT(*LVL2) TGTRLS(*CURRENT) DBGVIEW(*SOURCE) REPLACE(*YES) COMPILEOPT('TGTCCSID(*JOB) INCDIR(''src/prouzalib'' ''src/prouzalib2'')')")



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