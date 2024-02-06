
def get_table_element(toml, tree_list):
    
    toml_copy = toml.copy()

    for entry in tree_list:
        
        if entry not in toml_copy:
            return None

        toml_copy = toml_copy[entry]
    
    return toml_copy