import logging
import pathlib
import fnmatch
import re, sys
from io import StringIO

from module import obi_constants
from module import files, properties
from typing import TypedDict, List, Union
import subprocess
import json


class FilterDict(TypedDict):
    SOURCE_FILE_NAMES: Union[List[str], None]
    TARGET_LIB: Union[str, None]

class ExtendedSourceConfig(TypedDict):
    steps: List[str|dict]
    use_regex: bool
    use_script: Union[str, None]
    use_shell: Union[str, None]
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

    sources_config: ExtendedSourceConfigFile = properties.get_config(obi_constants.OBIConstants.get("EXTENDED_SOURCE_PROCESS_CONFIG_TOML"))
    logging.debug(f"{sources_config=}")
    if len(sources_config) == 0 or 'extended_source_processing' not in sources_config:
        return None
    
    source_properties: {} = properties.get_source_properties(app_config, source)

    for source_config_entry in sources_config['extended_source_processing']:
        
        logging.debug(f"Extended source processing entry: {source_config_entry=}")
        
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
            
            steps: [str|dict] = get_steps_from_current_esp(source_config_entry, source, app_config=app_config, **source_properties)
            
            result_steps.extend(steps)
            last_config_entry = source_config_entry
            logging.debug(f"Extended source processing entry found for {source=}: {last_config_entry=}")
        
    if len(result_steps) == 0:
        return None
            
    return result_steps




def get_steps_from_current_esp(source_config_entry: ExtendedSourceConfig, source: str, app_config, **source_properties) -> list[str|dict]:
    steps: [str|dict] = source_config_entry.get('steps', [])
    new_steps: [str|dict] = []
    
    logging.debug("get_steps_from_current_esp")
    
    for step in steps:
        
        logging.debug(f"Step: ({type(step)}) {step=}")
        
        # Check if step is a dictionary
        if isinstance(step, str):
            new_steps.append(step)
            continue
        
        if not isinstance(step, dict):
            e = Exception(f"Step '{step}' ({type(step)}) is not a dictionary or a str")
            logging.exception(e, stack_info=True)
            raise e
        
        steps_2_append = []
        if 'step' in step:
            steps_2_append.append({'step': step['step']})
            
        logging.debug(f"{steps_2_append=}")
        if step.get('use_standard_step', False):            
            global_steps = get_global_steps(source, app_config=app_config)
            steps_2_append += [{'step': gs} for gs in global_steps]
    
        for step_2_append in steps_2_append:
            exit_point_script = step.get('exit_point_script', None)
            
            if not exit_point_script:
                new_steps.append({**step, **step_2_append})
                continue
            
            func = get_script_function(exit_point_script)
            parms = get_script_parameter(exit_point_script)
            step_2_append = call_script(func, source=source, **{**step, **{'step': step_2_append}}, **source_properties, **parms)
            
            logging.debug(f"Modified source: {source=}: {step_2_append=}")
            new_steps.append({**step, **step_2_append})

    logging.debug(f"New steps: {new_steps=}")    
    return new_steps






def match_source_shell(source_config_entry: ExtendedSourceConfig, source: str, source_properties: dict) -> bool:
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
    
    if shell is None or len(shell) == 0:
        return True
    
    for key, value in source_properties.items():
        key = f"$({key})"
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




def match_source_script(source_config_entry: ExtendedSourceConfig, source: str, source_properties: dict) -> bool:
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
    
    if script is None or len(script) == 0:
        return True

    func = get_script_function(script)
    parms = get_script_parameter(script)

    result = call_script(func, source=source, **source_properties, **parms)

    return result



def call_script(func: callable, **parms) -> any:
    """Process script
    Args:
        func (callable): Function to be called
        parms (dict): Parameter to be passed to the function
    Returns:
        any: Result of the function
    """
    
    result = False
    
    # No script defined
    
    stdout_orig = sys.stdout
    stdout_new = StringIO()
    sys.stdout = stdout_new
    stderr_orig = sys.stderr
    sys.stderr = stderr_new = StringIO()

    hdl = logging.StreamHandler(stream=stdout_new)
    logging.getLogger().addHandler(hdl)

    try:
        result = func(**parms)

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
    
    # Ignore parameter if exists
    # Format: filename.function_name:parameter
    obj = script.split(':', 1)[0].split('.')

    if len(obj) != 2:
        raise Exception(f"Script '{script}' has not the correct format: 'filename.function_name' (without '.py' in filename)")

    # Check if script exists
    scripts_path = pathlib.Path(obi_constants.OBIConstants.get("ESP_SCRIPT_FOLDER"))
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
    
    
    
def get_script_parameter(script: str) -> dict:
    """Get script parameter
    Args:
        script (str): Script name
    Returns:
        {}: Dictionary with parameters
    """
    
    # Ignore parameter if exists
    # Format: filename.function_name:parameter
    obj = script.split(':', 1)
    
    if len(obj) == 2:
        try:
            return json.loads(obj[1])
        except json.JSONDecodeError as e:
            logging.exception(e, stack_info=True)
            raise Exception(f"Script parameter '{obj[1]}' is not a valid JSON string: {e}")
    
    return {}



def match_source_conditions(source_config_entry: ExtendedSourceConfig, source: str, source_properties: dict) -> bool:
    """Process conditions for extended source commands
    Args:
        source_config_entry (dict): Extended source config entry
        source (str): Source file name
        source_properties (dict): Source properties (TGTRLS, STGMDL, TARGET_LIB, OBJ_NAME etc.)
    Returns:
        bool: True if conditions match
    """

    config_conditions = source_config_entry.get('conditions', [])
    logging.debug(f"{len(config_conditions)}")
    if len(config_conditions) == 0:
        return True

    for condition_name, condition_value in config_conditions.items():

        if condition_name not in source_properties.keys():
            logging.warning(f"Unknown extended source condition name: {condition_name}, {source=}")
            return False
        found = False

        # Every condition needs to match
        if isinstance(condition_value, str):
            found = match_condition_by_value(source, condition_name, condition_value, source_config_entry, source_properties)
        if isinstance(condition_value, list):
            found = match_condition_by_list(source, condition_name, condition_value, source_config_entry, source_properties)
        logging.debug(f"Match {condition_name=}, {condition_value=}, {found=}")
        if not found:
            return False

    logging.debug(f"Extended source processing conditions matched for {source=}: {source_config_entry=}")
    return True




def match_condition_by_list(source:str, condition_key: str, condition_values: list[str], source_config_entry: ExtendedSourceConfig, source_properties: dict) -> bool:

    for condition_value in condition_values:

        if source_config_entry['use_regex']:
            if re.search(condition_value, source):
                return True

        logging.debug(f"Match {source=}, {condition_value=}: {fnmatch.fnmatch(source, condition_value)}")
        if fnmatch.fnmatch(source, condition_value):
            return True

    return False




def match_condition_by_value(source:str, condition_key: str, condition_value:str, source_config_entry: ExtendedSourceConfig, source_properties: dict) -> bool:

    logging.debug(f"Match regex: {source_config_entry['use_regex']}, {source=}, {condition_value=}: {source_properties[condition_key]=}")
    if source_config_entry['use_regex']:
        return re.search(condition_value, source_properties[condition_key])

    return fnmatch.fnmatch(source_properties[condition_key], condition_value)


