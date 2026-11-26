"""
Branch build: a build on a branch with a ticket number in its name goes into libraries of that
ticket (e.g. `#be_337`) instead of the main libraries.

Optional: only active if the config has a `[branch-build]` section which doesn't set `enabled = false`.
Without it, nothing in here changes the build, and git is never called.

The context of the current OBI call is set once with `init` (actions create and add_source).
The ESP and its scripts keep seeing the main libraries: the branch library is applied to the
properties of each command (`apply_branch_lib`, `finalize_properties`).
"""

import logging
import re
import subprocess

from module import properties


MODE_BRANCH = 'branch'
MODE_MAIN = 'main'

# IBM i library name: max. 10 characters
LIB_NAME_PATTERN = re.compile(r'[A-Za-z#$@][A-Za-z0-9#$@_.]{0,9}')
ENV_PATTERN = re.compile(r'[A-Za-z0-9]{1,8}')
# Branch names may contain characters a shell or CL would interpret
UNSAFE_TEXT_CHARS = re.compile(r'[^A-Za-z0-9._/\-]')
TEXT_MAX_LENGTH = 50
# Can't be part of a real value
TARGET_LIB_PLACEHOLDER = '\x00OBI_TARGET_LIB\x00'
GIT_TIMEOUT = 10

DEFAULT_CRT_LIB_CMD = ('cl "CHKOBJ OBJ($(LIB)) OBJTYPE(*LIB)" > /dev/null 2>&1 || '
                       'cl -v "CRTLIB LIB($(LIB)) TYPE(*TEST) TEXT(\'$(BRANCH_TEXT)\')"')


_context = None



class BranchBuildError(Exception):
  pass



def get_config(app_config: dict) -> dict | None:
  """The `[branch-build]` section, or None if the feature is off"""

  if 'branch-build' not in app_config:
    return None

  config = app_config['branch-build']
  if not isinstance(config, dict):
    raise BranchBuildError("Invalid config: 'branch-build' must be a section ([branch-build])")

  if config.get('enabled', True) is False:
    return None

  return config



def is_active(app_config: dict) -> bool:
  return get_config(app_config) is not None



def validate_config(config: dict) -> None:
  """Raises BranchBuildError if the section is incomplete. A half configured feature must not fall back to the main libraries"""

  errors = []

  pattern = config.get('ticket-pattern')
  if not isinstance(pattern, str) or pattern.strip() == '':
    errors.append("'ticket-pattern' is missing")
  else:
    try:
      if re.compile(pattern).groups < 1:
        errors.append("'ticket-pattern' needs a group for the ticket number, e.g. '(?i)\\bproj[-_](\\d+)'")
    except re.error as e:
      errors.append(f"'ticket-pattern' is not a valid regular expression: {e}")

  lib_name = config.get('lib-name')
  if not isinstance(lib_name, str) or lib_name.strip() == '':
    errors.append("'lib-name' is missing")
  elif '$(TICKET)' not in lib_name:
    errors.append("'lib-name' must contain $(TICKET)")

  env = config.get('env', {})
  if not isinstance(env, dict):
    errors.append("'env' must be a section ([branch-build.env])")
  else:
    if isinstance(lib_name, str) and '$(ENV)' in lib_name and len(env) == 0:
      errors.append("'lib-name' uses $(ENV), but [branch-build.env] is missing or empty")
    for lib, env_name in env.items():
      if not isinstance(env_name, str) or not ENV_PATTERN.fullmatch(env_name):
        errors.append(f"[branch-build.env] {lib}: '{env_name}' is not a valid ENV (1-8 letters or digits)")

  if not isinstance(config.get('settings', {}), dict):
    errors.append("'settings' must be a section ([branch-build.settings])")

  if errors:
    raise BranchBuildError(f"Invalid [branch-build] config: {'; '.join(errors)}")



def get_branch(branch_arg: str | None = None) -> tuple[str | None, str | None]:
  """Branch of the project (current directory)

  Returns:
      tuple: (branch or None, warning or None)
  """

  if branch_arg is not None and branch_arg.strip() != '':
    return branch_arg.strip(), None

  try:
    # No shell: nothing of the output or the project path gets interpreted
    s = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True,
                       timeout=GIT_TIMEOUT, check=False)
  except (OSError, subprocess.TimeoutExpired) as e:
    return None, f"git is not available ({e})"

  if s.returncode != 0:
    return None, f"No git repository ({s.stderr.strip()})"

  branch = s.stdout.strip()
  if branch in ('', 'HEAD'):
    return None, "Detached HEAD"

  return branch, None



def get_ticket(branch: str | None, pattern: str) -> str | None:

  if branch is None:
    return None

  match = re.search(pattern, branch)
  if match is None or not match.group(1):
    return None

  return match.group(1)



def create_context(app_config: dict, branch_arg: str | None = None) -> dict | None:
  """Build context of the current branch. None if the feature is off"""

  config = get_config(app_config)
  if config is None:
    return None

  validate_config(config)

  branch, warning = get_branch(branch_arg)
  ticket = get_ticket(branch, config['ticket-pattern'])

  context = {
    'mode': MODE_BRANCH if ticket else MODE_MAIN,
    'branch': branch,
    'ticket': ticket,
    'libs': [],
  }

  if warning is not None:
    context['warning'] = f"{warning}. Building into the main libraries"
    logging.warning(f"Branch build: {context['warning']}")

  logging.info(f"Branch build: {context['mode']=}, {branch=}, {ticket=}")

  return context



def describe(context: dict | None) -> str:

  if not isinstance(context, dict) or context.get('mode') != MODE_BRANCH:
    return "the main libraries"

  return f"ticket {context.get('ticket')} (branch {context.get('branch')})"



def init(app_config: dict, branch_arg: str | None = None, compile_list: dict | None = None) -> dict | None:
  """Set the context of this OBI call

  Args:
      app_config (dict): Application config
      branch_arg (str, optional): Branch passed by the client (--branch). Otherwise it's read from git
      compile_list (dict, optional): Existing compile list (add_source). Its context must match the current one

  Returns:
      dict | None: Context, None if the feature is off
  """

  global _context
  _context = None

  context = create_context(app_config, branch_arg)
  if context is None:
    return None

  if compile_list is not None:
    stored = compile_list.get('build_context')
    stored_mode = stored.get('mode') if isinstance(stored, dict) else MODE_MAIN
    stored_ticket = stored.get('ticket') if isinstance(stored, dict) else None

    # Otherwise the list would build into the libraries of two different branches
    if (stored_mode, stored_ticket) != (context['mode'], context['ticket']):
      raise BranchBuildError(f"The build list was created for {describe(stored)}, but the current branch builds into "
                             f"{describe(context)}. Create a new build list")

    if isinstance(stored, dict):
      context['libs'] = list(stored.get('libs', []))

  _context = context
  return _context



def get_context() -> dict | None:
  return _context



def reset() -> None:
  global _context
  _context = None



def is_branch_mode() -> bool:
  return _context is not None and _context.get('mode') == MODE_BRANCH



def get_production_lib(lib: str, lib_mapping: dict | None) -> str:
  """Library of a main build (e.g. #h_beobj) -> production library (h_beobj). Without a mapping, it's the library itself"""

  lib = str(lib).lower()

  for production_lib, main_lib in (lib_mapping or {}).items():
    if str(main_lib).lower() == lib:
      return str(production_lib).lower()

  return lib



def get_branch_lib(lib: str, lib_mapping: dict | None, app_config: dict) -> str | None:
  """Branch library of a library. None if the library has no ENV

  Raises:
      BranchBuildError: If the name isn't a valid library name
  """

  config = get_config(app_config)
  lib_name = config['lib-name']
  values = {'TICKET': _context['ticket']}

  if '$(ENV)' in lib_name:
    env_mapping = {str(k).lower(): v for k, v in config.get('env', {}).items()}
    env = env_mapping.get(get_production_lib(lib, lib_mapping))
    if env is None:
      return None
    values['ENV'] = env

  branch_lib = properties.resolve_string(lib_name, values)

  if not LIB_NAME_PATTERN.fullmatch(branch_lib):
    raise BranchBuildError(f"Branch library '{branch_lib}' (for '{lib}') is not a valid library name (max. 10 characters)")

  return branch_lib.lower()



def apply_branch_lib(props: dict, app_config: dict, main_lib: str | None = None, with_settings: bool = True) -> dict:
  """Set the variables of the branch build (before the properties get resolved)

  TARGET_LIB_MAIN is the target library of a main build. In branch mode TARGET_LIB becomes its branch library.
  A library without ENV (e.g. a pseudo library before ESP) stays as it is; `finalize_properties` checks the commands.

  Args:
      props (dict): Properties of a source or a step
      app_config (dict): Application config
      main_lib (str, optional): Target library of a main build. Default: TARGET_LIB of props
      with_settings (bool): Add [branch-build.settings] (branch mode only)

  Returns:
      dict: New properties. Unchanged if the feature is off
  """

  if _context is None:
    return props

  props = dict(props)

  if main_lib is None:
    main_lib = props.get('TARGET_LIB', '')
  # e.g. TARGET_LIB = "$(TARGET_LIB_ORIG)" in a step
  main_lib = str(properties.resolve_nested_string(main_lib, {**props, 'TARGET_LIB': props.get('TARGET_LIB_MAIN', props.get('TARGET_LIB'))})).lower()

  props['TARGET_LIB_MAIN'] = main_lib
  props['TARGET_LIB'] = main_lib
  props['BUILD_MODE'] = _context['mode']
  props['BRANCH'] = _context.get('branch') or ''
  props['TICKET'] = _context.get('ticket') or ''

  if not is_branch_mode():
    return props

  branch_lib = get_branch_lib(main_lib, props.get('TARGET_LIB_MAPPING'), app_config)
  if branch_lib is not None:
    props['TARGET_LIB'] = branch_lib

  if with_settings:
    props.update(get_config(app_config).get('settings', {}))

  return props



def cmd_uses_target_lib(cmd: str, unresolved_props: dict, replace_cmd_parameters) -> bool:
  """True if the command uses TARGET_LIB, directly or through another variable

  Args:
      cmd (str): Command before its variables are replaced
      unresolved_props (dict): Properties of the command before they got resolved
      replace_cmd_parameters (callable): build_cmds.replace_cmd_parameters
  """

  test_props = properties.resolve_properties({**unresolved_props, 'TARGET_LIB': TARGET_LIB_PLACEHOLDER})
  return TARGET_LIB_PLACEHOLDER in replace_cmd_parameters(cmd, test_props)



def finalize_properties(props: dict, app_config: dict, source: str, step_id: str | None = None, uses_target_lib: bool = True) -> dict:
  """Check and complete the resolved properties of a command (branch mode only)

  * Fail-safe: a command which uses the target library must use a branch library, never a main library
  * SET_LIBL: the branch libraries of all libraries of LIBL go on top, the target library topmost
  * The target library is remembered, so `run` creates it

  Commands which don't use TARGET_LIB (e.g. copybook steps) and steps in `no-lib-steps` (e.g. messages)
  don't build into the target library: they're not checked and get no library.

  Raises:
      BranchBuildError: If the target library has no branch library
  """

  if not is_branch_mode():
    return props

  config = get_config(app_config)
  needs_lib = uses_target_lib and not (step_id is not None and step_id in config.get('no-lib-steps', []))

  lib_mapping = props.get('TARGET_LIB_MAPPING')
  target_lib = str(props.get('TARGET_LIB', '')).lower()
  main_lib = str(props.get('TARGET_LIB_MAIN', target_lib)).lower()
  is_branch_lib = get_branch_lib(main_lib, lib_mapping, app_config) == target_lib

  if needs_lib and not is_branch_lib:
    raise BranchBuildError(f"{source}: target library '{main_lib}' has no branch library for {describe(_context)}. "
                           f"Add its production library ({get_production_lib(main_lib, lib_mapping)}) to [branch-build.env]")

  # LIBL as in a main build ...
  libl = [main_lib if str(lib).lower() == target_lib else lib for lib in props.get('LIBL', [])]

  # ... plus the branch libraries. `add-lible` puts each library on top, so the target library is added last
  branch_libs = []
  for lib in libl:
    if '$(' in str(lib):
      continue
    branch_lib = get_branch_lib(lib, lib_mapping, app_config)
    if branch_lib is not None and branch_lib != target_lib and branch_lib not in branch_libs:
      branch_libs.append(branch_lib)
  if is_branch_lib:
    branch_libs.append(target_lib)

  props = dict(props)
  props['BRANCH_LIBS'] = ' '.join(branch_libs)
  props['SET_LIBL'] = properties.get_set_libl_cmd(app_config, libl + branch_libs, main_lib)

  if needs_lib and target_lib not in _context['libs']:
    _context['libs'] = sorted(_context['libs'] + [target_lib])

  return props



def get_branch_text(branch: str | None) -> str:
  """Branch name for TEXT of a library: only safe characters, max. 50 characters"""

  text = f"OBI {UNSAFE_TEXT_CHARS.sub('_', branch or '')}"
  return text[:TEXT_MAX_LENGTH].rstrip()



def get_crt_lib_cmd(lib: str, context: dict, app_config: dict) -> str:
  """Command to create a branch library if it doesn't exist (global.cmds.crt-branch-lib)"""

  # The name ends up in a shell command
  if not LIB_NAME_PATTERN.fullmatch(lib):
    raise BranchBuildError(f"Invalid branch library name '{lib}'")

  cmd = app_config.get('global', {}).get('cmds', {}).get('crt-branch-lib') or DEFAULT_CRT_LIB_CMD

  return cmd.replace('$(LIB)', lib).replace('$(BRANCH_TEXT)', get_branch_text(context.get('branch')))



def get_libs_to_create(context: dict | None) -> list[str]:
  """Branch libraries of a compile list's build context, which `run` has to create"""

  if not isinstance(context, dict) or context.get('mode') != MODE_BRANCH:
    return []

  return list(context.get('libs', []))
