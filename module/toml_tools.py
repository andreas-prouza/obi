import logging
import inspect

from module import properties
from etc import constants



def get_table_element(toml, tree_list):
    
    toml_copy = toml.copy()

    for entry in tree_list:
        
        if entry not in toml_copy:
            return None

        toml_copy = toml_copy[entry]
    
    return toml_copy



def remove_compiled_objects(compile_list, app_config=None):

    if app_config is None:
        app_config = properties.get_app_properties()

    compiled_object_list = properties.get_config(app_config['general']['compiled-object-list'])
  
    # Level 1-n
    for level, level_list in compile_list.items():
        

        # Each entry in a level list
        for level_list_entry in level_list:

            # Level list entry is a dict
            for src_name, cmds in level_list_entry.items():
                if src_name in compiled_object_list.keys():
                    logging.info(f"Remove {level=}: {src_name}")
                    del compiled_object_list[src_name]

    logging.debug(f"Write new build list: {len(compiled_object_list)} objects; {inspect.stack()[1]}")
    properties.write_config(app_config['general']['compiled-object-list'], compiled_object_list)
