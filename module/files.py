import os, pathlib, datetime, json, logging, toml
from . import properties
from pathlib import PureWindowsPath


def get_files(path, file_extensions=[], fs_encoding='utf-8'):

  src={}

  path = bytes(os.path.expanduser(path), 'utf-8')

  for root, dirs, files in os.walk(path):

    root_decoded = root.decode(fs_encoding)
    root_utf8 = root.decode('utf-8')
    for file in files:

      file_decoded = file.decode(fs_encoding)
      file_utf8 = file.decode('utf-8')
      if file_decoded.endswith(tuple(file_extensions)):

        path_file=f"{os.path.join(root, file).removeprefix(path).removeprefix(bytes(os.sep, 'utf-8')).decode(fs_encoding)}"
        if os.path.sep == '\\': # Needed because of Windows file format
          path_file = PureWindowsPath(path_file).as_posix()

        changed_time=datetime.datetime.fromtimestamp(pathlib.Path(os.path.join(root_utf8, file_utf8)).stat().st_mtime)
        src.update({path_file.replace("\\", '/'): changed_time})

  return src



def get_changed_sources(source_dir, build_toml, object_types, src_list=None):

  if src_list is None:
    src_list=get_files(source_dir, object_types)

  build_list=properties.get_config(build_toml)

  logging.debug(f"Search for changed sources in '{source_dir}'")
  logging.debug(f"{object_types=}")
  logging.info(f"Found {len(src_list)} sources")

  missing_obj=[]
  changed_src=[]

  for src, chgange_time in src_list.items():
    if src not in build_list.keys():
      missing_obj.append(src)
      continue
    if chgange_time > build_list[src]:
      changed_src.append(src)

  return {"new-objects": missing_obj, "changed-sources": changed_src}



def readText(file):
  with open(f"{os.path.dirname(__file__)}/../{file}", 'r') as text_file:
    return str(text_file.read())



def writeText(content, file, write_empty_file=False):
  
  
  if file is None or len(content) == 0 and not write_empty_file:
    return

  logging.debug(f"Write Textfile: {os.path.abspath(file)=}; {len(content)} Bytes")

  # Create dir if not exist
  pathlib.Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)

  with open(file, 'w', encoding='utf-8') as text_file:
      text_file.write(content)




def writeJson(content, file):
  
  if file is None:
    return

  # Create dir if not exist
  pathlib.Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)

  with open(file, 'w') as json_file:
      json.dump(content, json_file, indent=2)



def writeToml(content, file):
  
  if file is None:
    return

  # Create dir if not exist
  pathlib.Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)

  with open(file, 'w') as toml_file:
      toml.dump(content, toml_file)


