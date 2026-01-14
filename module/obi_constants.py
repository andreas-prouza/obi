
from etc import constants
from typing import Optional
import os
import json
import logging



class OBIConstants:

    JOBLOG = '.obi/log/joblog.txt'
    OBI_BACKEND_VERSION = 3

    @staticmethod
    def get_current_user_config_file() -> str:
        settings_file = OBIConstants.get_constant_value('WORKSPACE_SETTINGS_JSON')
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                profile = data.get('current_profile')
                if profile:
                    return f".obi/etc/{profile}"
            except (json.JSONDecodeError, IOError):
                # Fall through to default if file is invalid or unreadable
                pass

        return OBIConstants.get_constant_value('CONFIG_USER_TOML')



    @staticmethod
    def get(key: str, default: Optional[str]=None) -> str:

        logging.debug(f"Get OBI constant: {key}")

        if key == 'CONFIG_USER_TOML':
            logging.debug(f"Original: {getattr(constants, key)}; new: {OBIConstants.get_current_user_config_file()}")
            return OBIConstants.get_current_user_config_file()
        
        return OBIConstants.get_constant_value(key, default)
    


    @staticmethod
    def get_constant_value(key: str, default: Optional[str]=None) -> str:

        if hasattr(constants, key):
            return getattr(constants, key)
        return getattr(OBIConstants, key, default) or ''
