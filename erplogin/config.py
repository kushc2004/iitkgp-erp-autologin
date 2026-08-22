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
    module._credentials_file = path
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


def write_credentials(path, fields):
    """Write a credentials.py file readable only by the current user."""
    lines = [
        '# Managed by erp-login. Edit freely.',
        '# Contains your ERP password - do not share or commit this file.',
        '',
        f'ROLL_NUMBER = {fields["roll_number"]!r}',
        f'PASSWORD = {fields["password"]!r}',
        f'BROWSER = {fields["browser"]!r}',
        '',
        'SECURITY_QUESTIONS_ANSWERS = {',
    ]
    for question, answer in fields['questions']:
        lines.append(f'    {question!r}: {answer!r},')
    lines += [
        '}',
        '',
        f'EMAIL_ADDRESS = {fields["email"]!r}',
        f'EMAIL_APP_PASSWORD = {fields["app_password"]!r}',
        '',
    ]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as file:
        file.write('\n'.join(lines))


def save_security_answer(creds, question, answer):
    """Add a proven question->answer pair to the credentials file.

    ERP rotates through a handful of security questions; each one answered
    correctly once is stored so that login is never asked for it again.
    Returns True when the file was updated.
    """
    path = getattr(creds, '_credentials_file', None)
    if not path or not os.path.isfile(path):
        return False

    source = load_credentials_file(path)
    questions = dict(getattr(source, 'SECURITY_QUESTIONS_ANSWERS', {}) or {})
    if any(key.casefold() == question.casefold() for key in questions):
        return False
    questions[question] = answer

    write_credentials(path, {
        'roll_number': source.ROLL_NUMBER,
        'password': source.PASSWORD,
        'browser': getattr(source, 'BROWSER', 'default'),
        'questions': sorted(questions.items()),
        'email': getattr(source, 'EMAIL_ADDRESS', ''),
        'app_password': getattr(source, 'EMAIL_APP_PASSWORD', ''),
    })
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return True
