"""
Events of a job: one JSON object per line in `<service dir>/jobs/<id>/events.jsonl`, append only.

`seq` starts at 1 and has no gaps, so a client can continue after the last event it got.
Only one process writes at a time: `submit` (queued), then the job process, then whoever ends the job.

See docs/processing-service.md#events
"""
import json
import logging
import os
import threading
from datetime import datetime

from module import service_config



def events_file(job_id: int) -> str:
  return os.path.join(service_config.job_dir(job_id), 'events.jsonl')



def count_events(file: str) -> int:

  if not os.path.isfile(file):
    return 0

  count = 0
  with open(file, 'rb') as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b''):
      count += chunk.count(b'\n')
  return count



def write_event(file: str, seq: int, event_type: str, data: dict) -> dict:

  event = {'seq': seq, 'time': datetime.now().isoformat(), 'type': event_type, **data}

  os.makedirs(os.path.dirname(file), exist_ok=True)
  # json.dumps escapes line breaks and non-ASCII characters: one event is always one line, whatever the encoding of the client
  with open(file, 'a', encoding='ascii') as f:
    f.write(json.dumps(event) + '\n')

  return event



def append_event(job_id: int, event_type: str, **data) -> dict:
  """Writes a single event. For events of the job process, use EventWriter."""

  file = events_file(job_id)
  return write_event(file, count_events(file) + 1, event_type, data)



class EventWriter:
  """Writes the events of the job process. Counts the existing events only once."""

  def __init__(self, job_id: int):
    self.file = events_file(job_id)
    self.seq = count_events(self.file)
    self.lock = threading.Lock()


  def emit(self, event_type: str, **data) -> dict:
    with self.lock:
      self.seq += 1
      return write_event(self.file, self.seq, event_type, data)



class EventReader:
  """Reads the events of a job, each only once. Keeps the position in the file between two calls."""

  def __init__(self, job_id: int, since: int = 0):
    self.file = events_file(job_id)
    self.since = since
    self.offset = 0
    # Start of a line that is still being written
    self.rest = b''


  def read_new(self) -> list[dict]:

    try:
      with open(self.file, 'rb') as f:
        f.seek(self.offset)
        data = f.read()
    except FileNotFoundError:
      return []

    self.offset += len(data)
    lines = (self.rest + data).split(b'\n')
    self.rest = lines.pop()

    events = []
    for line in lines:
      if not line.strip():
        continue
      try:
        event = json.loads(line)
      except ValueError as e:
        logging.warning(f"Invalid event in {self.file}: {e}")
        continue
      if event.get('seq', 0) > self.since:
        events.append(event)

    return events



def read_events(job_id: int, since: int = 0) -> list[dict]:
  return EventReader(job_id, since).read_new()
