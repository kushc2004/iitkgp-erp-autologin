// Pure helper functions shared by the service worker and the popup.
// Loaded as a plain script (importScripts in the worker, <script> in the
// popup), so everything here must be side-effect free declarations.

'use strict';

/** Undo repeated URL-encoding so stored keys can be plain readable text. */
function normalizeQuestion(text) {
  let out = String(text == null ? '' : text).trim();
  for (let i = 0; i < 3; i++) {
    let decoded;
    try {
      decoded = decodeURIComponent(out);
    } catch (e) {
      break;
    }
    if (decoded === out) break;
    out = decoded;
  }
  return out;
}

/** Look up an answer by question text, ignoring case and encoding. */
function lookupAnswer(answers, rawQuestion) {
  const target = normalizeQuestion(rawQuestion).toLowerCase();
  for (const [key, value] of Object.entries(answers || {})) {
    if (normalizeQuestion(key).toLowerCase() === target) return value;
  }
  return null;
}

/** Pull the hidden sessionToken out of the SSO login page HTML. */
function extractSessionToken(html) {
  const tags = String(html || '').match(/<input\b[^>]*>/gi) || [];
  for (const tag of tags) {
    if (!/id\s*=\s*["']?sessionToken["']?(?:\s|>|$)/i.test(tag)) continue;
    const m = tag.match(/value\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s">]+))/i);
    const value = m ? (m[1] !== undefined ? m[1] : (m[2] !== undefined ? m[2] : m[3])) : '';
    if (value) return value;
  }
  return null;
}

/** Extract an ssoToken from a URL (query string). */
function extractSsoFromUrl(url) {
  const m = String(url || '').match(/[?&]ssoToken=([^&\s"']+)/);
  return m ? m[1] : null;
}

function decodeEntities(text) {
  return String(text || '')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#0?39;/g, "'")
    .replace(/&apos;/g, "'").replace(/&amp;/g, '&');
}

function stripTags(text) {
  return String(text || '').replace(/<[^>]*>/g, ' ');
}

/**
 * Parse Gmail's Atom feed (https://mail.google.com/mail/feed/atom).
 * Returns [{id, title, summary}]; DOMParser is unavailable in service
 * workers, hence the regex-based extraction.
 */
function parseAtomEntries(xmlText) {
  const xml = String(xmlText || '');
  if (!/<feed[\s>]/i.test(xml)) return [];          // sign-in page etc.
  const entries = [];
  const blocks = xml.match(/<entry>[\s\S]*?<\/entry>/gi) || [];
  for (const block of blocks) {
    const pick = (name) => {
      const m = block.match(new RegExp('<' + name + '[^>]*>([\\s\\S]*?)</' + name + '>', 'i'));
      return m ? decodeEntities(stripTags(m[1])).trim() : '';
    };
    entries.push({
      id: pick('id'),
      title: pick('title'),
      summary: pick('summary'),
    });
  }
  return entries;
}

/** The standalone six-digit OTP inside a mail snippet (last one wins). */
function extractOtp(text) {
  const candidates = String(text || '').match(/(?<!\d)\d{6}(?!\d)/g);
  return candidates ? candidates[candidates.length - 1] : null;
}
