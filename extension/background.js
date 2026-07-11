/**
 * Applywise Agent — background service worker.
 *
 * Orchestrates: scan open tabs → filter by target title → for each match, ask the
 * local backend to prepare a tailored application → tell the content script to
 * fill + (auto or after approval) submit → record the result.
 *
 * The heavy lifting (LLM tailoring, profile, persistence) stays in the backend;
 * this worker only coordinates and talks to the page via the content script.
 */

const DEFAULT_BACKEND = "http://localhost:8000";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.cmd === "scan") {
    scanTabs(msg).then(sendResponse).catch((e) => sendResponse({ error: String(e), tabs: [] }));
    return true;
  }
  if (msg.cmd === "apply") {
    applyToTabs(msg).then(sendResponse).catch((e) => sendResponse({ error: String(e), results: [] }));
    return true;
  }
});

// ── Scan ────────────────────────────────────────────────────────────────────
async function scanTabs({ title }) {
  const targetTokens = tokenize(title);
  const tabs = await chrome.tabs.query({ currentWindow: true });
  const out = [];
  for (const tab of tabs) {
    if (!tab.id || !/^https?:/.test(tab.url || "")) continue;
    const scan = await injectAndSend(tab.id, { cmd: "scan" });
    if (!scan || scan.error) {
      out.push({ tabId: tab.id, title: tab.title || tab.url, company: "", url: tab.url, fieldCount: 0, matched: false, unreadable: true });
      continue;
    }
    const jobTitle = (scan.job && scan.job.title) || tab.title || "";
    out.push({
      tabId: tab.id,
      title: jobTitle,
      company: (scan.job && scan.job.company) || "",
      url: scan.url || tab.url,
      fieldCount: (scan.fields || []).length,
      matched: matchesTitle(targetTokens, jobTitle),
      flags: scan.flags || {},
    });
  }
  return { tabs: out };
}

// ── Apply ──────────────────────────────────────────────────────────────────
async function applyToTabs({ email, backendUrl, autonomy, tabIds }) {
  const base = (backendUrl || DEFAULT_BACKEND).replace(/\/$/, "");
  const results = [];

  for (const tabId of tabIds) {
    try {
      await chrome.tabs.update(tabId, { active: true }); // surface the tab so the user sees the overlay
      progress({ tabId, phase: "scanning" });
      const scan = await injectAndSend(tabId, { cmd: "scan" });
      if (!scan || scan.error) throw new Error(scan?.error || "Could not read page");

      const job = scan.job || {};
      progress({ tabId, phase: "preparing", job });
      const prep = await postJson(`${base}/api/v1/extension/prepare-application`, {
        email,
        job_title: job.title || "",
        company: job.company || "",
        job_description: job.description || "",
        apply_url: scan.url || "",
        fields: scan.fields || [],
      });

      progress({ tabId, phase: "filling", job });
      const filled = await injectAndSend(tabId, {
        cmd: "fill",
        data: { answers: prep.answers || {}, job, autonomy },
      });

      const status = filled?.status || "needs_review";
      await postJson(`${base}/api/v1/extension/record-application`, {
        email,
        job_title: job.title || "",
        company: job.company || "",
        apply_url: scan.url || "",
        status,
        notes: `Filled ${filled?.filledCount || 0} field(s) via extension${filled?.flags?.fileUpload ? "; resume upload needs manual attach" : ""}`,
        notify: false,
      }).catch(() => {});

      const result = { tabId, job, status, filledCount: filled?.filledCount || 0, flags: filled?.flags || {} };
      results.push(result);
      progress({ tabId, phase: "done", job, status, filledCount: result.filledCount });
    } catch (e) {
      results.push({ tabId, status: "failed", error: String(e) });
      progress({ tabId, phase: "error", error: String(e) });
    }
  }
  return { results };
}

// ── Helpers ──────────────────────────────────────────────────────────────────
async function injectAndSend(tabId, message) {
  try {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  } catch (e) {
    return { error: "inject failed: " + String(e) };
  }
  try {
    return await chrome.tabs.sendMessage(tabId, message);
  } catch (e) {
    return { error: "message failed: " + String(e) };
  }
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = res.status;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    throw new Error(`Backend ${res.status}: ${detail}`);
  }
  return res.json();
}

function progress(data) {
  chrome.runtime.sendMessage({ cmd: "progress", ...data }).catch(() => {});
}

function tokenize(s) {
  return (s || "")
    .toLowerCase()
    .split(/[^a-z0-9+#]+/)
    .filter((t) => t.length >= 3 && !["the", "and", "for", "job", "senior", "junior"].includes(t));
}

function matchesTitle(targetTokens, title) {
  if (!targetTokens.length) return true;
  const t = (title || "").toLowerCase();
  return targetTokens.every((tok) => t.includes(tok));
}
