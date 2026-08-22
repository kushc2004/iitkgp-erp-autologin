#!/usr/bin/env python3
"""Sign in to the IIT KGP ERP portal and open it, already logged in.

Works on macOS, Windows and Linux. The browser to open is configured via
BROWSER in erpcreds.py ("default", "brave", "chrome", "edge", "firefox",
or a full path to a browser executable).
"""

import logging
import sys

import erpcreds
from erplogin import ErpLoginError, login
from erplogin import desktop
from erplogin.endpoints import HOMEPAGE_URL


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s:%(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    try:
        _, sso_token = login(erpcreds, storage_file='.session')
    except ErpLoginError as error:
        print(f'ERP login failed: {error}', file=sys.stderr)
        return 1

    url = f'{HOMEPAGE_URL}?ssoToken={sso_token}'
    print(f'Opening ERP as {erpcreds.ROLL_NUMBER}: {url}')

    # Presenting the ssoToken spends it, so the browser must be the first
    # client to open this URL. The clipboard copy feeds the extension's
    # "Paste token & sign in" fallback button.
    if desktop.copy_to_clipboard(sso_token):
        print('ssoToken copied to clipboard. If ERP still shows the login '
              'page, click the ERP Session Helper extension and choose '
              '"Paste token & sign in".')

    used = desktop.open_url(url, getattr(erpcreds, 'BROWSER', 'default'))
    print(f'ERP opened in {used}.' if used else 'ERP opened in your default browser.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
