import toml

def get_config(config):
  with open(config, 'r') as f:
    return toml.load(f)


def write_config(config, content):
  with open(config, 'w') as f:
    toml.dump(content, f)