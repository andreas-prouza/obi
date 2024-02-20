import os, pathlib, datetime, json, logging, toml
from . import properties


def get_files(path, file_extensions=[]):

  src={}

  path = os.path.expanduser(path)

  for root, dirs, files in os.walk(path):
    for file in files:
      if file.endswith(tuple(file_extensions)):
        path_file=f"{os.path.join(root, file).removeprefix(path).removeprefix(os.sep)}"
        changed_time=datetime.datetime.fromtimestamp(pathlib.Path(os.path.join(root, file)).stat().st_mtime)
        src.update({path_file: changed_time})

  return src



def get_changed_sources(source_dir, build_toml, object_types):

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
  with open(file, 'r') as text_file:
    return str(text_file.readall())



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


