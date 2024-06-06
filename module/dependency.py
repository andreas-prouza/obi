import logging
from pathlib import Path

from etc import constants
from . import properties
from . import dict_tools
from . import build_cmds
from . import files


def parse_dependency_file(file_path):

  return properties.get_config(file_path)



def get_build_order(dependency_dict, target_list=[], app_config=properties.get_config(constants.CONFIG_TOML)):

  objects_tree = get_targets_depended_objects(dependency_dict, target_list)
  dependend_objects = get_targets_only_depended_objects(dependency_dict, target_list)
  logging.debug(f"{objects_tree=}")
  files.writeJson(dependend_objects, constants.DEPENDEND_OBJECT_LIST)

  ordered_target_tree = get_targets_by_level(objects_tree)
  logging.debug(f"{ordered_target_tree=}")
  files.writeJson(ordered_target_tree, 'tmp/ordered_target_tree.json')

  new_target_tree = remove_duplicities(ordered_target_tree)
  files.writeJson(new_target_tree, 'tmp/new_target_tree.json')
  logging.debug(f"{new_target_tree=}")

  build_cmds.add_build_cmds(new_target_tree, app_config)

  return new_target_tree




def get_all_targets(dependency_dict, target_list=[]):
  tree = target_list

  for obj, obj_dependencies in dependency_dict.items():
    if any(item in target_list for item in obj_dependencies):
      #tree.append(obj) #build_dependency_tree(dependency_dict, dep))
      tree.extend(build_dependency_tree(dependency_dict, [obj]))

  return tree



def get_targets_depended_objects(dependency_dict, targets=[], result={}):

  targets_objects = {}

  for target in targets:

    targets_objects[target] = get_target_depended_objects(dependency_dict, target)

  return targets_objects



def get_target_depended_objects(dependency_dict, target, result={}):

  dependend_objects = {}

  for obj, obj_dependencies in dependency_dict.items():
    if target in obj_dependencies:

      if not Path(obj).is_file():
        logging.debug(f"Doesn't exist: {obj=}, {Path(obj).is_file()=}")
        continue
    
      logging.debug(f"Add obj {obj=}")
      #tree.append(obj) #build_dependency_tree(dependency_dict, dep))
      dependend_objects[obj]=get_target_depended_objects(dependency_dict, obj, result)
  
  return dependend_objects


def get_targets_only_depended_objects(dependency_dict, targets=[], result={}):

  targets_objects = []

  for target in targets:
    logging.debug(f"Dependend 1 {target}")
    targets_objects = targets_objects + get_target_only_depended_objects(dependency_dict, target)

  return list(set(targets_objects))



def get_target_only_depended_objects(dependency_dict, target, result={}):

  dependend_objects = []

  for obj, obj_dependencies in dependency_dict.items():
    if target in obj_dependencies:
      
      if not Path(obj).is_file():
        logging.warning(f"Doesn't exist: {obj=}, {Path(obj).is_file()=}")
        continue
      
      #tree.append(obj) #build_dependency_tree(dependency_dict, dep))
      dependend_objects = dependend_objects + [obj] + get_target_only_depended_objects(dependency_dict, obj, result)
  
  return dependend_objects



def remove_duplicities(target_tree={}):

  # All levels
  for level in sorted(list(target_tree.keys())):

    # All objects in this level
    for obj in list(target_tree[level]):

      # Scan reverse for duplicated objects
      for rev_level in reversed(sorted(list(target_tree.keys()))):

        if level < rev_level and obj in target_tree[rev_level] and obj in target_tree[level]:
          target_tree[level].remove(obj)

  return target_tree




def get_targets_by_level(target_tree={}, level=1):
  
  new_target_tree = {}
  
  # Add object to list
  for obj, next_objs in target_tree.items():
    
    if level not in new_target_tree.keys():
      new_target_tree[level] = []

    if obj in new_target_tree[level]:
      continue

    new_target_tree[level].append(obj)

    # Also add dependend objects to list
    for next_obj, next_sub_objs in next_objs.items():

      if level+1 not in new_target_tree.keys():
        new_target_tree[level+1] = []
      
      if next_obj in new_target_tree[level+1]:
        continue

      new_target_tree[level+1].append(next_obj)

      # Recursive call to go through the tree
      extended_tree = get_targets_by_level(next_sub_objs, level+2)
      new_target_tree = dict_tools.deep_merge(extended_tree, new_target_tree)
      a='x'

  return dict(sorted(new_target_tree.items()))

