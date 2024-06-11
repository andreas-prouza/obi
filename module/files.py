import os, pathlib, datetime, json, logging, toml
import hashlib, mmap
from . import properties
from pathlib import PureWindowsPath


def get_files(path, file_extensions=[], fs_encoding='utf-8', with_time=False):

  src={}

  path_bytes = bytes(os.path.expanduser(path), 'utf-8')

  for root, dirs, files in os.walk(path_bytes):

    root_decoded = root.decode(fs_encoding)

    for file in files:

      file_decoded = file.decode(fs_encoding)
      
      if file_decoded.endswith(tuple(file_extensions)):

        path_file=os.path.join(root_decoded, file_decoded).removeprefix(path).removeprefix(os.sep)
        if os.path.sep == '\\': # Needed because of Windows file format
          path_file = PureWindowsPath(path_file).as_posix()

        file_stat = os.path.join(root, file).decode('utf-8')
        
        changed_time = None
        if with_time:
          changed_time=datetime.datetime.fromtimestamp(pathlib.Path(file_stat).stat().st_mtime)
        
        hashed_file = get_file_hash(file_stat)

        src.update({path_file.replace("\\", '/'): {"created" : changed_time, "hash": hashed_file}})

  return src



def get_changed_sources(source_dir, build_toml, object_types, src_list=None):

  if src_list is None:
    src_list=get_files(source_dir, object_types)

  build_list=properties.get_config(build_toml)

  logging.debug(f"Objects in build list: {len(build_list)}")

  logging.debug(f"Search for changed sources in '{source_dir}'")
  logging.debug(f"{object_types=}")
  logging.info(f"Found {len(src_list)} sources")

  missing_obj=[]
  changed_src=[]

  for src, attributes in src_list.items():
    if src not in build_list.keys():
      missing_obj.append(src)
      continue
    if attributes['hash'] != build_list[src]['hash']:
      changed_src.append(src)

  return {"new-objects": missing_obj, "changed-sources": changed_src}



def get_file_hash(filename):
    
    if os.path.getsize(filename) == 0:
      return ''

    h  = hashlib.sha256()
    with open(filename, "rb") as f:
        with mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ) as mm:
            h.update(mm)
    return h.hexdigest()



def readText(file):
  with open(f"{os.path.dirname(__file__)}/../{file}", 'r') as text_file:
    return str(text_file.read())



def writeText(content, file, write_empty_file=False, encoding='utf-8', mode='w'):
  
  
  if file is None or len(content) == 0 and not write_empty_file:
    return

  logging.debug(f"Write Textfile: {os.path.abspath(file)=}; {len(content)} Bytes")

  # Create dir if not exist
  pathlib.Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)

  with open(file, mode, encoding=encoding) as text_file:
      text_file.write(content)



def getJson(file):

  with open(file, 'r') as f:
    return json.load(f)
  
  return None


def writeJson(content, file):
  
  if file is None:
    return

  logging.debug(content)
  # Create dir if not exist
  pathlib.Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)

  with open(file, 'w') as json_file:
      json.dump(content, json_file, indent=2, ensure_ascii=False)



def writeToml(content, file):
  
  if file is None:
    return

  # Create dir if not exist
  pathlib.Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)

  with open(file, 'w') as toml_file:
      toml.dump(content, toml_file)




def update_compiles_object_list(source, app_config=default_app_config):

  compiled_object_list = properties.get_config(app_config['general']['compiled-object-list'])
  
  file_hash = files.get_file_hash(f"{app_config['general']['source-dir']}/{source}")

  compiled_object_list[source] = {"created" : datetime.now(), "hash" : file_hash}
  logging.debug(f"Update {source=} in {compiled_object_list[source]}")

  logging.debug(f"Update build list: {len(compiled_object_list)}")
  properties.write_config(app_config['general']['compiled-object-list'], compiled_object_list)




def source_needs_compiled(source, app_config):

  compiled_object_list = properties.get_config(app_config['general']['compiled-object-list'])
  
  compiled_object_list[source] = {"created" : None, "hash" : None}
  logging.debug(f"Update {source=} in {compiled_object_list[source]}")

  properties.write_config(app_config['general']['compiled-object-list'], compiled_object_list)

