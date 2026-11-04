"""
The job process: `main.py -a run --job <id>`, started by the processing service.

It's the same build as `run`, plus:
  * the job's status at its start and its end
  * a heartbeat, so the service knows the process still exists
  * an event for each change, for the client (`watch`)
  * cancel: SIGTERM (or the flag in the queue) stops the running commands and starts no further source

See docs/processing-service.md
"""
import logging
import os
import signal
import threading

from module import job_events
from module import job_queue
from module import service_config



def all_cmds_succeeded(cmds: list) -> bool:
  # Same as run_cmds.all_cmds_succeeded: a source whose commands all succeeded is skipped
  return all(cmd.get('status') == 'success' for cmd in cmds)



def to_build(entry: dict) -> bool:
  """Sources which run_cmds builds"""
  return not entry.get('ignore') and not all_cmds_succeeded(entry.get('cmds', []))



def is_built(entry: dict) -> bool:
  return bool(entry.get('ignore')) or entry.get('status') == 'success' or all_cmds_succeeded(entry.get('cmds', []))



class JobRun:
  """
  Context of a running job

    with JobRun(job_id, project, compile_list) as job:
      job.build_started(target_tree)
      run_cmds.run_build_object_list(..., on_event=job.on_event, cancel=job.cancel)
      job.build_finished(target_tree)
  """

  def __init__(self, job_id: int, project: str, compile_list: str):

    self.job_id = job_id
    self.project = os.path.realpath(project)
    self.compile_list = os.path.abspath(compile_list)
    self.settings = service_config.get_settings()

    self.cancel = threading.Event()
    self.progress = {'sources': 0, 'sources_done': 0, 'sources_failed': 0, 'cmds': 0, 'cmds_done': 0}
    self.build_status = None
    self.events: job_events.EventWriter|None = None

    self.lock = threading.Lock()
    self.stop_heartbeat = threading.Event()
    self.heartbeat: threading.Thread|None = None
    self.previous_handlers = {}



  def __enter__(self):

    job = job_queue.get_job(self.job_id)

    if job is None:
      raise Exception(f"Job {self.job_id} not found")

    if job['status'] != job_queue.RUNNING:
      raise Exception(f"Job {self.job_id} is {job['status']}, it can't be run")

    # Only the process which the service started for this job
    if job['pid'] is not None and job['pid'] != os.getpid():
      raise Exception(f"Job {self.job_id} is run by process {job['pid']}")

    if os.path.realpath(job['project']) != self.project or job['compile_list'] != self.compile_list:
      error = f"Job {self.job_id} is for {job['compile_list']}, not for {self.compile_list}"
      job_queue.end_job(self.job_id, job_queue.FAILED, error=error, from_statuses=(job_queue.RUNNING,))
      raise Exception(error)

    job_queue.set_pid(self.job_id, os.getpid())
    job_queue.touch(self.job_id)
    self.events = job_events.EventWriter(self.job_id)

    if job['cancel_requested']:
      self.cancel.set()

    self.previous_handlers = {
      signal.SIGTERM: signal.signal(signal.SIGTERM, self.on_signal),
      signal.SIGHUP: signal.signal(signal.SIGHUP, signal.SIG_IGN),
    }

    self.heartbeat = threading.Thread(target=self.send_heartbeats, daemon=True)
    self.heartbeat.start()

    logging.info(f"Job {self.job_id} started: {self.compile_list}")
    return self



  def __exit__(self, exc_type, exc, tb):

    self.stop_heartbeat.set()
    self.heartbeat.join()

    for sig, handler in self.previous_handlers.items():
      signal.signal(sig, handler)

    build_status = None
    error = None

    if exc is not None:
      status = job_queue.FAILED
      error = str(exc) or type(exc).__name__
    elif self.cancel.is_set():
      status = job_queue.CANCELLED
    else:
      status = job_queue.FINISHED
      build_status = self.build_status

    with self.lock:
      progress = dict(self.progress)

    if not job_queue.end_job(self.job_id, status, build_status, error, progress, from_statuses=(job_queue.RUNNING,)):
      logging.warning(f"Job {self.job_id} had already been ended by someone else")

    logging.info(f"Job {self.job_id} ended: {status=}, {build_status=}, {error=}")
    # An error is passed on, so main.py writes it into status.json
    return False



  def on_signal(self, signum, frame) -> None:
    # The commands got the signal too (same process group) and end.
    # This process finishes the build: no further source, summary, final status.
    logging.warning(f"Job {self.job_id}: signal {signum} received, cancel the build")
    self.cancel.set()



  def request_cancel(self, reason: str) -> None:

    if self.cancel.is_set():
      return

    logging.warning(f"Job {self.job_id}: {reason}, cancel the build")
    self.cancel.set()

    # Stop the running commands. Only if this process is the leader of its own process group,
    # which it is when the service has started it.
    if os.getpgrp() == os.getpid():
      os.killpg(os.getpid(), signal.SIGTERM)



  def send_heartbeats(self) -> None:

    while not self.stop_heartbeat.wait(self.settings['heartbeat-interval']):
      try:
        with self.lock:
          progress = dict(self.progress)

        job = job_queue.touch(self.job_id, progress)

        if job is None or job['status'] != job_queue.RUNNING:
          # E.g. no heartbeat for too long: the service has given it up
          self.request_cancel(f"job is {job['status'] if job else 'deleted'}")
        elif job['cancel_requested']:
          self.request_cancel("cancel requested")

      except Exception as e:
        logging.warning(f"Heartbeat of job {self.job_id} failed: {e}")



  def emit(self, event_type: str, **data) -> None:
    """A failed event must not stop the build"""

    try:
      self.events.emit(event_type, **data)
    except Exception as e:
      logging.exception(e)



  def build_started(self, target_tree: dict) -> None:

    with self.lock:
      for level in target_tree.get('compiles', []):
        for entry in level.get('sources', []):
          if to_build(entry):
            self.progress['sources'] += 1
            self.progress['cmds'] += len([cmd for cmd in entry.get('cmds', []) if not cmd.get('ignore')])
      progress = dict(self.progress)

    self.emit('started', progress=progress)



  def on_event(self, event_type: str, **data) -> None:
    """Callback of run_cmds. Called under its write lock, so the events keep their order."""

    with self.lock:
      if event_type == 'cmd_finished':
        self.progress['cmds_done'] += 1
      elif event_type == 'source_finished':
        self.progress['sources_done'] += 1
        if data.get('status') != 'success':
          self.progress['sources_failed'] += 1

      if event_type in ('cmd_finished', 'source_finished'):
        data['progress'] = dict(self.progress)

    self.emit(event_type, **data)



  def build_finished(self, target_tree: dict) -> None:

    entries = [entry for level in target_tree.get('compiles', []) for entry in level.get('sources', [])]
    self.build_status = 'success' if all(is_built(entry) for entry in entries) else 'failed'
