import toml
import os, datetime
from module import properties
from module import files

config = properties.get_config('etc/config.toml')
source_dir=f"{config['general']['project-dir']}/{config['general']['source-dir']}"
build_list=config['general']['build-list']
object_types=config['general']['supported-object-types']

# Access values from the config
print(config['global']['cmds']['ccsid-conf'])



source_list=files.get_files(source_dir, object_types)
#properties.write_config('etc/build.toml', source_list)
#print(source_list)

changed_list=files.get_changed_sources(source_dir, build_list, object_types)

print(changed_list)

#print(src_list[0])
#print(datetime.datetime.fromtimestamp(src_list[0]['modified']))
#print(build_list[0])
#print(datetime.datetime.fromtimestamp(build_list[0]['modified']))