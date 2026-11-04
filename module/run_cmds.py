import logging
import subprocess
import threading
import uuid
import concurrent.futures
from contextlib import suppress
from datetime import datetime

from module import properties
from module import obi_constants
from module import toml_tools
from module import files
import os




default_app_config = properties.get_app_properties()



class BuildCancelled(Exception):
  pass



def no_event(event_type, **data):
  pass



def all_cmds_succeeded(cmds:[]) -> bool:
  for cmd_item in cmds:
    if 'status' not in cmd_item or cmd_item['status'] != 'success':
      return False
  return True



def get_max_parallel_builds(app_config=default_app_config) -> int:
  """Max number of sources to build in parallel (config: general.max-parallel-builds). Defaults to 1 (sequential)"""

  try:
    max_parallel_builds = int(app_config['general'].get('max-parallel-builds', 1))
  except (TypeError, ValueError) as e:
    logging.warning(f"Invalid 'max-parallel-builds' config value, falling back to 1: {e}")
    max_parallel_builds = 1

  return max(max_parallel_builds, 1)



def run_build_object_list(target_tree, save_update_2_json_file=None, app_config=default_app_config, on_event=None, cancel=None):
  """Run commands for all source entries

  Sources within a level are built in parallel (up to `general.max-parallel-builds` at a time), because they
  don't depend on each other. Levels are built in sequence, because a level can depend on a previous one.
  Commands of a single source are always run in sequence.

  After a failure no further source gets started. Sources which are already running will be finished.

  Args:
      target_tree (dict): List of all sources and the related commands
      save_update_2_json_file (str, optional): If given, every change will update the json file. Defaults to None.
      app_config (properties, optional): Application config file
      on_event (callable, optional): Called with (event_type, **data) for each change, under the write lock (processing service)
      cancel (threading.Event, optional): If set, no further level, source or command is started

  Raises:
      Exception: If a command fails an exception will be thrown
      BuildCancelled: If `cancel` has been set
  """

  max_parallel_builds = get_max_parallel_builds(app_config)
  write_lock = threading.Lock()   # Protects target_tree (changes + writing it) and the compiled-object-list
  stop_builds = threading.Event()
  on_event = on_event or no_event

  def stop_on_error(future):
    if future.exception() is not None:
      stop_builds.set()

  # Level 1-n
  for level_item in target_tree['compiles']:

    if cancel is not None and cancel.is_set():
      raise BuildCancelled(f"Build cancelled before level {level_item['level']}")

    logging.info(f"Run {level_item['level']=}: {len(level_item['sources'])} entries ({max_parallel_builds=})")
    on_event('level_started', level=level_item['level'], sources=len(level_item['sources']))

    # Each entry in a level list, up to `max_parallel_builds` in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel_builds) as executor:
      futures = []
      for level_list_entry in level_item['sources']:
        future = executor.submit(run_source_build, level_list_entry, target_tree, save_update_2_json_file, app_config, write_lock, stop_builds,
                                 on_event, cancel, level_item['level'])
        future.add_done_callback(stop_on_error)
        futures.append(future)

      errors = [future.exception() for future in concurrent.futures.as_completed(futures) if future.exception() is not None]

    # Only move on to the next level once the whole level is done
    if errors:
      raise errors[0]



def run_source_build(level_list_entry, target_tree, save_update_2_json_file, app_config, write_lock, stop_builds,
                     on_event=no_event, cancel=None, level=None):
  """Run all commands of a single source entry, in sequence

  Args:
      level_list_entry (dict): Source entry (source, cmds, ...). Modified in place
      target_tree (dict): Whole compile list, shared across sources. Only change or write it with `write_lock`
      save_update_2_json_file (str): If given, every change will update the json file
      app_config (properties): Application config file
      write_lock (threading.Lock): Protects target_tree and the compiled-object-list
      stop_builds (threading.Event): If set, a previous source failed and this source won't be started
      on_event (callable): Called with (event_type, **data) for each change, under `write_lock`
      cancel (threading.Event, optional): If set, this source (or its next command) won't be started
      level (int, optional): Level of the source, for the events

  Raises:
      Exception: If a command fails an exception will be thrown
      BuildCancelled: If `cancel` has been set before a command of this source
  """

  src_name = level_list_entry['source']
  cmds = level_list_entry['cmds']

  def cancelled():
    return cancel is not None and cancel.is_set()

  if stop_builds.is_set():
    logging.info(f"Source {src_name} not started because of a previous error")
    return

  if cancelled():
    logging.info(f"Source {src_name} not started because the build has been cancelled")
    return

  with write_lock:
    level_list_entry['absolute_path'] = os.path.abspath(f"{app_config['general']['source-dir']}/{src_name}")

  logging.info(src_name)

  if 'ignore' in level_list_entry and level_list_entry['ignore']:
    logging.info(f"Source {src_name} ignored")
    return

  # Skip this if object was successfully build
  if all_cmds_succeeded(level_list_entry['cmds']):
    return

  with write_lock:
    level_list_entry['status'] = 'in process'
    on_event('source_started', level=level, source=src_name)

  status = 'failed'

  try:
    # each source can have multiple commands, always run in sequence
    for cmd_index, cmd_item in enumerate(cmds):

      if 'ignore' in cmd_item and cmd_item['ignore']:
        logging.info(f"Source {src_name} ignored cmd {cmd_item['cmd']}")
        continue

      if cancelled():
        with write_lock:
          level_list_entry['status'] = 'failed'
          files.writeJson(target_tree, save_update_2_json_file)
        raise BuildCancelled(f"Build of '{src_name}' cancelled")

      with write_lock:
        cmd_item['updated'] = datetime.now().isoformat()
        cmd_item['status'] = 'in process'
        target_tree['timestamp'] = str(datetime.now())
        files.writeJson(target_tree, save_update_2_json_file)
        on_event('cmd_started', level=level, source=src_name, cmd_index=cmd_index, cmd=cmd_item['cmd'])

      result = run_pase_cmd(cmd_item['cmd'], app_config)
      cmd_failed = result['exit-code'] != 0 or result['stderr'] != ''

      with write_lock:
        cmd_item['updated'] = datetime.now().isoformat()
        cmd_item['status'] = 'failed' if cmd_failed else 'success'
        cmd_item.update(result)
        if cmd_failed:
          level_list_entry['status'] = 'failed'
        target_tree['timestamp'] = str(datetime.now())
        files.writeJson(target_tree, save_update_2_json_file)
        on_event('cmd_finished', level=level, source=src_name, cmd_index=cmd_index, cmd=cmd_item['cmd'],
                 status=cmd_item['status'], updated=cmd_item['updated'], **result)

      if cmd_failed:
        e = Exception(f"Error for '{src_name}': {result['stderr']}")
        logging.error(f"{result=}")
        logging.exception(e)
        raise e

    file_hash = files.get_file_hash(f"{app_config['general']['source-dir']}/{src_name}")

    with write_lock:
      level_list_entry['status'] = 'success'
      level_list_entry['hash'] = file_hash
      files.writeJson(target_tree, save_update_2_json_file)
      files.update_compiles_object_list(src_name, app_config)

    status = 'success'

  finally:
    with write_lock:
      on_event('source_finished', level=level, source=src_name, status=status,
               hash=level_list_entry.get('hash') if status == 'success' else None)




def run_pase_cmd(cmd, app_config=default_app_config):

  # Unique joblog file per call, so parallel commands don't overwrite each other's joblog
  joblog_file = f"{obi_constants.OBIConstants.get('JOBLOG')}.{uuid.uuid4().hex}"
  # Keep the exit code of the cmd, otherwise it's the one of the joblog cmd
  cmd += f'; obi_exit_code=$?; cl -v "dspjoblog" > {joblog_file}; exit $obi_exit_code'
  logging.debug(f"Run PASE cmd: {cmd}")

  s=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, check=False, executable='/usr/bin/bash')

  encoding = app_config['general'].get('console-output-encoding', 'utf-8')
  stdout = str(s.stdout, encoding)
  stderr = str(s.stderr, encoding)

  joblog = ''
  if os.path.isfile(joblog_file):
    joblog = files.readFile(joblog_file)
    with suppress(OSError):
      os.remove(joblog_file)

  # exit-code: 0 = OK
  return {"exit-code": s.returncode, "stdout": stdout, "stderr": stderr, "joblog": joblog}

