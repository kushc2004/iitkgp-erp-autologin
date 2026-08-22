"""Locate and load per-user configuration on any operating system.

Two credential sources are supported, in this order of preference:

1. ``./erpcreds.py`` next to the caller - used when running from a source
   checkout, so the repo keeps working exactly as before.
2. ``credentials.py`` inside the platform config directory - what
   ``erp-login --setup`` creates for pip-installed usage:

   - Windows:  ``%APPDATA%\\erp-autologin\\credentials.py``
   - macOS:    ``~/Library/Application Support/erp-autologin/credentials.py``
   - Linux:    ``$XDG_CONFIG_HOME/erp-autologin/credentials.py``
               (or ``~/.config/erp-autologin/credentials.py``)

The cached ERP session (``.session``) lives in the same config directory.
"""

import importlib.util
import os

from .desktop import SYSTEM

CONFIG_DIRNAME = 'erp-autologin'
CREDENTIALS_FILENAME = 'credentials.py'
SESSION_FILENAME = '.session'
LOCAL_CREDENTIALS_NAME = 'erpcreds.py'


def config_dir():
    """Per-user directory that holds credentials.py and .session."""
    if SYSTEM == 'Windows':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
    elif SYSTEM == 'Darwin':
        base = os.path.expanduser('~/Library/Application Support')
    else:
        base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(base, CONFIG_DIRNAME)


def credentials_path():
    return os.path.join(config_dir(), CREDENTIALS_FILENAME)


def session_path():
    return os.path.join(config_dir(), SESSION_FILENAME)


def load_credentials_file(path):
    """Import a credentials file as a module-like object."""
    spec = importlib.util.spec_from_file_location('erp_autologin_credentials', path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not load credentials from {path!r}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_credentials():
    """Return the first credentials module found, or None."""
    local = os.path.join(os.getcwd(), LOCAL_CREDENTIALS_NAME)
    if os.path.isfile(local):
        return load_credentials_file(local)
    installed = credentials_path()
    if os.path.isfile(installed):
        return load_credentials_file(installed)
    return None
