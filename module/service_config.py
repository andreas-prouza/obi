"""
Directory and settings of the processing service.

Each user has their own service. Everything it needs is in its directory (default `~/.obi-service`).
No import of project modules here: the service runs without a project.

See docs/processing-service.md
"""
import logging
import os

import toml



DIR_ENV = 'OBI_SERVICE_DIR'
DEFAULT_DIR = '~/.obi-service'

OBI_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# key: (default, minimum, type)
SETTINGS = {
  'max-parallel-jobs': (2, 1, int),
  'idle-timeout': (1800, 0, float),
  'poll-interval': (5, 0.01, float),
  'heartbeat-interval': (10, 0.01, float),
  'heartbeat-timeout': (60, 0.01, float),
  'cancel-timeout': (30, 0, float),
  'keep-jobs-days': (7, 0, float),
}



class ServiceDirError(Exception):
  pass



def get_dir() -> str:
  return os.path.abspath(os.path.expanduser(os.environ.get(DIR_ENV) or DEFAULT_DIR))



def get_path(*parts: str) -> str:
  return os.path.join(get_dir(), *parts)



def db_file() -> str:
  return get_path('jobs.sqlite')

def socket_file() -> str:
  return get_path('service.sock')

def lock_file() -> str:
  return get_path('service.lock')

def pid_file() -> str:
  return get_path('service.pid')

def settings_file() -> str:
  return get_path('settings.toml')

def log_dir() -> str:
  return get_path('log')

def job_dir(job_id: int) -> str:
  return get_path('jobs', str(int(job_id)))



def ensure_dir() -> str:
  """
  Creates the service directory if needed and checks that only the user can access it.
  Job outputs contain joblogs and commands, and the queue decides what gets run.

  Raises:
      ServiceDirError: The directory belongs to another user or others have access to it
  """

  directory = get_dir()

  if not os.path.exists(directory):
    os.makedirs(directory, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)

  stat = os.stat(directory)

  if not os.path.isdir(directory):
    raise ServiceDirError(f"Service directory {directory} is not a directory")

  if hasattr(os, 'getuid') and stat.st_uid != os.getuid():
    raise ServiceDirError(f"Service directory {directory} belongs to another user")

  if stat.st_mode & 0o077:
    raise ServiceDirError(f"Others have access to the service directory {directory}. Allow access only for yourself: chmod 700 {directory}")

  return directory



def get_settings() -> dict:
  """Settings of the user (settings.toml in the service directory). Invalid values fall back to the default."""

  settings = {key: default for key, (default, _, _) in SETTINGS.items()}
  file = settings_file()

  if not os.path.isfile(file):
    return settings

  try:
    with open(file, 'r', encoding='utf-8') as f:
      user_settings = toml.load(f)
  except Exception as e:
    logging.error(f"Settings {file} can't be read, using the defaults: {e}")
    return settings

  for key, value in user_settings.items():

    if key not in SETTINGS:
      logging.warning(f"Unknown setting '{key}' in {file}")
      continue

    default, minimum, value_type = SETTINGS[key]
    try:
      if isinstance(value, bool):
        raise ValueError('no number')
      value = value_type(value)
      if value < minimum:
        raise ValueError(f'less than {minimum}')
      settings[key] = value
    except (TypeError, ValueError) as e:
      logging.warning(f"Invalid value {value!r} of '{key}' in {file}, using {default}: {e}")

  return settings
