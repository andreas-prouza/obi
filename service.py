#################################################################
# Processing service
#
#   Runs builds independent of the client. One service per user.
#   `main.py -a submit` starts it by itself, so this is only needed to look at it or to stop it.
#
#   <obi>/venv/bin/python <obi>/service.py start | stop | restart | status
#
#   See docs/processing-service.md
#################################################################

import argparse
import logging
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler


sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from module import job_queue
from module import processing_service
from module import service_config


parser = argparse.ArgumentParser(
  prog='OBI processing service',
  description='Runs builds independent of the client. See docs/processing-service.md'
)
parser.add_argument('command', choices=['start', 'stop', 'restart', 'status', 'run'],
                    help='run: run in the foreground (used by start)')



def setup_logging():

  os.makedirs(service_config.log_dir(), exist_ok=True)
  handler = RotatingFileHandler(os.path.join(service_config.log_dir(), 'service.log'), maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
  handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s - %(filename)s[%(lineno)d]: %(message)s'))
  logging.basicConfig(level=logging.INFO, handlers=[handler])



def run() -> int:

  setup_logging()

  try:
    processing_service.Service().run_forever()
  except processing_service.ServiceAlreadyRunningError as e:
    logging.info(e)
    print(e, file=sys.stderr)
    return 0

  return 0



def start() -> int:

  if processing_service.is_running():
    print(f"Processing service is already running (pid {processing_service.get_pid()})")
    return 0

  state = processing_service.ensure_running()
  status()

  if state == 'not running':
    print(f"See {service_config.log_dir()}", file=sys.stderr)
    return 1

  return 0



def stop(wait: float = 10) -> int:

  if not processing_service.is_running():
    print("Processing service is not running")
    return 0

  pid = processing_service.get_pid()
  if pid is None:
    print(f"Processing service is running, but its pid is unknown ({service_config.pid_file()})", file=sys.stderr)
    return 1

  print(f"Stop processing service (pid {pid}). Running jobs are not stopped, they finish on their own.")
  os.kill(pid, signal.SIGTERM)

  deadline = time.monotonic() + wait
  while processing_service.is_running():
    if time.monotonic() >= deadline:
      print(f"Processing service (pid {pid}) didn't stop within {wait} seconds", file=sys.stderr)
      return 1
    time.sleep(0.1)

  print("Processing service stopped")
  return 0



def status() -> int:

  if processing_service.is_running():
    print(f"Processing service is running (pid {processing_service.get_pid()})")
  else:
    print("Processing service is not running")

  print(f"Directory: {service_config.get_dir()}")

  if os.path.exists(service_config.db_file()):
    jobs = job_queue.get_jobs(job_queue.OPEN_STATUSES)
    print(f"Jobs: {len([job for job in jobs if job['status'] == job_queue.RUNNING])} running, {len([job for job in jobs if job['status'] == job_queue.QUEUED])} queued")
    for job in reversed(jobs):
      print(f"  {job['id']:>6}  {job['status']:<8}  {job['compile_list']}")

  return 0



if __name__ == '__main__':

  args = parser.parse_args()

  try:
    service_config.ensure_dir()

    if args.command == 'run':
      sys.exit(run())
    if args.command == 'start':
      sys.exit(start())
    if args.command == 'stop':
      sys.exit(stop())
    if args.command == 'restart':
      sys.exit(stop() or start())
    if args.command == 'status':
      sys.exit(status())

  except service_config.ServiceDirError as e:
    print(e, file=sys.stderr)
    sys.exit(1)
