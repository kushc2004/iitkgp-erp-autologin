"""Cross-platform helpers: open a URL in the chosen browser, copy text.

Everything here degrades gracefully - if the requested browser or a
clipboard tool is missing, the caller gets a sensible fallback instead of
a crash.
"""

import os
import platform
import shutil
import subprocess
import webbrowser

SYSTEM = platform.system()  # 'Darwin', 'Windows' or 'Linux'


class BrowserNotFound(RuntimeError):
    """The requested browser is not installed on this machine."""


# Known browser aliases and where each usually lives per OS.
_KNOWN_BROWSERS = {
    'brave': {
        'Darwin': ['/Applications/Brave Browser.app',
                   os.path.expanduser('~/Applications/Brave Browser.app')],
        'Windows': [r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe',
                    r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
                    r'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe'],
        'Linux': ['brave-browser', 'brave'],
    },
    'chrome': {
        'Darwin': ['/Applications/Google Chrome.app',
                   os.path.expanduser('~/Applications/Google Chrome.app')],
        'Windows': [r'%PROGRAMFILES%\Google\Chrome\Application\chrome.exe',
                    r'%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe',
                    r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'],
        'Linux': ['google-chrome', 'google-chrome-stable', 'chromium'],
    },
    'chromium': {
        'Darwin': ['/Applications/Chromium.app'],
        'Windows': [r'%LOCALAPPDATA%\Chromium\Application\chrome.exe',
                    r'%PROGRAMFILES%\Chromium\Application\chrome.exe'],
        'Linux': ['chromium', 'chromium-browser'],
    },
    'edge': {
        'Darwin': ['/Applications/Microsoft Edge.app'],
        'Windows': [r'%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe',
                    r'%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe'],
        'Linux': ['microsoft-edge', 'microsoft-edge-stable'],
    },
    'firefox': {
        'Darwin': ['/Applications/Firefox.app'],
        'Windows': [r'%PROGRAMFILES%\Mozilla Firefox\firefox.exe',
                    r'%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe'],
        'Linux': ['firefox', 'firefox-esr'],
    },
}


def _locate_known(key):
    """Find an installed known browser; returns its command prefix or None."""
    candidates = _KNOWN_BROWSERS[key][SYSTEM]
    if SYSTEM == 'Darwin':
        for app in candidates:
            if os.path.isdir(app):
                return ['open', '-a', app]
    elif SYSTEM == 'Windows':
        for pattern in candidates:
            path = os.path.expandvars(pattern)
            if os.path.isfile(path):
                return [path]
    else:  # Linux and everything else
        for name in candidates:
            binary = shutil.which(name)
            if binary:
                return [binary]
    return None


def find_browser(choice):
    """Return the argument list that opens a URL in the requested browser.

    Returns ``None`` when the system default should be used.  Raises
    :class:`BrowserNotFound` when a specific browser was requested but is
    not installed.
    """
    key = (choice or '').strip().strip('"\'').lower()
    if key in ('', 'default', 'system'):
        return None

    if key in _KNOWN_BROWSERS:
        command = _locate_known(key)
        if command is None:
            raise BrowserNotFound(
                f'{key.title()} was not found on this {SYSTEM} system')
        return command

    # Anything else is treated as a path to a browser executable (or a
    # macOS .app bundle), falling back to $PATH lookup by name.
    path = os.path.expandvars(os.path.expanduser((choice or '').strip()))
    if SYSTEM == 'Darwin' and path.endswith('.app'):
        if os.path.isdir(path):
            return ['open', '-a', path]
        raise BrowserNotFound(f'No .app bundle at {path!r}')
    if os.path.isfile(path):
        return [path]
    binary = shutil.which(path)
    if binary:
        return [binary]
    raise BrowserNotFound(f'No browser executable found at {path!r}')


def _open_default(url):
    if SYSTEM == 'Darwin':
        subprocess.run(['open', url], check=False)
    elif SYSTEM == 'Windows':
        os.startfile(url)  # type: ignore[attr-defined]  # Windows only
    elif shutil.which('xdg-open'):
        subprocess.run(['xdg-open', url], check=False)
    else:
        webbrowser.open(url)


def open_url(url, choice='default'):
    """Open *url* in the chosen browser, falling back to the default one.

    Returns the display name of the browser used, or ``None`` for the
    system default.
    """
    try:
        command = find_browser(choice)
    except BrowserNotFound as error:
        print(f'{error} - using the default browser instead.')
        command = None

    if command is None:
        _open_default(url)
        return None

    label = os.path.basename(command[-1])
    if label.endswith('.app'):
        label = label[:-4]

    result = subprocess.run(command + [url], check=False)
    if result.returncode != 0:
        print(f'{label} did not accept the URL - using the default browser.')
        _open_default(url)
        return None
    return label


def copy_to_clipboard(text):
    """Best-effort clipboard copy. Returns True on success."""
    data = text.encode('utf-8')
    try:
        if SYSTEM == 'Darwin':
            subprocess.run(['pbcopy'], input=data, check=True)
            return True
        if SYSTEM == 'Windows':
            subprocess.run(['clip'], input=data, check=True)
            return True
        for args in (['wl-copy'], ['xclip', '-selection', 'clipboard']):
            if shutil.which(args[0]):
                subprocess.run(args, input=data, check=True)
                return True
    except (OSError, subprocess.CalledProcessError):
        pass
    return False
