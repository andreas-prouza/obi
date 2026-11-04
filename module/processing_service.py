"""
Processing service

Runs builds independent of the client, so a build keeps running if the SSH connection ends.

  client                                       processing service (service.py)

  main.py -a submit
    job in the queue (queued)
    ensure_running(), notify()  -- wake-up -->   Service.run_once()
                                                   claims the job (running)
                                                   starts `main.py -a run --job <id>` in its own session
  main.py -a watch                               the job process writes its events and heartbeat
    reads the events of the job

One service per user. The database is the only interface. The wake-up only avoids waiting for the next look into the queue.
No import of project modules here: the service runs without a project.

See docs/processing-service.md
"""
import errno
import fcntl
import logging
import os
import select
import signal
import socket
import subprocess
import sys
import time

from module import job_queue
from module import service_config



MAIN_PY = os.path.join(service_config.OBI_DIR, 'main.py')
SERVICE_PY = os.path.join(service_config.OBI_DIR, 'service.py')

# Limit of the path of a unix socket (104 on some systems, incl. the terminating 0)
MAX_SOCKET_PATH = 100

# Seconds between two clean-ups of ended jobs
CLEANUP_INTERVAL = 3600



class ServiceAlreadyRunningError(Exception):
  pass



def notify() -> bool:
  """
  Wakes up the service, so it looks into the queue immediately.

  Returns:
      bool: False if the service is not running
  """

  try:
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
      s.setblocking(False)
      s.sendto(b'1', service_config.socket_file())

  except BlockingIOError:
    # It's listening, but has not processed the previous wake-ups yet
    return True

  except OSError as e:
    logging.debug(f"Processing service is not listening on {service_config.socket_file()}: {e}")
    return False

  return True



def is_running() -> bool:
  """
  The service holds the lock as long as it runs.
  Don't call it in the service itself: closing the file would release its lock.
  """

  lock_file = service_config.lock_file()
  if not os.path.exists(lock_file):
    return False

  fd = os.open(lock_file, os.O_RDWR)
  try:
    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.lockf(fd, fcntl.LOCK_UN)
    return False
  except OSError as e:
    if e.errno in (errno.EACCES, errno.EAGAIN):
      return True
    raise
  finally:
    os.close(fd)



def get_pid() -> int|None:

  try:
    with open(service_config.pid_file(), 'r') as f:
      return int(f.read().strip())
  except (OSError, ValueError):
    return None



def start_detached() -> subprocess.Popen:
  """Starts the service in its own session. It keeps running after the caller (e.g. the SSH session) has ended."""

  service_config.ensure_dir()
  os.makedirs(service_config.log_dir(), exist_ok=True)

  with open(os.path.join(service_config.log_dir(), 'service-output.log'), 'ab') as output:
    return subprocess.Popen(
      [sys.executable, '-X', 'utf8', SERVICE_PY, 'run'],
      cwd=service_config.get_dir(), stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
      start_new_session=True
    )



def ensure_running(wait: float = 10) -> str:
  """
  Starts the service if it isn't running and wakes it up. Call it after the job has been added to the queue:
  a service which is ending looks into the queue after it released its lock (see Service.check_idle).

  Returns:
      str: 'running' (was already running), 'started' or 'not running' (couldn't be started)
  """

  if is_running():
    notify()
    return 'running'

  process = start_detached()
  deadline = time.monotonic() + wait

  while time.monotonic() < deadline:
    time.sleep(0.05)
    if is_running():
      notify()
      return 'started'
    # E.g. the service directory isn't safe. Or another one has been started at the same time.
    if process.poll() is not None:
      return 'running' if is_running() else 'not running'

  return 'not running'



def has_exited(process: subprocess.Popen) -> bool:
  """Whether a child has ended, without reaping it (where possible), so its pid stays reserved"""

  if not hasattr(os, 'waitid'):
    return process.poll() is not None

  try:
    return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None
  except ChildProcessError:
    # Already reaped
    return True



def process_exists(pid: int) -> bool:

  try:
    os.kill(pid, 0)
  except ProcessLookupError:
    return False
  except PermissionError:
    # Belongs to another user, so it's not the job process anymore
    return False

  return True



def signal_job(job: dict, sig: int, heartbeat_timeout: float|None = None) -> bool:
  """
  Sends a signal to the process group of a running job (the job process, its commands and their children).
  Only if the heartbeat is current, so a pid which is used by another process meanwhile is never hit.
  """

  if heartbeat_timeout is None:
    heartbeat_timeout = service_config.get_settings()['heartbeat-timeout']

  pid = job.get('pid')
  heartbeat = job.get('heartbeat')

  if pid is None or heartbeat is None or time.time() - heartbeat > heartbeat_timeout:
    return False

  try:
    # The job process is the leader of its own process group (start_new_session)
    if os.getpgid(pid) != pid:
      return False
    os.killpg(pid, sig)
  except (ProcessLookupError, PermissionError):
    return False

  logging.info(f"Signal {sig} sent to job {job['id']} (process group {pid})")
  return True




class Service:
  """
  The processing service

  Waits for jobs in the queue and starts each of them as its own process (`main.py -a run --job <id>`).
  It has only one thread and keeps no database connection open.
  """

  def __init__(self, settings: dict|None = None):

    self.settings = settings or service_config.get_settings()
    self.socket: socket.socket|None = None
    self.lock_fd: int|None = None
    # {job id: process} of the jobs started by this service
    self.children: dict[int, subprocess.Popen] = {}
    self.stop_requested = False
    self.last_active = time.monotonic()
    self.last_cleanup = 0.0



  def start(self, lock_wait: float = 10) -> None:

    service_config.ensure_dir()
    self.acquire_lock(lock_wait)
    self.open_socket()
    self.write_pid_file()

    logging.info(f"Processing service started: pid {os.getpid()}, {service_config.get_dir()=}, {self.settings=}")



  def acquire_lock(self, wait: float) -> None:
    """
    Only one service per user. The lock also tells the clients that the service is running.
    Waits a moment for a service which is ending.
    """

    fd = os.open(service_config.lock_file(), os.O_RDWR | os.O_CREAT, 0o600)
    deadline = time.monotonic() + wait

    while True:
      try:
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.lock_fd = fd
        return
      except OSError as e:
        if e.errno not in (errno.EACCES, errno.EAGAIN):
          os.close(fd)
          raise
        if time.monotonic() >= deadline:
          os.close(fd)
          raise ServiceAlreadyRunningError(f"Processing service is already running (pid {get_pid()}, {service_config.get_dir()})")
        time.sleep(0.2)



  def release_lock(self) -> None:

    if self.lock_fd is not None:
      os.close(self.lock_fd)
      self.lock_fd = None



  def open_socket(self) -> None:
    """The wake-up. Without it (path too long), the service only looks into the queue every poll-interval."""

    path = service_config.socket_file()
    if len(path.encode()) > MAX_SOCKET_PATH:
      logging.warning(f"Path of the socket is too long ({path}): no wake-up, the queue is checked every {self.settings['poll-interval']} seconds. "
                      f"Use a shorter service directory ({service_config.DIR_ENV}) to avoid it")
      return

    # Left over if the service has been killed. Safe to remove: this service holds the lock.
    if os.path.exists(path):
      os.remove(path)

    self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    self.socket.bind(path)
    self.socket.setblocking(False)
    os.chmod(path, 0o600)



  def close_socket(self) -> None:
    """Removes the socket file only if it's the own one: after the lock is released, it may belong to a new service"""

    if self.socket is None:
      return

    self.socket.close()
    self.socket = None

    if os.path.exists(service_config.socket_file()):
      os.remove(service_config.socket_file())



  def write_pid_file(self) -> None:

    with open(service_config.pid_file(), 'w') as f:
      f.write(str(os.getpid()))



  def remove_pid_file(self) -> None:
    """Only while holding the lock: afterwards it may belong to a new service"""

    if self.lock_fd is not None and os.path.exists(service_config.pid_file()):
      os.remove(service_config.pid_file())



  def stop(self) -> None:
    """Stops the service. Running jobs are not affected: they have their own process."""

    self.close_socket()
    self.remove_pid_file()
    self.release_lock()

    running =[job['id'] for job in job_queue.get_jobs([job_queue.RUNNING])]
    logging.info(f"Processing service stopped. Jobs which are still running: {running}")



  def request_stop(self, signum=None, frame=None) -> None:

    logging.info(f"Stop of processing service requested ({signum=})")
    self.stop_requested = True
    # Don't wait for the next look into the queue
    notify()



  def wait_for_wakeup(self, timeout: float) -> None:

    if self.socket is None:
      time.sleep(timeout)
      return

    readable, _, _ = select.select([self.socket], [], [], timeout)
    if not readable:
      return

    # One look into the queue is enough for all of them
    try:
      while True:
        self.socket.recv(16)
    except BlockingIOError:
      pass



  def run_once(self, timeout: float|None = None) -> None:
    """
    One cycle: wait for a wake-up, look after the job processes, start queued jobs, clean up

    Args:
        timeout (float, optional): Seconds to wait for a wake-up. Defaults to poll-interval
    """

    self.wait_for_wakeup(self.settings['poll-interval'] if timeout is None else timeout)

    if self.stop_requested:
      return

    self.reap_children()
    self.check_running_jobs()
    self.start_jobs()
    self.clean_up()
    self.check_idle()



  def run_forever(self) -> None:

    self.start()

    signal.signal(signal.SIGTERM, self.request_stop)
    signal.signal(signal.SIGINT, self.request_stop)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    try:
      # Jobs which have been queued or lost their process while the service was not running
      timeout = 0

      while not self.stop_requested:
        try:
          self.run_once(timeout)
        except Exception as e:
          # E.g. a locked database. The next cycle tries again.
          logging.exception(e)
        timeout = None

    finally:
      self.stop()



  def abort_job(self, job: dict, error: str) -> None:
    """Ends a job whose process has ended without setting its final status"""

    status = job_queue.CANCELLED if job.get('cancel_requested') else job_queue.FAILED
    logging.error(f"Job {job['id']} {status}: {error}")
    job_queue.end_job(job['id'], status, error=error, from_statuses=(job_queue.RUNNING,))



  def reap_children(self) -> None:
    """Looks after the job processes of this service which have ended"""

    for job_id, process in list(self.children.items()):

      if not has_exited(process):
        continue

      # A job process sets its final status by itself
      job = job_queue.get_job(job_id)
      unexpected = job is not None and job['status'] == job_queue.RUNNING

      if unexpected:
        # Its commands may still be running (e.g. the job process has been killed). Stop them before the process is reaped:
        # until then its pid, and so the id of its process group, can't be used by another process.
        try:
          os.killpg(process.pid, signal.SIGKILL)
          logging.warning(f"Remaining processes of job {job_id} killed (process group {process.pid})")
        except (ProcessLookupError, PermissionError):
          pass

      exit_code = process.wait()
      del self.children[job_id]
      logging.info(f"Job process {process.pid} of job {job_id} ended ({exit_code=})")

      if unexpected:
        reason = f"signal {-exit_code}" if exit_code < 0 else f"exit code {exit_code}"
        self.abort_job(job, f"Job process {process.pid} ended unexpectedly ({reason})")



  def check_running_jobs(self) -> None:
    """
    Jobs whose process doesn't exist anymore (killed, system restarted, service restarted meanwhile) are ended.
    Jobs which have been cancelled, but didn't end within cancel-timeout, are killed.
    """

    heartbeat_timeout = self.settings['heartbeat-timeout']

    for job in job_queue.get_jobs([job_queue.RUNNING]):

      has_heartbeat = job['heartbeat'] is not None and time.time() - job['heartbeat'] <= heartbeat_timeout
      own_child = job['id'] in self.children

      if job['pid'] is None and not own_child:
        if has_heartbeat:
          # Claimed, its process is going to be started
          continue
        error = "Job process has not been started"

      elif not own_child and not process_exists(job['pid']):
        error = f"Job process {job['pid']} doesn't exist anymore"

      elif not has_heartbeat:
        # The job process stops by itself when it sees that it has been given up
        error = f"No sign of life from job process {job['pid']} for more than {heartbeat_timeout} seconds"

      else:
        self.kill_after_cancel_timeout(job)
        continue

      self.abort_job(job, error)



  def kill_after_cancel_timeout(self, job: dict) -> None:

    if not job['cancel_requested'] or time.time() - job['cancel_requested'] < self.settings['cancel-timeout']:
      return

    logging.warning(f"Job {job['id']} didn't end within {self.settings['cancel-timeout']} seconds after cancel: kill it")

    if job['id'] in self.children:
      # Own child: its pid can't be used by another process
      try:
        os.killpg(self.children[job['id']].pid, signal.SIGKILL)
      except (ProcessLookupError, PermissionError) as e:
        logging.warning(f"Job {job['id']} couldn't be killed: {e}")
    else:
      signal_job(job, signal.SIGKILL, self.settings['heartbeat-timeout'])



  def start_jobs(self) -> None:
    """Starts queued jobs, as long as max-parallel-jobs is not reached"""

    while job_queue.count_jobs([job_queue.RUNNING]) < self.settings['max-parallel-jobs']:

      job = job_queue.claim_next_job()
      if job is None:
        return

      self.start_job_process(job)



  def job_command(self, job: dict) -> list[str]:

    return [
      sys.executable, '-X', 'utf8', MAIN_PY, '-a', 'run',
      '-p', job['project'], '-c', os.path.dirname(job['compile_list']), '--job', str(job['id'])
    ]



  def start_job_process(self, job: dict) -> None:

    job_dir = service_config.job_dir(job['id'])
    os.makedirs(job_dir, exist_ok=True)

    try:
      with open(os.path.join(job_dir, 'output.log'), 'ab') as output:
        process = subprocess.Popen(
          self.job_command(job), cwd=job['project'],
          stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
          # Own session: the job keeps running when the service ends, and can be stopped with all its commands
          start_new_session=True
        )

    except OSError as e:
      logging.exception(e)
      job_queue.end_job(job['id'], job_queue.FAILED, error=f"Job process could not be started: {e}", from_statuses=(job_queue.RUNNING,))
      return

    self.children[job['id']] = process
    job_queue.set_pid(job['id'], process.pid)
    logging.info(f"Job process {process.pid} started for job {job['id']}: {job['compile_list']}")



  def clean_up(self) -> None:

    if time.monotonic() - self.last_cleanup < CLEANUP_INTERVAL and self.last_cleanup > 0:
      return

    self.last_cleanup = time.monotonic()
    deleted = job_queue.delete_ended_jobs(self.settings['keep-jobs-days'])
    if deleted:
      logging.info(f"Deleted ended jobs: {deleted}")



  def check_idle(self) -> None:
    """Ends the service after idle-timeout without queued or running jobs. The next submit starts it again."""

    if self.children or job_queue.count_jobs(job_queue.OPEN_STATUSES) > 0:
      self.last_active = time.monotonic()
      return

    idle_timeout = self.settings['idle-timeout']
    if idle_timeout <= 0 or time.monotonic() - self.last_active < idle_timeout:
      return

    # Release the lock first, then look once more. `submit` adds its job first, then looks at the lock.
    # So either this look finds the job, or submit finds no service and starts a new one.
    self.close_socket()
    self.remove_pid_file()
    self.release_lock()

    if job_queue.count_jobs(job_queue.OPEN_STATUSES) > 0:
      try:
        self.acquire_lock(0)
      except ServiceAlreadyRunningError:
        logging.info("A new processing service has been started meanwhile: stop this one")
        self.stop_requested = True
        return

      self.open_socket()
      self.write_pid_file()
      self.last_active = time.monotonic()
      return

    logging.info(f"No jobs for {idle_timeout} seconds: stop processing service")
    self.stop_requested = True
