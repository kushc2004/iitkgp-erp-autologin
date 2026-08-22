const ERP_ORIGIN = "https://erp.iitkgp.ac.in";
const ERP_URL = ERP_ORIGIN + "/IIT_ERP3/";
const KEEP_ALIVE_URL = ERP_ORIGIN + "/IIT_ERP3/keepAlive.htm";

function status(msg) {
  document.getElementById("popup-status").textContent = msg;
}

// Reads the ssoToken copied by open_erp.py from the clipboard and installs it
// as the browser's ERP session cookie.  This bypasses the ?ssoToken= URL
// parameter entirely, so it works even when ERP rejects a reused param token.
async function pasteTokenAndSignIn() {
  let text = "";
  try {
    text = await navigator.clipboard.readText();
  } catch (e) {
    status("Could not read clipboard: " + e.message);
    return;
  }
  if (!text) {
    status("Clipboard is empty - run open_erp.command again.");
    return;
  }

  // Accept either the bare token or a full login URL containing ssoToken=...
  const match = text.match(/[?&]ssoToken=([^&\s"']+)/);
  let token = match ? match[1] : text.trim();

  if (!/^[A-Za-z0-9._-]{10,}$/.test(token)) {
    status("No valid ssoToken found in clipboard.");
    return;
  }

  await resetErpCookies();

  try {
    await chrome.cookies.set({
      url: ERP_ORIGIN + "/",
      name: "ssoToken",
      value: token,
      path: "/",
      secure: true
    });
  } catch (e) {
    status("Failed to set cookie: " + e.message);
    return;
  }

  status("Signed in - opening ERP...");
  chrome.tabs.create({ url: ERP_URL });
  window.close();
}

// Removes stale session cookies (dead ssoToken / JSP session ids) that can
// otherwise shadow the freshly issued token.
async function resetErpCookies() {
  const cookies = await chrome.cookies.getAll({ domain: "erp.iitkgp.ac.in" });
  await Promise.all(cookies
    .filter(c => c.name === "ssoToken" || c.name.indexOf("JSID") !== -1)
    .map(c => chrome.cookies.remove({ url: cookieUrl(c), name: c.name })));
}

function cookieUrl(cookie) {
  const host = (cookie.domain || "").replace(/^\./, "");
  return "https://" + host + (cookie.path || "/");
}

document.getElementById("paste").addEventListener("click", pasteTokenAndSignIn);
document.getElementById("open").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "open-erp" }, () => window.close());
});
