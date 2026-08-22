"""Fetches the ERP OTP: automatically over Gmail IMAP, or typed by hand.

The automatic path uses a Google *app* password (not the account password),
so no Google Cloud project, OAuth client or API library is needed - just
Python's built-in :mod:`imaplib`.

Gmail quirk this module works around: a long-lived IMAP connection keeps
serving stale SEARCH results, so every poll issues a NOOP first to make the
server notice newly arrived mail.  INBOX is checked first and Gmail's
"All Mail" folder as a fallback, in case a filter filed the OTP away.
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
        try:
            return _otp_over_imap(address, app_password, session,
                                  login_details, interval, timeout)
        except ErpLoginError:
            raise
    if address or app_password:
        log.info(" EMAIL_ADDRESS / EMAIL_APP_PASSWORD incomplete - asking for the OTP manually")
    return _otp_manual(session, login_details)


def _otp_manual(session, login_details):
    request_otp(session, login_details)
    return input('Enter the OTP sent to your registered email address: ').strip()


def _connect(address, app_password):
    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST)
        conn.login(address, app_password)
    except imaplib.IMAP4.error as error:
        raise ErpLoginError(
            f"Gmail login over IMAP failed ({error}). Check EMAIL_ADDRESS and "
            "EMAIL_APP_PASSWORD (a 16-character app password from "
            "myaccount.google.com/apppasswords), and that IMAP is enabled for "
            "the account.")
    return conn


def _mailboxes(conn):
    """Mailboxes to poll: INBOX plus Gmail's All Mail folder when present."""
    boxes = ['INBOX']
    try:
        status, lines = conn.list()
    except imaplib.IMAP4.error:
        return boxes
    if status != 'OK':
        return boxes
    for raw in lines:
        match = re.search(r'"([^"]*[Aa]ll ?[Mm]ail[^"]*)"', raw.decode('ascii', 'replace'))
        if match and match.group(1) not in boxes:
            boxes.append(match.group(1))
    return boxes


def _select(conn, mailbox):
    status, _ = conn.select(mailbox)
    return status == 'OK'


def _latest_match(conn):
    """Message id of the newest OTP mail in the selected mailbox, or None."""
    # NOOP makes Gmail notice mail that arrived after this connection opened;
    # without it SEARCH can keep returning the same stale result forever.
    conn.noop()
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


def _extract_code(message):
    candidates = re.findall(r'(?<!\d)\d{6}(?!\d)', _message_text(message))
    return candidates[-1] if candidates else None


def _fetch_and_extract(conn, message_id):
    status, data = conn.fetch(message_id, '(RFC822)')
    if status != 'OK' or data[0] is None:
        return None
    message = email.message_from_bytes(data[0][1])
    code = _extract_code(message)
    if code is not None:
        # Mark as read instead of deleting anything.
        conn.store(message_id, '+FLAGS', '\\Seen')
    return code


def _otp_over_imap(address, app_password, session, login_details, interval, timeout):
    log.info(" Connecting to %s as %s ...", IMAP_HOST, address)
    conn = _connect(address, app_password)

    try:
        boxes = _mailboxes(conn)
        baselines = {}
        for box in boxes:
            if _select(conn, box):
                baselines[box] = _latest_match(conn)

        request_otp(session, login_details)
        log.info(" Waiting for OTP mail (checking %s) ...",
                 ', '.join(b.strip('"') for b in boxes))

        deadline = time.time() + timeout
        while True:
            for box in boxes:
                if not _select(conn, box):
                    continue
                message_id = _latest_match(conn)
                if message_id and message_id != baselines.get(box):
                    code = _fetch_and_extract(conn, message_id)
                    if code:
                        log.info(" Found the OTP mail in %s", box.strip('"'))
                        return code
            if time.time() > deadline:
                log.warning(
                    " No fresh OTP mail turned up in %s within %d seconds. "
                    "Check that %s really is the inbox ERP sends the OTP to.",
                    ', '.join(b.strip('"') for b in boxes), int(timeout), address)
                print('Falling back to manual entry.')
                return input('Enter the OTP you received: ').strip()
            time.sleep(interval)
    finally:
        try:
            conn.logout()
        except Exception:
            pass
