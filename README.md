# IIT KGP ERP Auto-Login

One-click sign-in for the [IIT KGP ERP portal](https://erp.iitkgp.ac.in):
the extension performs the whole SSO handshake for you, reads the email OTP
by itself, opens ERP already logged in, then keeps the session alive.
Works on **Windows, macOS and Linux** in any Chromium browser
(Brave, Chrome, Edge).

Prefer a terminal tool? The same flow also ships as a Python CLI
(`erp-login`) — see [The command-line tool](#the-command-line-tool-alternative).

```
click "Sign in"  ─►  OTP read from your Gmail  ─►  ERP tab opens, logged in
```

## Which one should I use?

| | Browser extension | Python CLI |
|---|---|---|
| Setup | Load the folder once, fill two fields | `pip install` + config file |
| OTP | Automatic (Gmail web feed) or typed by hand | Automatic (IMAP + app password) or manual |
| Needs | Any Chromium browser, signed into your Gmail | Python 3.9+, an app password |
| Keeps session alive | Yes, built in | No |

Both use the identical SSO handshake and learn your security answers the
same way.

## The browser extension (recommended)

### Install

1. Download or clone this repo.
2. Open the extensions page in your Chromium browser:
   `brave://extensions`, `chrome://extensions`, or `edge://extensions`.
3. Enable **Developer mode** → **Load unpacked**.
4. Select the `extension/` folder of this repo.

### Set up

Click the toolbar icon:

1. Open **Settings** inside the popup.
2. Enter your **roll number** and **ERP password**, then **Save**.
3. That's all. Leave *Gmail account index* at `0` unless several Gmail
   accounts are signed into this browser and the OTP doesn't turn up.

Security questions need no setup: when ERP asks one you haven't answered
before, type it once — it's saved automatically **after that login
succeeds**, so wrong guesses are never remembered. ERP rotates through a
few questions; each gets learned on first encounter, after which sign-in
is fully hands-off.

### Sign in

Click **Sign in to ERP**. You'll see live progress in the popup:

```
Fetching the SSO session token...
Fetching your security question...
Asking ERP to send the OTP...
Waiting for the OTP mail...
Got the OTP.
Signed in! Opening ERP...
```

The OTP is read from the Gmail feed of the account signed into this
browser (no app password, no Google Cloud project). It polls for about
half a minute; if the feed hasn't caught up you can hit **Mail arrived -
check now** for an instant re-scan or simply type the six digits
yourself — login never dead-ends.

While any ERP tab is open, the extension pings `keepAlive.htm` every
20 minutes so the session doesn't idle out.

### Notes

- The OTP mails stay in your inbox; extensions can't delete mail without
  heavyweight Google API access, which would defeat the zero-setup goal.
- Gmail's feed only lists **unread** mail. The extension snapshots it
  before requesting the OTP, so an older unread OTP is never mistaken for
  the fresh one.
- Removing the extension wipes everything it stored (roll number,
  password, learned answers).

## The command-line tool (alternative)

Everything below duplicates the extension's flow in a terminal-friendly
form, including fully-automatic IMAP OTP reading — useful for scripts or
if you prefer not to hand your ERP password to a browser extension.

### Install

```bash
pip install iitkgp-erp-autologin
erp-login --setup     # one-time wizard
erp-login             # every login after that
```

Credentials are stored in a user-private file outside any repo:

| OS | Config directory |
|---|---|
| Windows | `%APPDATA%\erp-autologin\credentials.py` |
| macOS | `~/Library/Application Support/erp-autologin/credentials.py` |
| Linux | `~/.config/erp-autologin/credentials.py` (or `$XDG_CONFIG_HOME`) |

Re-run `erp-login --setup` to change anything; use `--no-open` to log in
without launching a browser.

### Or from a source checkout

**Windows:**

```bat
git clone https://github.com/kushc2004/iitkgp-erp-autologin.git
cd iitkgp-erp-autologin
py -m venv venv
venv\Scripts\pip install -r requirements.txt
copy erpcreds.example.py erpcreds.py
notepad erpcreds.py
open_erp.bat
```

**macOS / Linux:**

```bash
git clone https://github.com/kushc2004/iitkgp-erp-autologin.git
cd iitkgp-erp-autologin
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp erpcreds.example.py erpcreds.py
nano erpcreds.py            # or any editor
./open_erp.sh               # macOS also: double-click open_erp.command
```

Fields for `erpcreds.py`:

| Field | What goes there |
|---|---|
| `ROLL_NUMBER` | Your roll number |
| `PASSWORD` | Your ERP password |
| `BROWSER` | `"default"`, `"brave"`, `"chrome"`, `"chromium"`, `"edge"`, `"firefox"`, or a full executable path |
| `SECURITY_QUESTIONS_ANSWERS` | Optional — answers are learned automatically |
| `EMAIL_ADDRESS` | Mailbox receiving ERP OTP mails |
| `EMAIL_APP_PASSWORD` | A 16-character Google app password |

#### Pick your browser (CLI)

| Value | Behaviour |
|---|---|
| `"default"` | System default browser (`open` / `start` / `xdg-open`) |
| named browser | Auto-located in its standard install location on your OS |
| full path | Uses exactly that executable |

If a named browser isn't installed, the script says so and falls back to
the system default.

#### Automatic OTP — create a Gmail app password (CLI only)

1. Turn on 2-Step Verification: <https://myaccount.google.com/signinoptions/two-step-verification>
2. Create an app password: <https://myaccount.google.com/apppasswords>
3. Paste it as `EMAIL_APP_PASSWORD`, set `EMAIL_ADDRESS` to the same mailbox.

Blank both out to type OTPs manually instead — everything else works
identically.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Extension: "Could not read the OTP automatically" | Make sure the Gmail account that receives ERP mail is signed into this browser, and try the right *Gmail account index* in Settings if you have several accounts. Otherwise just type the OTP — login continues either way. |
| Extension: OTP lands in Spam/Promotions | Gmail's feed covers the inbox only. Mark such mails *not spam*, or enter the OTP manually. |
| Browser lands back on the ERP login page | Click **Sign in to ERP** again; the extension clears stale cookies first. In the CLI, rerun `erp-login`. |
| "Wrong security answer" | Check the answer; the key must match the question ERP shows you. |
| CLI: `Gmail login over IMAP failed` | App password wrong/revoked or IMAP disabled. Re-create it at <https://myaccount.google.com/apppasswords>, or blank out both email fields to type OTPs manually. |
| CLI: `Timed out waiting for the OTP mail` | OTP never arrived (check the inbox manually) or IMAP is slow — run again, or use manual mode. |
| Wrong-password error | Update `PASSWORD` in Settings / via `erp-login --setup`. |
| Nothing opens (CLI, Linux) | Install `xdg-utils` (`sudo apt install xdg-utils`). |

## Security notes

- The extension stores your credentials in the browser's local extension
  storage (`chrome.storage.local`) — never synced, never committed, wiped
  when the extension is removed.
- The CLI stores them in a user-private file outside any repo
  (`credentials.py` config directory, or a gitignored `erpcreds.py`),
  so nothing sensitive can be committed by accident.
- Everything runs locally; nothing is sent anywhere except
  `erp.iitkgp.ac.in` and Gmail.
- The CLI's app password grants mailbox access until you revoke it at
  <https://myaccount.google.com/apppasswords>. Revoke it if a machine is lost.
- On shared machines, sign out of ERP and remove the stored credentials.

## Credits

Request sequence based on the reverse-engineered ERP SSO flow popularised by
[proffapt/iitkgp-erp-login-pypi](https://github.com/proffapt/iitkgp-erp-login-pypi).
This repo is a self-contained rewrite: a zero-setup browser extension plus a
Python CLI, IMAP app-password OTP instead of Google OAuth, redirect-safe
token hand-off, cross-platform launchers, and session keep-alive.

## License

[MIT](LICENSE)
