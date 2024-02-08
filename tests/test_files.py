import unittest
import json
import os

from etc import logger_config

from module import dependency
from module import properties
from module import files

class TestFiles(unittest.TestCase):



    def test_changed_sources(self):
      
      all_dependencies = properties.get_config('tests/test_dependency/dependency.toml')
      source_dir = 'tests/test_files/src'
      build_list = 'tests/test_files/build.toml'
      object_types = ['pgm', 'file', 'srvpgm']

      source_list = files.get_files(source_dir, object_types)
      properties.write_config(build_list, source_list)

      changed_list=files.get_changed_sources(source_dir, build_list, object_types)

      self.assertTrue(len(source_list) > 0)
      self.assertEqual(len(changed_list['new-objects']), 0)
      self.assertEqual(len(changed_list['changed-sources']), 0)

      source_list.pop('prouzalib2/qrpglesrc/sqlsrv1.sqlrpgle.srvpgm')
      source_list.pop('prouzalib2/qrpglesrc/test1.rpgle.pgm')
      properties.write_config(build_list, source_list)

      changed_list=files.get_changed_sources(source_dir, build_list, object_types)

      self.assertEqual(len(changed_list['new-objects']), 2)
      self.assertEqual(len(changed_list['changed-sources']), 0)

      with open(os.path.join(source_dir, "prouzalib/qsqlsrc/logger.sqltable.file"), "w") as file:
        file.write('-- some changes');

      changed_list=files.get_changed_sources(source_dir, build_list, object_types)

      self.assertEqual(len(changed_list['new-objects']), 2)
      self.assertEqual(len(changed_list['changed-sources']), 1)
