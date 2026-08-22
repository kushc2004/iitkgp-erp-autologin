"""Core ERP sign-in flow.

The request sequence mirrors what a browser does on erp.iitkgp.ac.in:

1.  GET  /IIT_ERP3/                          login page hides a sessionToken
2.  GET  /SSOAdministration/login.htm        binds the SSO page session and
         ?sessionToken=...&requestedUrl=...  may rotate the token
3.  POST /SSOAdministration/getSecurityQues.htm
4.  POST /SSOAdministration/getEmilOTP.htm  the OTP mail is sent
5.  POST /SSOAdministration/auth.htm        302 -> success.htm?reqType=REMOTE
                                            302 -> /IIT_ERP3/?ssoToken=...

Step 5's redirect chain is walked one hop at a time and stops the moment a
redirect target carries the ssoToken.  The token URL itself is never opened
here: ERP validates (and spends) the token when a client first presents it,
and that client must be the real browser, not this script.
"""

import logging
import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

from .endpoints import (
    HOMEPAGE_URL,
    LOGIN_PAGE_URL,
    LOGIN_URL,
    OTP_URL,
    SECRET_QUESTION_URL,
    WELCOMEPAGE_URL,
)

log = logging.getLogger("erp-autologin")

# Exact strings the SSO endpoints return.
ANSWER_MISMATCH = "Unable to send OTP due to security question's answare mismatch ."
PASSWORD_MISMATCH = "Unable to send OTP due to password mismatch."
OTP_SENT = ("An OTP(valid for a short time) has been sent to your email id "
            "registered with ERP, IIT Kharagpur. Please use that OTP for further processing. ")
OTP_MISMATCH = "ERROR:Email OTP mismatch"

BASE_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Content-Type': 'application/x-www-form-urlencoded',
}


class ErpLoginError(Exception):
    """Raised when any step of the ERP sign-in fails."""


def _post_headers():
    headers = dict(BASE_HEADERS)
    headers.setdefault('Referer', HOMEPAGE_URL)
    headers.setdefault('Origin', 'https://erp.iitkgp.ac.in')
    return headers


def get_sessiontoken(session):
    """Fetch the hidden sessionToken from the logged-out ERP home page."""
    resp = session.get(HOMEPAGE_URL, headers=BASE_HEADERS)
    field = BeautifulSoup(resp.text, 'html.parser').find(id='sessionToken')
    if field is None:
        raise ErpLoginError("Could not find a sessionToken on the ERP home page")
    return field['value']


def _session_token_from(location):
    if not location:
        return None
    match = re.search(r'[?&]sessionToken=([^&\s>]+)', location)
    return match.group(1) if match else None


def prepare_login_page(session, session_token):
    """Visit the SSO login page once so later requests share its session.

    ERP may rotate the token during this visit; prefer whatever value the
    final URL or the hidden form field carries.
    """
    url = f"{LOGIN_PAGE_URL}?sessionToken={session_token}&requestedUrl={HOMEPAGE_URL}"
    resp = session.get(url, headers=BASE_HEADERS)
    resp.raise_for_status()

    rotated = _session_token_from(resp.url)
    if not rotated:
        soup = BeautifulSoup(resp.text, 'html.parser')
        field = soup.find(id='sessionToken') or soup.find('input', {'name': 'sessionToken'})
        if field is not None:
            rotated = field.get('value')

    return rotated or session_token


def get_secret_question(session, roll_number):
    """Fetch the security question shown for this roll number."""
    resp = session.post(SECRET_QUESTION_URL, data={'user_id': roll_number},
                        headers=BASE_HEADERS)
    question = resp.text.strip()
    if not question or question.upper() == 'FALSE':
        raise ErpLoginError(f"Invalid roll number: {roll_number!r}")
    return question


def normalize(text):
    """Undo repeated URL-encoding so dict keys can be plain readable text."""
    out = text.strip()
    for _ in range(3):
        decoded = urllib.parse.unquote(out)
        if decoded == out:
            break
        out = decoded
    return out


def resolve_answer(security_questions, question):
    """Look up the answer for question; fall back to asking interactively."""
    lookup = {normalize(key).casefold(): value
              for key, value in (security_questions or {}).items()}
    answer = lookup.get(normalize(question).casefold())
    if answer is None:
        readable = normalize(question)
        print(f"\nYour security question: {readable}")
        answer = input("Answer (one-time): ").strip()
        print('\nTo skip this prompt next time, add this to '
              'SECURITY_QUESTIONS_ANSWERS in erpcreds.py:\n')
        print(f'    "{readable}": "{answer}",\n')
    return answer


def request_otp(session, login_details):
    """Ask ERP to email an OTP for this login attempt."""
    resp = session.post(OTP_URL, data=login_details, headers=_post_headers())
    try:
        message = resp.json().get('msg', '')
    except ValueError:
        raise ErpLoginError(
            f"Unexpected response while requesting OTP: {resp.text[:200]!r}")

    if ANSWER_MISMATCH in message:
        raise ErpLoginError("Invalid security question answer")
    if PASSWORD_MISMATCH in message:
        raise ErpLoginError("Invalid password")
    if OTP_SENT in message:
        log.info(" Requested OTP")
        return
    raise ErpLoginError(f"Failed to request OTP: {message}")


def _sso_token_from(location):
    if not location:
        return None
    match = re.search(r'[?&]ssoToken=([^&\s>]+)', location)
    return match.group(1) if match else None


def signin(session, login_details):
    """Submit credentials + OTP and return the fresh ssoToken.

    The redirect chain is followed hop by hop with allow_redirects=False.
    Opening ``/IIT_ERP3/?ssoToken=...`` is what validates and spends the
    token, so the walk stops as soon as a redirect target carries it and
    leaves presenting that URL to the real browser.
    """
    headers = _post_headers()
    current_url = LOGIN_URL
    resp = session.post(current_url, data=login_details, headers=headers,
                        allow_redirects=False)

    trail = []
    sso_token = None
    for _ in range(8):
        location = resp.headers.get('Location')
        trail.append(f"{resp.status_code} -> {location}")

        sso_token = _sso_token_from(location)
        if sso_token is None and resp.text:
            body_match = re.search(r'[?&]ssoToken=([^&\s<>"\']+)', resp.text)
            sso_token = body_match.group(1) if body_match else None
        if sso_token is not None:
            break

        if resp.status_code not in (301, 302, 303, 307, 308) or not location:
            break
        current_url = urllib.parse.urljoin(current_url, location)
        resp = session.get(current_url, headers=headers, allow_redirects=False)

    if sso_token is None:
        if OTP_MISMATCH in resp.text:
            raise ErpLoginError("Invalid OTP")
        raise ErpLoginError(
            f"No ssoToken found in redirect chain ({'; '.join(trail)})")
    log.info(" Generated ssoToken")
    return sso_token


def session_alive(session):
    """True when the session's ssoToken cookie still unlocks the portal."""
    resp = session.get(WELCOMEPAGE_URL, headers=BASE_HEADERS)
    return resp.headers.get('Content-Length') == '741'


def _populate_session(session, sso_token):
    session.cookies.clear()
    session.cookies.set('ssoToken', sso_token, domain='erp.iitkgp.ac.in')


def load_cached_tokens(storage_file):
    if not storage_file or not os.path.exists(storage_file):
        return None
    try:
        with open(storage_file) as file:
            lines = [line.strip() for line in file.readlines()]
        if len(lines) >= 2 and lines[0] and lines[1]:
            return lines[0], lines[1]
    except OSError:
        pass
    return None


def save_tokens(storage_file, session_token, sso_token):
    try:
        with open(storage_file, "w") as file:
            file.write(f"{session_token}\n{sso_token}\n")
    except OSError as error:
        log.error(" Could not write %s: %s", storage_file, error)


def login(creds, otp_check_interval=2.0, storage_file=None):
    """Run the full sign-in flow and return ``(session_token, sso_token)``.

    ``creds`` can be any module or object exposing ROLL_NUMBER, PASSWORD and
    SECURITY_QUESTIONS_ANSWERS, plus optional EMAIL_ADDRESS and
    EMAIL_APP_PASSWORD for automatic OTP reading.
    """
    session = requests.Session()

    cached = load_cached_tokens(storage_file)
    if cached:
        session_token, sso_token = cached
        _populate_session(session, sso_token)
        if session_alive(session):
            log.info(" Reused cached ERP session from %s", storage_file)
            return session_token, sso_token
        log.info(" Cached tokens are no longer valid")

    roll_number = creds.ROLL_NUMBER.strip()
    password = creds.PASSWORD

    log.info(" Starting ERP sign-in for %s", roll_number)
    session_token = get_sessiontoken(session)
    session_token = prepare_login_page(session, session_token)
    question = get_secret_question(session, roll_number)
    answer = resolve_answer(getattr(creds, 'SECURITY_QUESTIONS_ANSWERS', {}),
                            question)

    login_details = {
        'user_id': roll_number,
        'password': password,
        'answer': answer,
        'typeee': 'SI',
        'sessionToken': session_token,
        'requestedUrl': HOMEPAGE_URL,
    }

    # Imported lazily: otp.py needs request_otp from this module.
    from .otp import get_otp
    login_details['email_otp'] = get_otp(creds, session, login_details,
                                         interval=otp_check_interval)
    log.info(" Received OTP")

    sso_token = signin(session, login_details)

    if storage_file:
        save_tokens(storage_file, session_token, sso_token)
        log.info(" Stored tokens in %s", storage_file)
    return session_token, sso_token
