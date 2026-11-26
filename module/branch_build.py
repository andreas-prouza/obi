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



#################################################################
# Removing branch libraries (action branch_libs)
#################################################################

QSH = '/QOpenSys/usr/bin/qsh'
SQL_TIMEOUT = 300
SQL_LIB_MARKER = 'OBILIB|'
SQL_SIZE_MARKER = 'OBISIZE|'
SAFE_LIKE_PREFIX = re.compile(r'[A-Za-z0-9#@]*')

SQL_LIST_LIBS = ("SELECT '" + SQL_LIB_MARKER + "' CONCAT TRIM(OBJNAME) CONCAT '|' "
                 "CONCAT COALESCE(VARCHAR_FORMAT(OBJCREATED, 'YYYY-MM-DD HH24:MI:SS'), '') CONCAT '|' "
                 "CONCAT COALESCE(VARCHAR_FORMAT(LAST_USED_TIMESTAMP, 'YYYY-MM-DD'), '') CONCAT '|' "
                 "CONCAT TRIM(OBJOWNER) CONCAT '|' CONCAT COALESCE(TRIM(OBJTEXT), '') AS L "
                 "FROM TABLE(QSYS2.OBJECT_STATISTICS('*ALL', '*LIB')) X WHERE OBJNAME LIKE '{prefix}%'")

SQL_LIB_SIZES = ("SELECT '" + SQL_SIZE_MARKER + "' CONCAT L.N CONCAT '|' CONCAT VARCHAR(I.LIBRARY_SIZE) AS S "
                 "FROM (VALUES {values}) L(N), LATERAL (SELECT LIBRARY_SIZE FROM TABLE(QSYS2.LIBRARY_INFO(L.N)) Z) I")



def get_active_config(app_config: dict) -> dict:
  """The validated `[branch-build]` section. Raises BranchBuildError if the feature is off"""

  config = get_config(app_config)
  if config is None:
    raise BranchBuildError("Branch build is not configured: the config has no [branch-build] section, or it is disabled")

  validate_config(config)
  return config



def get_first_group(pattern: str) -> str | None:
  """Text of the first capturing group of a regular expression, e.g. `\\d+` of `(?i)\\bproj[-_](\\d+)`"""

  i = 0
  start = None
  depth = 0
  in_class = False

  while i < len(pattern):
    char = pattern[i]
    if char == '\\':
      i += 2
      continue
    if in_class:
      in_class = char != ']'
    elif char == '[':
      in_class = True
      # `]` right after `[` or `[^` is a character
      if pattern[i + 1:i + 2] == ']' or pattern[i + 1:i + 3] == '^]':
        i += 2 if pattern[i + 1] == ']' else 3
        continue
    elif char == '(':
      if start is None:
        is_capturing = not pattern.startswith('(?', i) or pattern.startswith('(?P<', i)
        if is_capturing:
          start = pattern.index('>', i) + 1 if pattern.startswith('(?P<', i) else i + 1
          depth = 1
      else:
        depth += 1
    elif char == ')' and start is not None:
      depth -= 1
      if depth == 0:
        return pattern[start:i]
    i += 1

  return None



def get_ticket_regex(config: dict) -> str:
  """Regex for the ticket part of a library name: the ticket group of `ticket-pattern`, otherwise letters and digits"""

  group = get_first_group(config['ticket-pattern'])
  if group:
    try:
      re.compile(group)
      return f"(?:{group})"
    except re.error:
      pass

  return '[A-Za-z0-9]+'



def get_lib_name_pattern(config: dict) -> re.Pattern:
  """Regular expression for the names `lib-name` can produce, with the groups `env` and `ticket`"""

  regex = ''
  ticket_used = False

  for part in re.split(r'(\$\(ENV\)|\$\(TICKET\))', config['lib-name']):
    if part == '$(ENV)':
      envs = sorted({str(env) for env in config.get('env', {}).values()}, key=len, reverse=True)
      regex += f"(?P<env>{'|'.join(re.escape(env) for env in envs)})"
    elif part == '$(TICKET)':
      regex += '(?P=ticket)' if ticket_used else f'(?P<ticket>{get_ticket_regex(config)})'
      ticket_used = True
    else:
      regex += re.escape(part)

  return re.compile(regex, re.IGNORECASE)



def get_protected_libs(app_config: dict) -> set[str]:
  """Libraries that are never branch libraries: main and production libraries of the config"""

  config = get_config(app_config) or {}
  general_settings = app_config.get('global', {}).get('settings', {}).get('general', {})
  lib_mapping = general_settings.get('TARGET_LIB_MAPPING', {}) or {}

  libs = {str(lib) for lib in lib_mapping.keys()} | {str(lib) for lib in lib_mapping.values()}
  libs |= {str(lib) for lib in config.get('env', {}).keys()}

  return {lib.lower() for lib in libs}



def parse_branch_lib_name(name: str, app_config: dict) -> dict | None:
  """ENV and ticket of a branch library name. None if it isn't one"""

  if not isinstance(name, str) or not LIB_NAME_PATTERN.fullmatch(name):
    return None

  if name.lower() in get_protected_libs(app_config):
    return None

  match = get_lib_name_pattern(get_active_config(app_config)).fullmatch(name)
  if match is None:
    return None

  groups = match.groupdict()
  return {'env': (groups.get('env') or '').upper(), 'ticket': groups.get('ticket')}



def escape_double_quoted(text: str) -> str:
  """Escape a text for a double-quoted shell string"""

  for char in ['\\', '"', '$', '`']:
    text = text.replace(char, f'\\{char}')
  return text



def run_db2(sql: str) -> list[str]:
  """Run a SELECT with the db2 utility of QShell. Returns the output lines

  Raises:
      BranchBuildError: If the statement fails
  """

  try:
    s = subprocess.run([QSH, '-c', f'db2 "{escape_double_quoted(sql)}"'], capture_output=True, text=True,
                       timeout=SQL_TIMEOUT, check=False)
  except OSError as e:
    raise BranchBuildError(f"QShell ({QSH}) is not available, the action runs on IBM i only: {e}")
  except subprocess.TimeoutExpired:
    raise BranchBuildError(f"SQL statement didn't finish within {SQL_TIMEOUT} seconds")
  lines = s.stdout.splitlines()

  # db2 shows SQL errors on stdout and doesn't always set the exit code
  if s.returncode != 0 or not any('RECORD(S) SELECTED' in line for line in lines):
    raise BranchBuildError(f"SQL statement failed: {(s.stdout + s.stderr).strip()[-1000:]}")

  return lines



def get_lib_sizes(names: list[str], run_sql) -> dict:

  if len(names) == 0:
    return {}

  # The names are valid library names (no quotes)
  values = ', '.join(f"('{name.upper()}')" for name in names)
  sizes = {}

  for line in run_sql(SQL_LIB_SIZES.format(values=values)):
    line = line.strip()
    if not line.startswith(SQL_SIZE_MARKER):
      continue
    name, size = line[len(SQL_SIZE_MARKER):].split('|', 1)
    if size.strip().isdigit():
      sizes[name.strip().upper()] = int(size.strip())

  return sizes



def list_branch_libs(app_config: dict, run_sql=run_db2) -> list[dict]:
  """All branch libraries on the system, sorted by ticket and name

  Returns:
      list: [{'name', 'ticket', 'env', 'text', 'created', 'last_used', 'owner', 'size'}]
  """

  config = get_active_config(app_config)

  # Narrow the SQL down to the fixed beginning of lib-name, if it's safe to put into the statement
  prefix = config['lib-name'].split('$(', 1)[0]
  if not SAFE_LIKE_PREFIX.fullmatch(prefix):
    prefix = ''

  libs = []
  for line in run_sql(SQL_LIST_LIBS.format(prefix=prefix.upper())):
    line = line.strip()
    if not line.startswith(SQL_LIB_MARKER):
      continue

    # The text is last: it may contain '|'
    name, created, last_used, owner, text = line[len(SQL_LIB_MARKER):].split('|', 4)
    lib_info = parse_branch_lib_name(name, app_config)
    if lib_info is None:
      continue

    libs.append({'name': name.upper(), **lib_info, 'text': text.strip(), 'created': created or None,
                 'last_used': last_used or None, 'owner': owner, 'size': None})

  sizes = get_lib_sizes([lib['name'] for lib in libs], run_sql)
  for lib in libs:
    lib['size'] = sizes.get(lib['name'])

  return sorted(libs, key=lambda lib: (lib['ticket'] or '', lib['name']))



def delete_branch_libs(names: list[str], app_config: dict, run_cmd, run_sql=run_db2) -> dict:
  """Delete branch libraries

  Every name has to be a branch library name (lib-name, not a main or production library) and has to exist.
  A library that can't be deleted (e.g. in use) is reported; the others are still deleted.

  Args:
      names (list): Library names
      app_config (dict): Application config
      run_cmd (callable): Runs a shell command, returns {'exit-code', 'stdout', 'stderr', 'joblog'} (run_cmds.run_pase_cmd)
      run_sql (callable): Runs a SELECT, returns the output lines

  Returns:
      dict: {'deleted': [...], 'failed': [{'name', 'message'}]}
  """

  get_active_config(app_config)

  names = [name.strip() for name in names if name.strip() != '']
  if len(names) == 0:
    raise BranchBuildError("No library to delete")

  # Checked before anything is deleted
  invalid = [name for name in names if parse_branch_lib_name(name, app_config) is None]
  if invalid:
    raise BranchBuildError(f"Not a branch library: {', '.join(invalid)}. Nothing was deleted")

  existing = {lib['name'] for lib in list_branch_libs(app_config, run_sql)}
  deleted = []
  failed = []

  for name in dict.fromkeys(name.upper() for name in names):
    if name not in existing:
      failed.append({'name': name, 'message': 'Library not found'})
      continue

    logging.info(f"Delete branch library {name}")
    result = run_cmd(f'cl -v "DLTLIB LIB({name})"')
    if result['exit-code'] != 0 or result['stderr'] != '':
      failed.append({'name': name, 'message': (result['stderr'] or result['stdout']).strip()})
      continue

    deleted.append(name)

  return {'deleted': deleted, 'failed': failed}



def get_libs_to_create(context: dict | None) -> list[str]:
  """Branch libraries of a compile list's build context, which `run` has to create"""

  if not isinstance(context, dict) or context.get('mode') != MODE_BRANCH:
    return []

  return list(context.get('libs', []))
