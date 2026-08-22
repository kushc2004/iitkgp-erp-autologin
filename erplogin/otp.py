"""Fetches the ERP OTP: automatically over Gmail IMAP, or typed by hand.

The automatic path uses a Google *app* password (not the account password),
so no Google Cloud project, OAuth client or API library is needed - just
Python's built-in :mod:`imaplib`.
"""

import email
import imaplib
import re
import time

from .core import ErpLoginError, log, request_otp

OTP_SUBJECT = 'OTP for Sign In in ERP Portal of IIT Kharagpur'
IMAP_HOST = 'imap.gmail.com'


def get_otp(creds, session, login_details, interval=2.0, timeout=180):
    """Return the OTP, reading it from Gmail when app-password creds exist."""
    address = (getattr(creds, 'EMAIL_ADDRESS', '') or '').strip()
    app_password = (getattr(creds, 'EMAIL_APP_PASSWORD', '') or '').strip().replace(' ', '')

    if address and app_password:
        return _otp_over_imap(address, app_password, session,
                              login_details, interval, timeout)
    if address or app_password:
        log.info(" EMAIL_ADDRESS / EMAIL_APP_PASSWORD incomplete - asking for the OTP manually")
    return _otp_manual(session, login_details)


def _otp_manual(session, login_details):
    request_otp(session, login_details)
    return input('Enter the OTP sent to your registered email address: ').strip()


def _latest_match(conn):
    """Message id of the newest OTP mail, or None."""
    status, data = conn.search(None, f'(SUBJECT "{OTP_SUBJECT}")')
    if status != 'OK':
        return None
    ids = data[0].split()
    return ids[-1].decode('ascii') if ids else None


def _message_text(message):
    text = ''
    for part in message.walk():
        if part.get_content_type() not in ('text/plain', 'text/html'):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or 'utf-8'
        try:
            text += payload.decode(charset, errors='replace') + '\n'
        except LookupError:
            text += payload.decode('utf-8', errors='replace') + '\n'
    return re.sub(r'<[^>]+>', ' ', text)


def _otp_over_imap(address, app_password, session, login_details, interval, timeout):
    log.info(" Connecting to %s as %s ...", IMAP_HOST, address)
    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST)
        conn.login(address, app_password)
    except imaplib.IMAP4.error as error:
        raise ErpLoginError(
            f"Gmail login over IMAP failed ({error}). Check EMAIL_ADDRESS and "
            "EMAIL_APP_PASSWORD (a 16-character app password from "
            "myaccount.google.com/apppasswords), and that IMAP is enabled for "
            "the account.")

    try:
        conn.select('INBOX')
        baseline = _latest_match(conn)

        request_otp(session, login_details)
        log.info(" Waiting for OTP mail ...")

        deadline = time.time() + timeout
        while True:
            message_id = _latest_match(conn)
            if message_id and message_id != baseline:
                break
            if time.time() > deadline:
                raise ErpLoginError("Timed out waiting for the OTP mail")
            time.sleep(interval)

        status, data = conn.fetch(message_id, '(RFC822)')
        if status != 'OK' or data[0] is None:
            raise ErpLoginError("Could not read the OTP mail")
        message = email.message_from_bytes(data[0][1])

        candidates = re.findall(r'(?<!\d)\d{6}(?!\d)', _message_text(message))
        if not candidates:
            raise ErpLoginError("The OTP mail did not contain a six-digit code")

        # Mark as read instead of deleting anything.
        conn.store(message_id, '+FLAGS', '\\Seen')
        return candidates[-1]
    finally:
        try:
            conn.logout()
        except Exception:
            pass
