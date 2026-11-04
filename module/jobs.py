"""
Jobs of the processing service, for clients: submit, list, follow the events, cancel.

All functions return JSON-serializable data. The command line (main.py) is a thin layer on top,
the planned Web GUI can use the same functions.

See docs/processing-service.md
"""
import logging
import os
import signal
import time
from typing import Iterator

from module import job_events
from module import job_queue
from module import processing_service
from module import service_config



class JobError(Exception):
  pass



def submit(project: str, compile_list: str) -> dict:
  """
  Adds the build of a build list to the queue and makes sure the service runs.

  Returns:
      dict: `job`, `service` ('running', 'started', 'not running') and a `warning` if the service couldn't be started
  """

  project = os.path.realpath(project)
  compile_list = os.path.abspath(compile_list)

  if not os.path.isdir(os.path.join(project, '.obi')):
    raise JobError(f"{project} is not an OBI project (missing .obi)")

  if not os.path.isfile(compile_list):
    raise JobError(f"Build list {compile_list} doesn't exist. Create it first")

  try:
    job = job_queue.add_job(project, compile_list)
  except job_queue.JobConflictError as e:
    raise JobError(str(e)) from e

  logging.info(f"Job {job['id']} queued: {compile_list}")

  service = processing_service.ensure_running()
  result = {'job': job, 'service': service}

  if service == 'not running':
    result['warning'] = f"The processing service could not be started. The job waits in the queue. See {service_config.log_dir()}"
    logging.warning(result['warning'])

  return result



def get_job(job_id: int) -> dict|None:
  return job_queue.get_job(job_id)



def list_jobs(project: str|None = None, limit: int = 50) -> list[dict]:
  return job_queue.get_jobs(project=os.path.realpath(project) if project else None, limit=limit)



def follow(job_id: int, since: int = 0, poll_interval: float = 0.5, status_interval: float = 2) -> Iterator[dict]:
  """
  Events of a job after `since`, as they happen, until the job has ended (event `ended`).

  Args:
      status_interval (float): Seconds between two looks into the queue, if no event came. Ends the loop for an ended job
                               whose `ended` was already sent (since >= its seq)
  """

  if job_queue.get_job(job_id) is None:
    raise JobError(f"Job {job_id} not found")

  reader = job_events.EventReader(job_id, since)
  last_status_check = 0.0

  while True:

    events = reader.read_new()
    for event in events:
      yield event
      if event['type'] == 'ended':
        return

    if events or time.monotonic() - last_status_check < status_interval:
      time.sleep(poll_interval)
      continue

    last_status_check = time.monotonic()
    job = job_queue.get_job(job_id)

    if job is None:
      raise JobError(f"Job {job_id} not found (deleted)")

    if job['status'] in job_queue.ENDED_STATUSES:
      # Written between the last read and the look into the queue
      for event in reader.read_new():
        yield event
      return

    time.sleep(poll_interval)



def cancel(job_id: int) -> dict:
  """
  A queued job is removed from the queue. A running job is stopped: its running commands end,
  no further source is started. Its process sets the status `cancelled`.
  """

  job = job_queue.get_job(job_id)
  if job is None:
    raise JobError(f"Job {job_id} not found")

  if job['status'] in job_queue.ENDED_STATUSES:
    return job

  if job_queue.end_job(job_id, job_queue.CANCELLED, from_statuses=(job_queue.QUEUED,)):
    logging.info(f"Queued job {job_id} cancelled")
    return job_queue.get_job(job_id)

  # Running (or taken from the queue just now): the job process looks at it with each heartbeat,
  # the signal makes it immediate. The service kills it after cancel-timeout.
  job = job_queue.request_cancel(job_id)
  if job['status'] == job_queue.RUNNING:
    processing_service.signal_job(job, signal.SIGTERM)
    logging.info(f"Cancel of running job {job_id} requested")

  return job_queue.get_job(job_id)
