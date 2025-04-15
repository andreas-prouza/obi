import logging
import pathlib
import fnmatch
import re, sys
from io import StringIO

from etc import constants
from module import toml_tools, files, properties
from typing import TypedDict, List, Union
import subprocess


class FilterDict(TypedDict):
    SOURCE_FILE_NAME: Union[str, None]
    SOURCE_FILE_NAME2: Union[str, None]

class ExtendedSourceConfig(TypedDict):
    steps: List[str]
    use_regex: bool
    use_script: str
    exit_point_steps: str
    filter: FilterDict

class ExtendedSourceConfigFile(TypedDict):
    extended_source_processing: List[ExtendedSourceConfig]



def get_steps(source: str, app_config: dict) -> list[str|dict]:

    """Get steps for a source file
    Args:
        app_config (properties): Application config file
        source (str): source file name
    Returns:
        list[str]: List of steps
    """
    init_steps: list[str] = []
    
    if '*ALL' in app_config['global']['steps']:
        init_steps = app_config['global']['steps']['*ALL']
    
    steps: list[str|dict] = get_extended_steps(source, app_config)
    # No match found
    if steps is not None:
        return init_steps + steps

    return init_steps + get_global_steps(source, app_config)




def get_global_steps(source: str, app_config: dict) -> list[str]:
    
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






def get_extended_steps(source: str, app_config: dict) -> list[str|dict]|None:
    """If extended steps exist, search for a match
    Args:
        app_config (properties): Application config file
        source (str): source file name

    Returns:
        list|None: List of steps or None if no match found
    """

    # No match found
    result_steps: list[str|dict] = []
    allow_multiple_matches: bool = True
    last_config_entry: ExtendedSourceConfig = None

    sources_config: ExtendedSourceConfigFile = properties.get_config(constants.EXTENDED_SOURCE_PROCESS_CONFIG_TOML)
    logging.debug(f"{sources_config=}")
    if len(sources_config) == 0 or 'extended_source_processing' not in sources_config:
        return None
    
    source_properties: {} = properties.get_source_properties(app_config, source)

    for source_config_entry in sources_config['extended_source_processing']:
        
        logging.debug(f"Extended source processing entry: {source_config_entry=}")
        use_script: str = source_config_entry.get('use_script', None)

        # Every condition needs to match
        if match_source_conditions(source_config_entry, source, source_properties) \
            and match_source_script(source_config_entry, source, source_properties) \
            and match_source_shell(source_config_entry, source, source_properties):
            
            # A source should only have one match in the extended source processing
            # New: Multiple steps are allowed
            if not allow_multiple_matches and len(result_steps) > 0:
                error = (f"Multiple extended source processing entries found for {source=}: {last_config_entry=}, {source_config_entry=}")
                logging.error(error)
                raise Exception(error)
            
            allow_multiple_matches = source_config_entry.get('allow_multiple_matches', True)
            
            steps: [str] = get_steps_from_current_esp(source_config_entry, source, app_config=app_config, **source_properties)
            
            result_steps.extend(steps)
            last_config_entry = source_config_entry
            logging.debug(f"Extended source processing entry found for {source=}: {last_config_entry=}")
        
    if len(result_steps) == 0:
        return None
            
    return result_steps




def get_steps_from_current_esp(source_config_entry: ExtendedSourceConfig, source: str, app_config, **source_properties) -> list[str]:
    steps: [str|dict] = source_config_entry.get('steps', [])
    new_steps: [str] = []
    
    for step in steps:
        
        # Check if step is a dictionary
        if isinstance(step, dict):
            
            if step.get('use_standard_step', False):
                
                global_steps = get_global_steps(source, app_config=app_config)
                step_properties = step.get('properties', None)
                
                # Inerhit properties from step
                if step_properties:
                    for global_step in global_steps:
                        new_steps.append({'step': global_step, 'properties': step_properties})
                    continue
                
                new_steps.extend(global_steps)
                continue
            
        new_steps.append(step)
    
    return new_steps






def match_source_shell(source_config_entry: ExtendedSourceConfig, source: str, source_properties: {}) -> bool:
    """Process script for extended source commands
    Args:
        source_config_entry (dict): Extended source config entry
        source (str): Source file name
        source_properties (dict): Source properties (TGTRLS, STGMDL, TARGET_LIB, OBJ_NAME etc.)
    Returns:
        bool: True if shell matches
    """
    
    result = False
    
    # No shell defined
    shell = source_config_entry.get('use_shell', None)
    
    if shell is None:
        return True
    
    for key, value in source_properties.items():
        key = f"${{{key}}}"
        if key in shell:
            shell = shell.replace(key, value)
            
    logging.debug(f"Execute shell cmd: {shell}")
    
    try:
        result = subprocess.run(shell, shell=True, check=True, text=True, capture_output=True)
        logging.debug(f"Shell command stdout: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logging.debug(f"Shell command stdout: {e.stdout}")
        logging.debug(f"Shell command stderr: {e.stderr}")
        return False




def match_source_script(source_config_entry: ExtendedSourceConfig, source: str, source_properties: {}) -> bool:
    """Process script for extended source commands
    Args:
        source_config_entry (dict): Extended source config entry
        source (str): Source file name
        source_properties (dict): Source properties (TGTRLS, STGMDL, TARGET_LIB, OBJ_NAME etc.)
    Returns:
        bool: True if script matches
    """
    
    result = False
    
    # No script defined
    script = source_config_entry.get('use_script', None)
    
    if script is None:
        return True

    func = get_script_function(script)

    stdout_orig = sys.stdout
    stdout_new = StringIO()
    sys.stdout = stdout_new
    stderr_orig = sys.stderr
    sys.stderr = stderr_new = StringIO()

    hdl = logging.StreamHandler(stream=stdout_new)
    logging.getLogger().addHandler(hdl)

    try:
        result = func(source, **source_properties)

    except Exception as e:
        print(str(e), file=sys.stderr)
        logging.exception(e, stack_info=True)
        raise e

    stderr_text = stderr_new.getvalue()
    if len(stderr_text) > 0:
        logging.error(stderr_text)

    sys.stdout = stdout_orig
    sys.stderr = stderr_orig
    logging.getLogger().removeHandler(hdl)

    return result


def get_script_function(script: str) -> callable:
    """Get script function
    Args:
        script (str): Script name
    Returns:
        callable: Function to be called
    Raises:
        Exception: If script or function not found
    """
    
    obj = script.split('.')

    if len(obj) != 2:
        raise Exception(f"Script '{script}' has not the correct format: 'filename.function_name' (without '.py' in filename)")

    # Check if script exists
    scripts_path = pathlib.Path(constants.ESP_SCRIPT_FOLDER)
    script_file = scripts_path / f"{obj[0]}.py"
    
    if not script_file.is_file():
        raise Exception(f"Script '{script}' not found in {scripts_path} ({script_file.absolute()})")
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(script_file.stem, script_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, obj[1]):
        return getattr(module, obj[1])
    
    raise Exception(f"Function '{obj[1]}' not found in script '{script}'")
    



def match_source_conditions(source_config_entry: ExtendedSourceConfig, source: str, source_properties: {}) -> bool:
    """Process conditions for extended source commands
    Args:
        source_config_entry (dict): Extended source config entry
        source (str): Source file name
        source_properties (dict): Source properties (TGTRLS, STGMDL, TARGET_LIB, OBJ_NAME etc.)
    Returns:
        bool: True if conditions match
    """

    conditions = {
        'SOURCE_FILE_NAME': match_condition_SOURCE_FILE_NAME,
        'TARGET_LIB': match_condition_TARGET_LIB
    }

    config_conditions = source_config_entry.get('conditions', [])
    logging.debug(f"{len(config_conditions)}")
    if len(config_conditions) == 0:
        return True

    for condition_name, condition_value in config_conditions.items():

        if condition_name not in conditions:
            logging.warning(f"Unknown extended source condition name: {condition_name}, {source=}")
            return False

        # Every condition needs to match
        found = conditions[condition_name](source, condition_value, source_config_entry, source_properties)
        logging.debug(f"Match {condition_name=}, {condition_value=}, {found=}")
        if not found:
            return False

    logging.debug(f"Extended source processing conditions matched for {source=}: {source_config_entry=}")
    return True




def match_condition_SOURCE_FILE_NAME(source:str, condition_value:str, source_config_entry: ExtendedSourceConfig, source_properties: {}) -> bool:

    if source_config_entry['use_regex']:
        return re.search(condition_value, source)

    logging.debug(f"Match {source=}, {condition_value=}: {fnmatch.fnmatch(source, condition_value)}")
    return fnmatch.fnmatch(source, condition_value)





def match_condition_TARGET_LIB(source:str, condition_value:str, source_config_entry: ExtendedSourceConfig, source_properties: {}) -> bool:

    logging.debug(f"Match regex: {source_config_entry['use_regex']}, {source=}, {condition_value=}: {source_properties['TARGET_LIB']=}")
    if source_config_entry['use_regex']:
        return re.search(condition_value, source_properties['TARGET_LIB'])

    return fnmatch.fnmatch(source_properties['TARGET_LIB'], condition_value)



