import logging
import pathlib
import fnmatch
import re

from etc import constants
from module import toml_tools, files, properties


def get_steps(app_config: dict, source: str) -> list:

    for extension_step in app_config['global']['steps']:
        if extension_step == source:
            return app_config['global']['steps'][extension_step]
        
    for extension_step in app_config['global']['steps']:
        if fnmatch.fnmatch(source, extension_step):
            return app_config['global']['steps'][extension_step]
        
    src_suffixes = pathlib.Path(source).suffixes
    file_extensions = "".join(src_suffixes[-2:]).removeprefix('.')
    logging.debug(f"{file_extensions=}")

    return app_config['global']['steps'].get(file_extensions, [])




def get_extended_steps(app_config: dict, source: str) -> list:
    """If extended steps exist, search for a match
    Args:
        app_config (properties): Application config file
        source (str): source file name

    Returns:
        list: List of steps
    """

    conditions = {
        'SOURCE_FILE_NAME': match_condition_SOURCE_FILE_NAME
    }

    sources_config=properties.get_config(constants.EXTENDED_SOURCE_PROCESS_CONFIG_TOML)
    if len(sources_config) == 0:
        return []

    for proc_name, proc_dict in sources_config.items():

        if 'conditions' not in proc_dict:
            continue

        found = True
        for cond_name, cond_dict in proc_dict.items():
        
            # Every condition needs to match
            found = conditions[cond_name](source, cond_dict)
            if not found:
                break

        if found:
            return step_values['steps']




def match_condition_SOURCE_FILE_NAME(source:str, conditions) -> bool:

    if conditions['settings']['use-regex']:
        return re.search(conditions['filter'], source)

    return fnmatch.fnmatch(source, conditions['filter'])