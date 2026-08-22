#!/usr/bin/env python3
"""Sign in to the IIT KGP ERP portal and open it, already logged in, in Brave."""

import logging
import subprocess
import sys
import webbrowser

import erpcreds
from erplogin import ErpLoginError, login
from erplogin.endpoints import HOMEPAGE_URL

BRAVE_APP = '/Applications/Brave Browser.app'


def open_in_browser(url):
    """Open url in Brave when available, else the default browser."""
    try:
        subprocess.run(['open', '-a', BRAVE_APP, url], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print('Brave not found - opening the default browser instead.')
        webbrowser.open(url)


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

    # The token must be presented by the browser first; the clipboard copy is
    # a fallback for the "Paste token & sign in" button of the extension.
    try:
        subprocess.run(['pbcopy'], input=sso_token.encode(), check=True)
        print('ssoToken copied to clipboard. If ERP still shows the login '
              'page, click the ERP Session Helper extension and choose '
              '"Paste token & sign in".')
    except (OSError, subprocess.CalledProcessError):
        pass

    open_in_browser(url)
    return 0


if __name__ == '__main__':
    sys.exit(main())
