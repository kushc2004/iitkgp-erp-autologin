# IIT KGP ERP Auto-Login

One-command sign-in for the [IIT KGP ERP portal](https://erp.iitkgp.ac.in):
the script logs in, fetches the email OTP by itself, and opens ERP in your
browser **already logged in** — no typing, no OTP copy-paste.
Works on **Windows, macOS and Linux**, and you choose which browser opens.

```
erp-login  ─►  OTP fetched from Gmail  ─►  your browser opens, logged in
```

## What it does

1. Performs the full SSO handshake (session token → security question →
   password + OTP) exactly like a browser does.
2. Reads the OTP mail automatically over Gmail IMAP using a Google
   **app password**, or falls back to asking you to type the OTP.
3. Opens `https://erp.iitkgp.ac.in/IIT_ERP3/?ssoToken=…` in the browser of
   your choice (Brave, Chrome, Edge, Firefox, Chromium, or your default).
   The ssoToken is handed over untouched so the first client to present it
   is the browser.
4. Caches valid tokens locally — reruns within the session's lifetime skip
   the whole login flow.
5. Ships with a tiny browser extension that keeps the ERP session alive
   (`keepAlive.htm` every 20 minutes) and can sign the browser in from the
   clipboard as a fallback.

## Requirements

| | |
|---|---|
| OS | Windows 10/11, macOS, or any modern Linux |
| Python | 3.9 or newer (`py --version` / `python3 --version`) |
| Mailbox | A Gmail-hosted account that receives the ERP OTP mail (your `@kgpian.iitkgp.ac.in` address) |
| Browser | Any; Chromium-based browsers (Brave/Chrome/Edge) also get the keep-alive extension |

No Google Cloud project is needed anywhere.

## Setup

### Option A — install with pip (recommended)

```bash
pip install iitkgp-erp-autologin
erp-login --setup     # one-time wizard
erp-login             # every login after that
```

The wizard asks for your roll number, password, preferred browser, security
question(s), and optionally the Gmail app password for automatic OTP reading.
It stores everything in a private file (permissions `600`) outside any repo:

| OS | Config directory |
|---|---|
| Windows | `%APPDATA%\erp-autologin\credentials.py` |
| macOS | `~/Library/Application Support/erp-autologin/credentials.py` |
| Linux | `~/.config/erp-autologin/credentials.py` (or `$XDG_CONFIG_HOME`) |

The cached ERP session (`.session`) lives right next to it. Re-run
`erp-login --setup` whenever you want to change something, and use
`erp-login --no-open` to log in without launching a browser.

Prefer editing by hand? Copy `erpcreds.example.py` from this repo to the
config path above as `credentials.py`.

### Option B — run from a source checkout

#### 1. Clone and install

**Windows (PowerShell or cmd):**

```bat
git clone https://github.com/kushc2004/iitkgp-erp-autologin.git
cd iitkgp-erp-autologin
py -m venv venv
venv\Scripts\pip install -r requirements.txt
```

**macOS / Linux (terminal):**

```bash
git clone https://github.com/kushc2004/iitkgp-erp-autologin.git
cd iitkgp-erp-autologin
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Only two packages are needed: `requests` and `beautifulsoup4`.
OTP reading uses Python's built-in `imaplib`.

#### 2. Add your credentials

```bash
# Windows
copy erpcreds.example.py erpcreds.py
notepad erpcreds.py

# macOS / Linux
cp erpcreds.example.py erpcreds.py
nano erpcreds.py        # or any editor
```

Fill in:

| Field | What goes there |
|---|---|
| `ROLL_NUMBER` | Your roll number |
| `PASSWORD` | Your ERP password |
| `BROWSER` | Which browser opens ERP — see [Pick your browser](#pick-your-browser) |
| `SECURITY_QUESTIONS_ANSWERS` | Your security question and answer |
| `EMAIL_ADDRESS` | The mailbox that receives ERP OTP mails (optional) |
| `EMAIL_APP_PASSWORD` | A 16-character Google app password (optional) |

Don't know the exact wording of your security question? Leave
`SECURITY_QUESTIONS_ANSWERS` empty — on the first run you'll be shown the
question, type the answer once, and the script prints a ready-made line to
paste into `erpcreds.py` for future runs:

```python
SECURITY_QUESTIONS_ANSWERS = {
    "what is your mothers name": "…",
}
```

Capitalisation doesn't matter; URL-encoding oddities are handled for you.

#### Pick your browser

Set `BROWSER` in `erpcreds.py` (or answer the prompt in `erp-login --setup`):

| Value | Behaviour |
|---|---|
| `"default"` | Opens with the system default browser (`open` / `start` / `xdg-open`) |
| `"brave"`, `"chrome"`, `"chromium"`, `"edge"`, `"firefox"` | Auto-locates that browser in its standard install location on your OS |
| full path | Uses exactly that executable — e.g. `/Applications/Vivaldi.app` (macOS), `C:\Program Files\Vivaldi\Application\vivaldi.exe` (Windows), `/usr/bin/vivaldi-stable` (Linux) |

If a named browser isn't installed, the script tells you and falls back to
the system default instead of failing.

Standard locations searched per browser:

- **Windows:** `%PROGRAMFILES%`, `%PROGRAMFILES(X86)%` and `%LOCALAPPDATA%`
  (e.g. `%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe`)
- **macOS:** `/Applications` and `~/Applications`
- **Linux:** whatever is on `$PATH` (`brave-browser`, `google-chrome`,
  `microsoft-edge`, `firefox`, …)

#### Automatic OTP — create a Gmail app password

No project, no consent screen, no OAuth files. One minute of setup:

1. Turn on 2-Step Verification for the account:
   <https://myaccount.google.com/signinoptions/two-step-verification>
2. Create an app password:
   <https://myaccount.google.com/apppasswords> → name it e.g. `erp-login`
   → copy the 16-character password.
3. Paste it into `EMAIL_APP_PASSWORD` in `erpcreds.py` and set
   `EMAIL_ADDRESS` to the same mailbox.

> If your Google Workspace org blocks app passwords, leave both fields blank
> — the script will simply print *"Enter the OTP"* and wait for you to type
> it. Everything else works identically.

#### Run it

| Platform | Run it |
|---|---|
| Installed package | `erp-login` |
| Windows | Double-click `open_erp.bat`, or run `venv\Scripts\python open_erp.py` |
| macOS | Double-click `open_erp.command` in Finder, or run `./open_erp.sh` |
| Linux | Run `./open_erp.sh` |

You should see the handshake log end with `Generated ssoToken`, then your
browser opens inside ERP. On later runs, while the session is still valid,
the cached tokens finish everything instantly.

## Keep-alive extension (Chromium browsers)

ERP sessions expire quickly when idle. The bundled extension pings
`keepAlive.htm` every 20 minutes whenever an ERP tab is open, and can also
sign the browser in from your clipboard if a hand-off ever fails:

1. Open the extensions page in your Chromium browser:
   `brave://extensions`, `chrome://extensions`, or `edge://extensions`
2. Enable **Developer mode** → **Load unpacked**
3. Select the `keepalive_extension` folder from this repo

Buttons in the popup:

- **Paste token & sign in** — reads the ssoToken the script copies to your
  clipboard, clears stale ERP cookies, sets the fresh one as a cookie, and
  opens ERP. This bypasses URL-parameter quirks completely.
- **Open ERP login** — just opens the portal.

If you change extension code, hit its reload icon on the extensions page.
(Firefox users: the script works fine without the extension.)

## Troubleshooting

| Symptom | Fix |
|---|---|
| Browser lands back on the ERP login page | Click the extension's **Paste token & sign in**. If it persists, clear cookies for `erp.iitkgp.ac.in` (padlock in the address bar → Site settings → Delete data) and run again. |
| "…was not found on this … system - using the default browser" | Install the named browser, or change `BROWSER` to another value/full path from [Pick your browser](#pick-your-browser). |
| Nothing opens on Linux | Install `xdg-utils` (`sudo apt install xdg-utils`), which provides `xdg-open`. |
| `Invalid security question answer` | Check the answer in your credentials file; make sure the key matches the question ERP shows you. |
| `Gmail login over IMAP failed` | App password wrong/revoked, or IMAP disabled for the account. Re-create the app password, or blank out both email fields to type OTPs manually. |
| `Timed out waiting for the OTP mail` | OTP never arrived (check the inbox manually) or IMAP is slow — run again, or use manual mode. |
| `Invalid OTP` | The previous attempt's OTP mail was picked up instead of the new one; run again. |
| Wrong-password error | Update `PASSWORD` via `erp-login --setup` or in your credentials file. |

## Security notes

- Credentials live in a user-private file outside the repo
  (`credentials.py` in the config directory, or a gitignored `erpcreds.py`
  in checkouts) — nothing sensitive can be committed by accident.
- Everything runs locally; nothing is sent anywhere except `erp.iitkgp.ac.in`
  and Gmail's IMAP server.
- The app password grants mailbox access only until you revoke it at
  <https://myaccount.google.com/apppasswords>. Revoke it if a machine is lost.
- On shared machines, delete the `.session` file in the config directory
  after use.

## Publishing / building the package yourself

```bash
pip install -U build twine
python -m build            # creates dist/*.whl and dist/*.tar.gz
twine upload dist/*        # pushes to PyPI
```

Test first on <https://test.pypi.org> with `twine upload --repository testpypi dist/*`,
then install from there to verify.

## Credits

Request sequence based on the reverse-engineered ERP SSO flow popularised by
[proffapt/iitkgp-erp-login-pypi](https://github.com/proffapt/iitkgp-erp-login-pypi).
This repo is a self-contained rewrite: single small package, IMAP app-password
OTP instead of Google OAuth, redirect-safe token hand-off to the browser,
cross-platform launchers with browser selection, and a keep-alive extension.

## License

[MIT](LICENSE)
