from module import properties


def get_table_element(toml, tree_list):
    
    toml_copy = toml.copy()

    for entry in tree_list:
        
        if entry not in toml_copy:
            return None

        toml_copy = toml_copy[entry]
    
    return toml_copy


def remove_compiled_objects(compile_list):

    compiled_object_list = properties.get_config(app_config['general']['compiled-object-list'])
  
    # Level 1-n
    for level, level_list in compile_list.items():
        
        logging.info(f"Run {level=}: {len(level_list)} entries")

        # Each entry in a level list
        for level_list_entry in level_list:

            # Level list entry is a dict
            for src_name, cmds in level_list_entry.items():
                if src_name in compiled_object_list.keys():
                    del compiled_object_list[src_name]

    properties.write_config(app_config['general']['compiled-object-list'], compiled_object_list)
