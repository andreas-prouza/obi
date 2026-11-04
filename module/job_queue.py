"""
Queue of the processing service: the jobs in SQLite (`<service dir>/jobs.sqlite`).

The database is the only interface between the clients (submit, watch, cancel), the service and the job processes.
Each call opens its own connection, so no connection is kept open (needed for the service, which starts processes).

See docs/processing-service.md
"""
import contextlib
import json
import os
import shutil
import sqlite3
import time
from datetime import datetime, timedelta

from module import job_events
from module import service_config



QUEUED = 'queued'
RUNNING = 'running'
FINISHED = 'finished'
FAILED = 'failed'
CANCELLED = 'cancelled'

OPEN_STATUSES = (QUEUED, RUNNING)
ENDED_STATUSES = (FINISHED, FAILED, CANCELLED)

SCHEMA_VERSION = 1

# Characters of an error which are stored for a job. The complete error is in the log.
MAX_ERROR_LENGTH = 2000



class JobConflictError(Exception):
  pass



def now() -> str:
  return datetime.now().isoformat(timespec='seconds')



def create_tables(conn: sqlite3.Connection) -> None:

  version = conn.execute('PRAGMA user_version').fetchone()[0]

  if version > SCHEMA_VERSION:
    raise Exception(f"The job database {service_config.db_file()} is newer than this OBI (version {version}). Update OBI")

  if version == SCHEMA_VERSION:
    return

  conn.executescript(f"""
    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      project TEXT NOT NULL,
      compile_list TEXT NOT NULL,
      status TEXT NOT NULL,
      build_status TEXT,
      error TEXT,
      progress TEXT,
      queued TEXT NOT NULL,
      started TEXT,
      ended TEXT,
      pid INTEGER,
      heartbeat REAL,
      cancel_requested REAL
    );
    CREATE INDEX IF NOT EXISTS jobs_status ON jobs (status);
    CREATE INDEX IF NOT EXISTS jobs_compile_list ON jobs (compile_list);
    PRAGMA user_version = {SCHEMA_VERSION};
  """)



@contextlib.contextmanager
def connect():

  service_config.ensure_dir()
  db_file = service_config.db_file()
  new_db = not os.path.exists(db_file)

  # Autocommit, transactions are started explicitly (BEGIN IMMEDIATE)
  conn = sqlite3.connect(db_file, timeout=30, isolation_level=None)

  try:
    if new_db:
      os.chmod(db_file, 0o600)
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    yield conn

  finally:
    conn.close()



@contextlib.contextmanager
def transaction():

  with connect() as conn:
    conn.execute('BEGIN IMMEDIATE')
    try:
      yield conn
      conn.execute('COMMIT')
    except BaseException:
      conn.execute('ROLLBACK')
      raise



def to_dict(row: sqlite3.Row|None) -> dict|None:

  if row is None:
    return None

  job = dict(row)
  job['progress'] = json.loads(job['progress']) if job['progress'] else None
  return job



def get_job(job_id: int) -> dict|None:

  with connect() as conn:
    return to_dict(conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone())



def get_jobs(statuses: tuple|list|None = None, project: str|None = None, limit: int|None = None) -> list[dict]:
  """Jobs, the newest first"""

  sql = 'SELECT * FROM jobs WHERE 1 = 1'
  params = []

  if statuses:
    sql += f" AND status IN ({', '.join('?' * len(statuses))})"
    params += list(statuses)

  if project is not None:
    sql += ' AND project = ?'
    params.append(project)

  sql += ' ORDER BY id DESC'

  if limit is not None:
    sql += ' LIMIT ?'
    params.append(int(limit))

  with connect() as conn:
    return [to_dict(row) for row in conn.execute(sql, params).fetchall()]



def count_jobs(statuses: tuple|list) -> int:

  with connect() as conn:
    return conn.execute(f"SELECT COUNT(*) FROM jobs WHERE status IN ({', '.join('?' * len(statuses))})", list(statuses)).fetchone()[0]



def add_job(project: str, compile_list: str) -> dict:
  """
  Adds a job to the queue and writes its first event.

  Raises:
      JobConflictError: The build list has already a job that is queued or running
  """

  job_id = None

  try:
    with transaction() as conn:

      open_job = conn.execute(
        f"SELECT id, status FROM jobs WHERE compile_list = ? AND status IN ({', '.join('?' * len(OPEN_STATUSES))})",
        (compile_list, *OPEN_STATUSES)
      ).fetchone()

      if open_job is not None:
        raise JobConflictError(f"The build list {compile_list} is already {open_job['status']} (job {open_job['id']})")

      job_id = conn.execute(
        'INSERT INTO jobs (project, compile_list, status, queued) VALUES (?, ?, ?, ?)',
        (project, compile_list, QUEUED, now())
      ).lastrowid

      position = conn.execute('SELECT COUNT(*) FROM jobs WHERE status = ? AND id <= ?', (QUEUED, job_id)).fetchone()[0]

      # Before the commit: the service can't take the job before its first event has been written
      job_events.append_event(job_id, 'queued', position=position)

  except BaseException:
    # The id may be used again after the rollback
    if job_id is not None:
      shutil.rmtree(service_config.job_dir(job_id), ignore_errors=True)
    raise

  return get_job(job_id)



def claim_next_job() -> dict|None:
  """The oldest queued job is set to running. The heartbeat gives its process the time to start."""

  with transaction() as conn:

    row = conn.execute('SELECT id FROM jobs WHERE status = ? ORDER BY id LIMIT 1', (QUEUED,)).fetchone()
    if row is None:
      return None

    conn.execute(
      'UPDATE jobs SET status = ?, started = ?, heartbeat = ? WHERE id = ?',
      (RUNNING, now(), time.time(), row['id'])
    )

  return get_job(row['id'])



def set_pid(job_id: int, pid: int) -> None:

  with transaction() as conn:
    conn.execute('UPDATE jobs SET pid = ? WHERE id = ? AND status = ?', (pid, job_id, RUNNING))



def touch(job_id: int, progress: dict|None = None) -> dict|None:
  """Sign of life of the job process. Returns the job, e.g. to see whether it has been cancelled."""

  with transaction() as conn:
    if progress is None:
      conn.execute('UPDATE jobs SET heartbeat = ? WHERE id = ? AND status = ?', (time.time(), job_id, RUNNING))
    else:
      conn.execute('UPDATE jobs SET heartbeat = ?, progress = ? WHERE id = ? AND status = ?', (time.time(), json.dumps(progress), job_id, RUNNING))

  return get_job(job_id)



def request_cancel(job_id: int) -> dict|None:

  with transaction() as conn:
    conn.execute(
      'UPDATE jobs SET cancel_requested = COALESCE(cancel_requested, ?) WHERE id = ? AND status = ?',
      (time.time(), job_id, RUNNING)
    )

  return get_job(job_id)



def end_job(job_id: int, status: str, build_status: str|None = None, error: str|None = None,
            progress: dict|None = None, from_statuses: tuple = OPEN_STATUSES) -> bool:
  """
  Sets the final status of a job and writes its last event (`ended`).

  Returns:
      bool: False if the job wasn't in one of `from_statuses` (e.g. it has already ended)
  """

  if status not in ENDED_STATUSES:
    raise ValueError(f"Invalid final status {status}")

  if error is not None:
    error = error[:MAX_ERROR_LENGTH]

  with transaction() as conn:

    sql = f"UPDATE jobs SET status = ?, build_status = ?, error = ?, ended = ?{', progress = ?' if progress is not None else ''} WHERE id = ? AND status IN ({', '.join('?' * len(from_statuses))})"
    params = [status, build_status, error, now()] + ([json.dumps(progress)] if progress is not None else []) + [job_id, *from_statuses]

    if conn.execute(sql, params).rowcount == 0:
      return False

    job = to_dict(conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone())
    # In the transaction: if the event can't be written, the job doesn't end
    job_events.append_event(job_id, 'ended', status=status, build_status=build_status, error=error, progress=job['progress'])

  return True



def delete_ended_jobs(keep_days: float) -> list[int]:
  """Deletes ended jobs and their files after `keep_days`. 0: keep them."""

  if keep_days <= 0:
    return []

  cutoff = (datetime.now() - timedelta(days=keep_days)).isoformat(timespec='seconds')

  with transaction() as conn:
    ids = [row['id'] for row in conn.execute(
      f"SELECT id FROM jobs WHERE status IN ({', '.join('?' * len(ENDED_STATUSES))}) AND ended < ?",
      (*ENDED_STATUSES, cutoff)
    ).fetchall()]
    conn.executemany('DELETE FROM jobs WHERE id = ?', [(job_id,) for job_id in ids])

  for job_id in ids:
    shutil.rmtree(service_config.job_dir(job_id), ignore_errors=True)

  return ids
