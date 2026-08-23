// IIT KGP ERP Auto-Login - service worker.
// Performs the whole SSO handshake in-browser, reads the OTP from Gmail's
// private unread-mail feed (with manual entry as fallback), opens ERP
// logged in, and keeps the session alive afterwards.

'use strict';

importScripts('lib.js');

const ERP_ORIGIN = 'https://erp.iitkgp.ac.in';
const ERP_URL = ERP_ORIGIN + '/IIT_ERP3/';
const HOMEPAGE_URL = ERP_URL;
const WELCOMEPAGE_URL = ERP_URL + 'welcome.jsp';
const LOGIN_PAGE_URL = ERP_ORIGIN + '/SSOAdministration/login.htm';
const LOGIN_URL = ERP_ORIGIN + '/SSOAdministration/auth.htm';
const SECRET_QUESTION_URL = ERP_ORIGIN + '/SSOAdministration/getSecurityQues.htm';
const OTP_URL = ERP_ORIGIN + '/SSOAdministration/getEmilOTP.htm';  // blame ERP for the typo

// Exact strings the SSO endpoints return.
const ANSWER_MISMATCH = "security question's answare mismatch";
const PASSWORD_MISMATCH = 'password mismatch';
const OTP_SENT = 'has been sent to your email id registered with ERP';
const OTP_MISMATCH = 'ERROR:Email OTP mismatch';

const OTP_SUBJECT = 'OTP for Sign In in ERP Portal of IIT Kharagpur';
const OTP_FEED_POLL_MS = 3000;
const OTP_FEED_TIMEOUT_MS = 60000;

const ALARM_NAME = 'erp-keep-alive';
const KEEP_ALIVE_URL = ERP_URL + 'keepAlive.htm';

// ---------------------------------------------------------------- state --

let STATE = freshState();

function freshState() {
  return {
    phase: 'idle',          // idle | running | done | error
    log: [],
    awaiting: null,         // null | 'answer' | 'otp'
    question: '',
    error: '',
    answeredCount: 0,
  };
}

function publicState() {
  return { ...STATE };
}

function setState(patch) {
  STATE = { ...STATE, ...patch };
  try {
    chrome.action.setBadgeText({ text: STATE.awaiting ? '!' : '' });
    chrome.action.setBadgeBackgroundColor({ color: '#c62828' });
  } catch (e) { /* action API unavailable in some contexts */ }
  broadcast();
}

function addLog(message) {
  STATE.log = [...STATE.log.slice(-7), message];
  broadcast();
}

function broadcast() {
  try {
    const p = chrome.runtime.sendMessage({ type: 'state-update', state: publicState() });
    if (p && p.catch) p.catch(() => {});   // no popup open - fine
  } catch (e) { /* context invalidated */ }
}

// ------------------------------------------------------------- settings --

async function getSettings() {
  const stored = await chrome.storage.local.get({
    rollNumber: '', password: '', answers: {}, gmailAccount: 0,
  });
  return stored;
}

async function saveSettings(patch) {
  await chrome.storage.local.set(patch);
}

// ------------------------------------------------------------- prompts --

let pendingPrompt = null;   // { resolve }

function askUser(kind, payload) {
  return new Promise((resolve) => {
    pendingPrompt = { resolve };
    setState({ awaiting: kind, ...payload });
  });
}

function submitPrompt(value) {
  const prompt = pendingPrompt;
  pendingPrompt = null;
  setState({ awaiting: null });
  if (prompt) prompt.resolve(String(value == null ? '' : value).trim());
}

// ------------------------------------------------------------ fetchers --

async function fetchText(url, options) {
  const response = await fetch(url, {
    credentials: 'include',
    headers: { 'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8' },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${url.split('/').pop()} responded ${response.status}`);
  }
  return response;
}

async function postForm(url, fields) {
  const response = await fetchText(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(fields).toString(),
  });
  return response;
}

// --------------------------------------------------------- sso handshake --

async function getSessionToken() {
  addLog('Fetching the SSO session token...');
  const response = await fetchText(HOMEPAGE_URL);
  const token = extractSessionToken(await response.text());
  if (!token) throw new Error('Could not find a sessionToken on the login page');
  return token;
}

async function prepareLoginPage(sessionToken) {
  const url = `${LOGIN_PAGE_URL}?sessionToken=${encodeURIComponent(sessionToken)}`
            + `&requestedUrl=${encodeURIComponent(HOMEPAGE_URL)}`;
  const response = await fetchText(url);
  const html = await response.text();

  // ERP may rotate the token during this visit; prefer the freshest value,
  // from the final URL's sessionToken= parameter or the hidden form field.
  const fromUrl = (response.url.match(/[?&]sessionToken=([^&\s"']+)/) || [])[1];
  const fromForm = extractSessionToken(html);
  return decodeURIComponent(fromUrl || fromForm || sessionToken);
}

async function getSecretQuestion(rollNumber) {
  addLog('Fetching your security question...');
  const response = await postForm(SECRET_QUESTION_URL, { user_id: rollNumber });
  const question = (await response.text()).trim();
  if (!question || question.toUpperCase() === 'FALSE') {
    throw new Error('Invalid roll number');
  }
  return question;
}

async function requestOtp(details) {
  addLog('Asking ERP to send the OTP...');
  const response = await postForm(OTP_URL, details);
  let message = '';
  try {
    message = (await response.json()).msg || '';
  } catch (e) {
    throw new Error(`Unexpected reply while requesting the OTP: ${(await response.text()).slice(0, 120)}`);
  }
  if (message.includes(ANSWER_MISMATCH)) throw new Error('Wrong security answer');
  if (message.includes(PASSWORD_MISMATCH)) throw new Error('Wrong password');
  if (!message.includes(OTP_SENT)) throw new Error(`Could not request the OTP: ${message}`);
}

// ----------------------------------------------------------- otp reading --

function feedUrls(gmailAccount) {
  // Poll the configured account first, then a few neighbours, because the
  // Gmail account index depends on how many accounts the browser holds.
  const primary = Number(gmailAccount) || 0;
  return [primary, ...[0, 1, 2, 3].filter((n) => n !== primary)]
    .map((n) => `https://mail.google.com/mail/u/${n}/feed/atom`);
}

async function readFeedAccount(url) {
  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) return [];
  const entries = parseAtomEntries(await response.text());
  return entries.filter((e) => e.title.includes(OTP_SUBJECT));
}

async function snapshotFeedBaselines(urls) {
  const baselines = {};
  for (const url of urls) {
    try {
      const matches = await readFeedAccount(url);
      baselines[url] = matches.length ? matches[matches.length - 1].id : '';
    } catch (e) {
      baselines[url] = null;   // unreachable account
    }
  }
  return baselines;
}

async function obtainOtp(baselines, urls) {
  addLog('Waiting for the OTP mail...');
  const deadline = Date.now() + OTP_FEED_TIMEOUT_MS;
  while (Date.now() < deadline) {
    for (const url of urls) {
      if (baselines[url] === null) continue;   // account not reachable
      let matches;
      try {
        matches = await readFeedAccount(url);
      } catch (e) {
        continue;
      }
      const newest = matches[matches.length - 1];
      if (newest && newest.id !== baselines[url]) {
        const code = extractOtp(`${newest.title}\n${newest.summary}`);
        if (code) return code;
      }
    }
    await new Promise((r) => setTimeout(r, OTP_FEED_POLL_MS));
  }

  addLog('Could not read the OTP automatically - enter it manually.');
  setState({ awaiting: 'otp' });
  return askUser('otp', {});
}

// -------------------------------------------------------------- sign in --

let lastSsoToken = null;

async function authenticate(details) {
  addLog('Signing in...');
  const response = await fetch(LOGIN_URL, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(details).toString(),
    redirect: 'follow',
  });
  const finalText = await response.text();
  if (finalText.includes(OTP_MISMATCH) || /invalid\s+otp/i.test(finalText)) {
    throw new Error('Invalid OTP');
  }
  lastSsoToken = extractSsoFromUrl(response.url);

  // welcome.jsp is reachable with a tiny fixed-size page only when logged in.
  const check = await fetch(WELCOMEPAGE_URL, { credentials: 'include' });
  const loggedIn = check.headers.get('content-length') === '741' || lastSsoToken;
  if (!loggedIn) throw new Error('Sign-in did not stick - wrong credentials or expired OTP');
}

async function setSsoCookie(token) {
  await chrome.cookies.set({
    url: ERP_ORIGIN + '/',
    name: 'ssoToken',
    value: token,
    path: '/',
    secure: true,
  });
}

async function resetErpCookies() {
  const cookies = await chrome.cookies.getAll({ domain: 'erp.iitkgp.ac.in' });
  for (const cookie of cookies) {
    if (cookie.name === 'ssoToken' || cookie.name.includes('JSID')) {
      const host = cookie.domain.replace(/^\./, '');
      await chrome.cookies.remove({ url: `https://${host}${cookie.path}`, name: cookie.name });
    }
  }
}

async function openErpTab() {
  await chrome.tabs.create({ url: ERP_URL });
}

// ----------------------------------------------------------------- flow --

async function login() {
  if (STATE.phase === 'running') return;
  setState({ ...freshState(), phase: 'running' });

  try {
    const settings = await getSettings();
    if (!settings.rollNumber || !settings.password) {
      throw new Error('Fill in your roll number and password in Settings first.');
    }

    addLog('Clearing stale ERP cookies...');
    await resetErpCookies();

    let sessionToken = await getSessionToken();
    sessionToken = await prepareLoginPage(sessionToken);
    const rawQuestion = await getSecretQuestion(settings.rollNumber);
    const question = normalizeQuestion(rawQuestion);

    let answer = lookupAnswer(settings.answers, question);
    let asked = false;
    if (answer == null) {
      addLog(`New security question - answer it once and it gets remembered.`);
      answer = await askUser('answer', { question });
      asked = true;
    } else {
      addLog('Security question recognised.');
    }

    const details = {
      user_id: settings.rollNumber,
      password: settings.password,
      answer,
      typeee: 'SI',
      sessionToken,
      requestedUrl: HOMEPAGE_URL,
    };

    const urls = feedUrls(settings.gmailAccount);
    const baselines = await snapshotFeedBaselines(urls);
    await requestOtp(details);

    // The typed answer is only trustworthy once the login succeeds, so it is
    // saved below rather than here.
    const otp = await obtainOtp(baselines, urls);
    addLog('Got the OTP.');
    details.email_otp = otp;

    await authenticate(details);

    if (asked) {
      settings.answers = { ...(settings.answers || {}), [question]: answer };
      await saveSettings({ answers: settings.answers });
      const count = Object.keys(settings.answers).length;
      setState({ answeredCount: count });
      addLog(`Answer saved (${count} remembered so far).`);
    }

    setState({ phase: 'done' });
    addLog('Signed in! Opening ERP...');
    await openErpTab();
  } catch (error) {
    setState({ phase: 'error', error: String(error.message || error) });
    addLog(`Failed: ${String(error.message || error)}`);
  }
}

// ------------------------------------------------------- keepalive alarm --

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 20 });
});
chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 20 });
});
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== ALARM_NAME) return;
  const tabs = await chrome.tabs.query({ url: 'https://erp.iitkgp.ac.in/*' });
  if (!tabs.length) return;
  try {
    const response = await fetch(KEEP_ALIVE_URL, { credentials: 'include', cache: 'no-store' });
    console.info('ERP keep-alive:', response.status);
  } catch (error) {
    console.warn('ERP keep-alive failed:', error);
  }
});

// -------------------------------------------------------------- messages --

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    switch (message && message.type) {
      case 'snapshot':
        sendResponse({ state: publicState(), settings: await getSettings() });
        break;
      case 'start-login':
        login();
        sendResponse({ ok: true });
        break;
      case 'submit-answer':
      case 'submit-otp':
        submitPrompt(message.value);
        sendResponse({ ok: true });
        break;
      case 'save-settings':
        await saveSettings(message.settings || {});
        setState({ answeredCount: Object.keys((message.settings || {}).answers || {}).length });
        sendResponse({ ok: true });
        break;
      case 'open-erp':
        await openErpTab();
        sendResponse({ ok: true });
        break;
      default:
        sendResponse({ ok: false });
    }
  })();
  return true;   // async sendResponse
});
