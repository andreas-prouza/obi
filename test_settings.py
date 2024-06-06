import logging
from etc import logger_config

from etc import constants
from module import properties


config = properties.get_config(constants.CONFIG_TOML)

out1 = properties.get_source_properties(config, "prouzalib/qrpglesrc/test4.rpgle.pgm")

logging.debug(f"{out1=}")