# Privacy Policy — IIT KGP ERP Auto-Login

Last updated: 2026-08-23

## What this software does

A browser extension and an optional command-line tool that sign the user in
to the IIT KGP ERP portal (https://erp.iitkgp.ac.in) automatically, including
reading the one-time password (OTP) email that the portal sends.

## What data is stored

**Browser extension** (stored in `chrome.storage.local`, never synced,
removed when the extension is uninstalled):

- ERP roll number
- ERP password
- Security-question answers learned during successful logins
- Preferred Gmail account index

**Command-line tool** (stored in a user-private file outside any repository):

- The same items above, in `credentials.py` under the OS config directory
- Cached ERP session tokens in a `.session` file

## What data leaves the device

- Credentials are sent only to `erp.iitkgp.ac.in` as part of its normal
  sign-in flow.
- The extension reads the **titles and snippets of unread mail** from
  `mail.google.com`'s feed for the sole purpose of finding the OTP, using
  the browser's existing Gmail session. No mail content is stored, logged,
  or sent anywhere else.
- Nothing else: no analytics, no telemetry, no advertising identifiers, no
  third-party requests, no remotely hosted code.

## Who has access

Only the user. The authors operate no servers and receive no data.

## Deleting your data

- Extension: remove it from the browser (or clear the extension's storage)
  and all stored values are destroyed.
- CLI: delete `credentials.py` and `.session` from the config directory.

## Contact

Open an issue at https://github.com/kushc2004/iitkgp-erp-autologin/issues
