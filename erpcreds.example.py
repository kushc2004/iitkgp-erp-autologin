# Copy this file to erpcreds.py and fill in your own details:
#
#     cp erpcreds.example.py erpcreds.py
#
# erpcreds.py is listed in .gitignore, so your real credentials can never be
# committed to git by accident.

ROLL_NUMBER = "20XX XXXX XXX"
PASSWORD = "your-erp-password"

# ERP asks you one security question at sign-in. Write it here exactly as ERP
# displays it (capitalisation does not matter) with your answer as the value.
# If the dictionary is empty the first run will ask you interactively and
# print a ready-made line to paste here.
SECURITY_QUESTIONS_ANSWERS = {
    # "your security question appears like this": "your answer",
}

# --- Automatic OTP reading (optional but recommended) -----------------------
#
# Leave these blank to type the OTP manually each time. To have the script
# read the OTP mail for you:
#   1. Turn on 2-Step Verification: https://myaccount.google.com/security
#   2. Create an app password:      https://myaccount.google.com/apppasswords
#   3. Paste the 16-character password below (spaces are fine, they are
#      stripped automatically).
#
# This uses a Google *app* password, not your normal login password, and it
# stays on your machine only (see .gitignore).
EMAIL_ADDRESS = ""   # e.g. your.name@kgpian.iitkgp.ac.in
EMAIL_APP_PASSWORD = ""
