
from etc import constants
from typing import Optional



class OBIConstants:

    JOBLOG = '.obi/log/joblog.txt'
    OBI_BACKEND_VERSION = 1

    @staticmethod
    def get(key: str, default: Optional[str]=None) -> str:
        if hasattr(constants, key):
            return getattr(constants, key)
        return getattr(OBIConstants, key, default) or ''
