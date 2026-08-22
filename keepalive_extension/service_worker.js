const ERP_URL = "https://erp.iitkgp.ac.in/IIT_ERP3/";
const KEEP_ALIVE_URL = "https://erp.iitkgp.ac.in/IIT_ERP3/keepAlive.htm";
const ALARM_NAME = "erp-keep-alive";

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 20 });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 20 });
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== ALARM_NAME) return;
  const tabs = await chrome.tabs.query({ url: "https://erp.iitkgp.ac.in/*" });
  if (!tabs.length) return;

  try {
    const response = await fetch(KEEP_ALIVE_URL, {
      method: "GET",
      credentials: "include",
      cache: "no-store"
    });
    console.info("ERP keep-alive:", response.status, await response.text());
  } catch (error) {
    console.warn("ERP keep-alive failed:", error);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "open-erp") {
    chrome.tabs.create({ url: ERP_URL });
    sendResponse({ ok: true });
  }
  return true;
});
