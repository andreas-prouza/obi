import logging, os
from pathlib import Path
from datetime import datetime

from etc import constants
from . import properties
from . import dict_tools
from . import build_cmds
from . import files


default_app_config = properties.get_app_properties()


def parse_dependency_file(file_path):

  return properties.get_config(file_path)



def get_build_order(dependency_dict, target_list=[], app_config=properties.get_app_properties()):

  objects_tree = get_targets_depended_objects(dependency_dict, target_list)
  files.writeJson(objects_tree, '.obi/tmp/objects_tree.json')

  dependend_objects = get_targets_only_depended_objects(dependency_dict, target_list)
  logging.debug(f"{objects_tree=}")
  files.writeJson(dependend_objects, constants.DEPENDEND_OBJECT_LIST)

  ordered_target_tree = get_targets_by_level(objects_tree)
  logging.debug(f"{ordered_target_tree=}")
  files.writeJson(ordered_target_tree, '.obi/tmp/ordered_target_tree.json')

  new_target_tree = remove_duplicities(ordered_target_tree)
  files.writeJson(new_target_tree, '.obi/tmp/new_target_tree.json')
  logging.debug(f"{new_target_tree=}")

  build_cmds.add_build_cmds(new_target_tree, app_config)

  new_target_tree = {'timestamp': str(datetime.now()), 'compiles': new_target_tree}

  return new_target_tree




def get_all_targets(dependency_dict, target_list=[]):
  tree = target_list

  for obj, obj_dependencies in dependency_dict.items():
    if any(item in target_list for item in obj_dependencies):
      #tree.append(obj) #build_dependency_tree(dependency_dict, dep))
      tree.extend(build_dependency_tree(dependency_dict, [obj]))

  return tree



def get_targets_depended_objects(dependency_dict, targets=[], result={}):
  """Get sources as dict with it's dependend sources
    {'source1': {'source3', 'source4'}, 'source2': {}}

  Args:
      dependency_dict (_type_): _description_
      targets (list, optional): _description_. Defaults to [].
      result (dict, optional): _description_. Defaults to {}.

  Returns:
      _type_: _description_
  """

  targets_objects = {}

  for target in targets:

    targets_objects[target] = get_target_depended_objects(dependency_dict, target)

  return targets_objects



def get_target_depended_objects(dependency_dict, target, result={}):

  dependend_objects = {}
  src_base_path = default_app_config['general'].get('source-dir', 'src')

  for obj, obj_dependencies in dependency_dict.items():
    if target in obj_dependencies:

      if not Path(os.path.join(src_base_path, obj)).is_file():
        logging.debug(f"Doesn't exist: {obj=}, {Path(obj).is_file()=}")
        continue
    
      logging.debug(f"Add obj {obj=}")
      #tree.append(obj) #build_dependency_tree(dependency_dict, dep))
      dependend_objects[obj]=get_target_depended_objects(dependency_dict, obj, result)
  
  return dependend_objects



def get_targets_only_depended_objects(dependency_dict, targets=[]) -> []:
  """Get dependencies of the targets

  Args:
      dependency_dict (dict}): All dependencies of all sources
      targets (list, optional): List of targets. Defaults to []

  Returns:
      list: Returns a list with dependencies
  """

  targets_objects = []

  for target in targets:
    logging.debug(f"Dependend 1 {target}")
    targets_objects = targets_objects + get_target_only_depended_objects(dependency_dict, target, targets)

  return list(set(targets_objects))



def get_target_only_depended_objects(dependency_dict, target, orig_targets:[]):

  dependend_objects = []
  src_base_path = default_app_config['general'].get('source-dir', 'src')

  for obj, obj_dependencies in dependency_dict.items():
    if target in obj_dependencies:
      
      if not Path(os.path.join(src_base_path, obj)).is_file():
        logging.warning(f"Doesn't exist: {obj=}, {Path(obj).is_file()=}")
        continue
      
      if (obj in orig_targets):
        continue

      #tree.append(obj) #build_dependency_tree(dependency_dict, dep))
      dependend_objects = dependend_objects + [obj] + get_target_only_depended_objects(dependency_dict, obj, orig_targets)
  
  return dependend_objects



def remove_duplicities(target_tree=[]):

  # All levels
  for level_item in sorted(target_tree, key=lambda d: d['level']):

    # All objects in this level
    for obj in level_item['sources']:

      # Scan reverse for duplicated objects
      for rev_level_item in reversed(sorted(target_tree, key=lambda d: d['level'])):

        rev_level_sources = [item['source'] for item in rev_level_item['sources']]

        for i in range(len(target_tree)):
          sources = [item['source'] for item in target_tree[i]['sources']]
          if target_tree[i]['level'] < rev_level_item['level'] and obj['source'] in rev_level_sources and obj['source'] in sources:
            target_tree[i]['sources'].remove(obj)

  return target_tree




def get_targets_by_level(target_tree={}, level=1):
  
  new_target_tree = []
  
  # Add object to list
  for obj, next_objs in target_tree.items():

    loop_level_obj = {}
    loop_level_obj = [item for item in new_target_tree if item['level'] == level]
    if len(loop_level_obj) > 0:
      loop_level_obj = loop_level_obj[0]

    #if level not in new_target_tree.keys():
    if not loop_level_obj:
      loop_level_obj = {'level': level, 'sources': []}
      new_target_tree.append(loop_level_obj)

    #if obj in new_target_tree[level]:
    if obj in [item['source'] for item in loop_level_obj['sources']]:
      continue

    loop_level_obj['sources'].append({'source': obj, 'cmds': []})

    # Also add dependend objects to list
    for next_obj, next_sub_objs in next_objs.items():

      loop_next_level_obj = {}
      loop_next_level_obj = [item for item in new_target_tree if item['level'] == level+1]
      if loop_next_level_obj:
        loop_next_level_obj = loop_next_level_obj[0]

      if not loop_next_level_obj:
        loop_next_level_obj = {'level': level+1, 'sources': []}
        new_target_tree.append(loop_next_level_obj)
      
      if next_obj in [item['source'] for item in loop_next_level_obj['sources']]:
        continue

      loop_next_level_obj['sources'].append({'source': next_obj, 'cmds': []})

      # Recursive call to go through the tree
      extended_tree = get_targets_by_level(next_sub_objs, level+2)
      new_target_tree = dict_tools.deep_list_merge(extended_tree, new_target_tree)

  return sorted(new_target_tree, key=lambda d: d['level'])

