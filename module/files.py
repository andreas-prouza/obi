import os, pathlib, datetime
from . import properties


def get_files(path, file_extensions=[]):

  src={}

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

  missing_obj=[]
  changed_src=[]

  for src, chgange_time in src_list.items():
    if src not in build_list.keys():
      missing_obj.append(src)
      continue
    if chgange_time > build_list[src]:
      changed_src.append(src)

  return {"new-objects": missing_obj, "changed-sources": changed_src}