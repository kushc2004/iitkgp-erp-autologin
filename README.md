# IIT KGP ERP Auto-Login

One-command sign-in for the [IIT KGP ERP portal](https://erp.iitkgp.ac.in):
the script logs in, fetches the email OTP by itself, and opens ERP in your
browser **already logged in** — no typing, no OTP copy-paste.

```
double-click open_erp.command  ─►  OTP fetched from Gmail  ─►  Brave opens, logged in
```

## What it does

1. Performs the full SSO handshake (session token → security question →
   password + OTP) exactly like a browser does.
2. Reads the OTP mail automatically over Gmail IMAP using a Google
   **app password**, or falls back to asking you to type the OTP.
3. Opens `https://erp.iitkgp.ac.in/IIT_ERP3/?ssoToken=…` in **Brave**
   (falls back to your default browser). The ssoToken is handed to the
   browser untouched so the first client to present it is the browser.
4. Caches valid tokens in a local `.session` file — reruns within the
   session's lifetime skip the whole login flow.
5. Ships with a tiny browser extension that keeps the ERP session alive
   (`keepAlive.htm` every 20 minutes) and can sign the browser in from the
   clipboard as a fallback.

## Requirements

- macOS (for double-click launch and opening Brave; the Python script also
  works on Linux if you open the printed URL yourself)
- Python 3.9+
- A Gmail-hosted account that receives the ERP OTP mail
  (your `@kgpian.iitkgp.ac.in` address)
- [Brave](https://brave.com/) installed at `/Applications/Brave Browser.app`
  (optional)

No Google Cloud project is needed anywhere.

## Setup

### 1. Clone and install

```bash
git clone https://github.com/kushc2004/iitkgp-erp-autologin.git
cd iitkgp-erp-autologin
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Only two packages are needed: `requests` and `beautifulsoup4`.
OTP reading uses Python's built-in `imaplib`.

### 2. Add your credentials

```bash
cp erpcreds.example.py erpcreds.py
open -e erpcreds.py     # or edit in any editor
```

Fill in:

| Field | What goes there |
|---|---|
| `ROLL_NUMBER` | Your roll number |
| `PASSWORD` | Your ERP password |
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

### 3. Automatic OTP — create a Gmail app password

This replaces the old Google-Cloud-OAuth approach entirely: no project, no
consent screen, no `credentials.json`, no `token.json`. One minute of setup:

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

### 4. First run

```bash
./open_erp.command        # or: venv/bin/python open_erp.py
```

You should see the handshake log end with `Generated ssoToken`, then Brave
opens inside ERP. On later runs, while the session is still valid, the
script reuses `.session` and finishes instantly.

## Keep-alive extension (recommended)

ERP sessions expire quickly when idle. The bundled extension pings
`keepAlive.htm` every 20 minutes whenever an ERP tab is open, and can also
sign the browser in from your clipboard if a hand-off ever fails:

1. Open `brave://extensions` (or `chrome://extensions`)
2. Enable **Developer mode** → **Load unpacked**
3. Select the `keepalive_extension` folder from this repo

Buttons in the popup:

- **Paste token & sign in** — reads the ssoToken that `open_erp.py` copies
  to your clipboard, clears stale ERP cookies, sets the fresh one as a
  cookie, and opens ERP. This bypasses URL-parameter quirks completely.
- **Open ERP login** — just opens the portal.

If you change extension code, hit its reload icon on the extensions page.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Browser lands back on the ERP login page | Click the extension's **Paste token & sign in**. If it persists, clear cookies for `erp.iitkgp.ac.in` (padlock in the address bar → Site settings → Delete data) and run again. |
| `Invalid security question answer` | Check the answer in `erpcreds.py`; make sure the key matches the question ERP shows you. |
| `Gmail login over IMAP failed` | App password wrong/revoked, or IMAP disabled for the account. Re-create the app password, or blank out both email fields to type OTPs manually. |
| `Timed out waiting for the OTP mail` | OTP never arrived (check the inbox manually) — increase `timeout` or use manual mode. |
| `Invalid OTP` | The previous attempt's OTP mail was picked up instead of the new one; run again. |
| Wrong-password error | Update `PASSWORD` in `erpcreds.py`. |

## Security notes

- `erpcreds.py`, `.session`, `token.json` and `credentials.json` are all in
  [.gitignore](.gitignore) — your credentials can't be committed by accident.
  Double-check before force-adding anything.
- Everything runs locally; nothing is sent anywhere except `erp.iitkgp.ac.in`
  and Gmail's IMAP server.
- The app password grants mailbox access only until you revoke it at
  <https://myaccount.google.com/apppasswords>. Revoke it if a machine is lost.
- On shared machines, delete `.session` after use.

## Credits

Request sequence based on the reverse-engineered ERP SSO flow popularised by
[proffapt/iitkgp-erp-login-pypi](https://github.com/proffapt/iitkgp-erp-login-pypi).
This repo is a self-contained rewrite: single small package, IMAP app-password
OTP instead of Google OAuth, redirect-safe token hand-off to the browser, and
a keep-alive extension.

## License

[MIT](LICENSE)
