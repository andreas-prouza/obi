import unittest
import json

from etc import logger_config

from module import dependency
from module import properties
from module import dict_tools
from module import files

class TestDependency(unittest.TestCase):



    def test_tree(self):
      
      all_dependencies = properties.get_config('tests/test_dependency/dependency.toml')
      with open('tests/test_dependency/target_list.json', 'r') as f:
        expected_targets = json.load(f)


      targets = dependency.get_build_order(
        all_dependencies, [
          "pl/qrpglesrc/cpysrc2ifs.sqlrpgle.pgm",
          "pl/qrpglesrc/errhdlsql.sqlrpgle.srvpgm", 
          "pl/qrpglesrc/date.sqlrpgle.srvpgm"
          ]
        )
      
      # Necessary to convert, because of styling & co
      targets_json = json.dumps(targets)
      targets_converted = json.loads(targets_json)

      self.assertEqual(targets_converted, expected_targets)




    def test_another_tree(self):
      
      all_dependencies = properties.get_config('tests/test_dependency/dependency.toml')
      with open('tests/test_dependency/target_list_2.json', 'r') as f:
        expected_targets = json.load(f)

      targets = dependency.get_build_order(
        all_dependencies, [
          "pl/qrpglesrc/logger.sqlrpgle.srvpgm",
          "pl/qrpglesrc/errhdlsql.sqlrpgle.srvpgm", 
          "pl/qrpglesrc/date.sqlrpgle.srvpgm"
          ]
        )
      files.writeJson(targets, 'tests/test_dependency/out/2_target_list.json')
      
      #objects_tree = dependency.get_targets_depended_objects(all_dependencies, [
      #    "pl/qrpglesrc/logger.sqlrpgle.srvpgm",
      #    "pl/qrpglesrc/errhdlsql.sqlrpgle.srvpgm", 
      #    "pl/qrpglesrc/date.sqlrpgle.srvpgm"
      #    ])
      #files.writeJson(objects_tree, 'tests/out/objects_tree.json')
      #
      #ordered_target_tree = dependency.get_targets_by_level(objects_tree)
      #files.writeJson(ordered_target_tree, 'tests/out/ordered_target_tree.json')

      #new_target_tree = dependency.remove_duplicities(ordered_target_tree)
      #files.writeJson(new_target_tree, 'tests/out/new_target_tree.json')

      # Necessary to convert, because of styling & co
      targets_json = json.dumps(targets)
      targets_converted = json.loads(targets_json)

      self.assertEqual(targets_converted, expected_targets)





    def test_another_tree_2(self):

      all_dependencies = properties.get_config('tests/test_dependency/dependency.toml')
      with open('tests/test_dependency/expected_target_list_3.json', 'r') as f:
        expected_targets = json.load(f)

      targets = dependency.get_build_order(
        all_dependencies, [
          "pl/qsqlsrc/logger.sqltable.file",
          "pl/qrpglesrc/newpgm.rpgle.pgm",
          "pl/qrpglesrc/errhdlsql.sqlrpgle.srvpgm", 
          "pl/qrpglesrc/date.sqlrpgle.srvpgm"
          ]
        )
      files.writeJson(targets, 'tests/test_dependency/out/3_target_list.json')
      
      # Necessary to convert, because of styling & co
      targets_json = json.dumps(targets)
      targets_converted = json.loads(targets_json)

      self.assertEqual(targets_converted, expected_targets)




    
    def test_dict_merge(self):

      a={0: ['a', 'b']}
      b={0: ['b', 'c']}
      self.assertEqual(dict_tools.deep_merge(a, b), {0: ['a', 'b', 'c']})