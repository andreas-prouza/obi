import logging
import pathlib
import fnmatch
import re

from etc import constants
from module import toml_tools, files, properties
from typing import TypedDict, List, Union


class FilterDict(TypedDict):
    SOURCE_FILE_NAME: Union[str, None]
    SOURCE_FILE_NAME2: Union[str, None]

class ExtendedSourceConfig(TypedDict):
    steps: List[str]
    use_regex: bool
    filter: FilterDict

class ExtendedSourceConfigFile(TypedDict):
    extended_source_processing: List[ExtendedSourceConfig]



def get_steps(source: str, app_config: dict) -> list[str]:

    """Get steps for a source file
    Args:
        app_config (properties): Application config file
        source (str): source file name
    Returns:
        list[str]: List of steps
    """

    steps: list[str] = get_extended_steps(source, app_config)
    # No match found
    if steps is not None:
        return steps

    # Check if source matches the global steps
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




def get_extended_steps(source: str, app_config: dict) -> list|None:
    """If extended steps exist, search for a match
    Args:
        app_config (properties): Application config file
        source (str): source file name

    Returns:
        list|None: List of steps or None if no match found
    """

    # No match found
    last_steps: list[str] = None
    last_config_entry: ExtendedSourceConfig = None

    sources_config: ExtendedSourceConfigFile = properties.get_config(constants.EXTENDED_SOURCE_PROCESS_CONFIG_TOML)
    if len(sources_config) == 0 or 'extended_source_processing' not in sources_config:
        return None
    
    source_properties: {} = properties.get_source_properties(app_config, source)

    for source_config_entry in sources_config['extended_source_processing']:

        # Every condition needs to match
        if match_source_conditions(source_config_entry, source, source_properties):
            
            # A source should only have one match in the extended source processing
            if last_steps is not None:
                error = (f"Multiple extended source processing entries found for {source=}: {last_config_entry=}, {source_config_entry=}")
                logging.error(error)
                raise Exception(error)
            
            last_steps = source_config_entry['steps']
            last_config_entry = source_config_entry
            logging.debug(f"Extended source processing entry found for {source=}: {last_config_entry=}")
        
    return last_steps




def match_source_conditions(source_config_entry: ExtendedSourceConfig, source: str, source_properties: {}) -> bool:
    """Process conditions for extended source commands
    Args:
        conditions (dict): Conditions to process
        source (str): Source file name
        source_properties (dict): Source properties (TGTRLS, STGMDL, TARGET_LIB, OBJ_NAME etc.)
    Returns:
        bool: True if conditions match
    """

    conditions = {
        'SOURCE_FILE_NAME': match_condition_SOURCE_FILE_NAME,
        'TARGET_LIB': match_condition_TARGET_LIB
    }

    if len(source_config_entry['conditions']) == 0:
        return False

    for condition_name, condition_value in source_config_entry['conditions'].items():

        if condition_name not in conditions:
            logging.warning(f"Unknown extended source condition name: {condition_name}, {source=}")
            return False

        # Every condition needs to match
        found = conditions[condition_name](source, condition_value, source_config_entry, source_properties)
        if not found:
            return False

    return True




def match_condition_SOURCE_FILE_NAME(source:str, condition_value:str, source_config_entry: ExtendedSourceConfig, source_properties: {}) -> bool:

    if source_config_entry['use_regex']:
        return re.search(condition_value, source)

    return fnmatch.fnmatch(source, condition_value)





def match_condition_TARGET_LIB(source:str, condition_value:str, source_config_entry: ExtendedSourceConfig, source_properties: {}) -> bool:

    if source_config_entry['use_regex']:
        return re.search(condition_value, source_properties['TARGET_LIB'])

    return fnmatch.fnmatch(source_properties['TARGET_LIB'], condition_value)



