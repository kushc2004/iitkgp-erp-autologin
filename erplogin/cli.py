"""Command-line interface: the ``erp-login`` command (and open_erp.py)."""

import argparse
import getpass
import logging
import os
import sys

from . import config
from . import desktop
from .core import ErpLoginError, login
from .endpoints import HOMEPAGE_URL


def _ask(prompt, default='', secret=False):
    getter = getpass.getpass if secret else input
    suffix = f' [{default}]' if default else ''
    answer = getter(f'{prompt}{suffix}: ')
    return answer.strip() or default


def run_setup():
    """Interactive first-run wizard; returns a loaded credentials module."""
    path = config.credentials_path()
    os.makedirs(config.config_dir(), exist_ok=True)

    print('Setting up IIT KGP ERP auto-login.\n')
    fields = {
        'roll_number': _ask('Roll number'),
        'password': _ask('ERP password', secret=True),
        'browser': _ask('Browser to open ERP in '
                        '(default/brave/chrome/chromium/edge/firefox)',
                        'default').lower(),
        'questions': [],
        'email': '',
        'app_password': '',
    }
    print('\nYour security question can be left out - ERP rotates through a '
          'few questions, and every answer you type during a login is saved '
          'automatically once that login succeeds.')
    while True:
        question = _ask('Security question (blank to finish)')
        if not question:
            break
        fields['questions'].append((question, _ask('Its answer')))

    fields['email'] = _ask('\nGmail address receiving the OTP '
                           '(blank = type OTP manually)')
    if fields['email']:
        fields['app_password'] = _ask('Google app password '
                                      '(myaccount.google.com/apppasswords)',
                                      secret=True)

    config.write_credentials(path, fields)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    print(f'\nSaved credentials to {path}')
    return config.load_credentials_file(path)


def _remember_answer(creds):
    """Callback factory: persist proven security answers for next time."""
    def on_learned(question, answer):
        if config.save_security_answer(creds, question, answer):
            stored = len(config.load_credentials_file(
                creds._credentials_file).SECURITY_QUESTIONS_ANSWERS)
            print(f'\nSaved the answer for "{question}" '
                  f'({stored} question(s) remembered so far).')
    return on_learned


def main(argv=None):
    from . import __version__
    parser = argparse.ArgumentParser(
        prog='erp-login',
        description='Sign in to the IIT KGP ERP portal and open it, '
                    'already logged in, in your browser.')
    parser.add_argument('--setup', action='store_true',
                        help='(re)configure credentials interactively')
    parser.add_argument('--no-open', action='store_true',
                        help='log in but do not open the browser; '
                             'print the URL instead')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__}')
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s:%(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    try:
        creds = None
        if not args.setup:
            creds = config.load_credentials()
        if creds is None:
            creds = run_setup()

        _, sso_token = login(creds, storage_file=config.session_path(),
                             on_learned=_remember_answer(creds))
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled.')
        return 130
    except ErpLoginError as error:
        print(f'ERP login failed: {error}', file=sys.stderr)
        return 1

    url = f'{HOMEPAGE_URL}?ssoToken={sso_token}'
    print(f'Opening ERP as {creds.ROLL_NUMBER}: {url}')

    # Presenting the ssoToken spends it, so the browser must be the first
    # client to open this URL. The clipboard copy feeds the extension's
    # "Paste token & sign in" fallback button.
    if desktop.copy_to_clipboard(sso_token):
        print('ssoToken copied to clipboard. If ERP still shows the login '
              'page, click the ERP Session Helper extension and choose '
              '"Paste token & sign in".')

    if args.no_open:
        return 0

    used = desktop.open_url(url, getattr(creds, 'BROWSER', 'default'))
    print(f'ERP opened in {used}.' if used
          else 'ERP opened in your default browser.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
