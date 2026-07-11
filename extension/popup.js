/** Applywise Agent — popup UI. */

const $ = (id) => document.getElementById(id);
const DEFAULT_BACKEND = "http://localhost:8000";
let scanned = []; // last scan results

document.addEventListener("DOMContentLoaded", init);

async function init() {
  const saved = await chrome.storage.local.get(["email", "title", "autonomy", "backend"]);
  $("email").value = saved.email || "";
  $("title").value = saved.title || "";
  $("autonomy").value = saved.autonomy || "review";
  $("backend").value = saved.backend || DEFAULT_BACKEND;

  for (const id of ["email", "title", "autonomy", "backend"]) {
    $(id).addEventListener("change", persist);
  }
  $("scan").addEventListener("click", onScan);
  $("apply").addEventListener("click", onApply);
  chrome.runtime.onMessage.addListener(onProgress);

  refreshWhoami();
}

function persist() {
  chrome.storage.local.set({
    email: $("email").value.trim(),
    title: $("title").value.trim(),
    autonomy: $("autonomy").value,
    backend: $("backend").value.trim() || DEFAULT_BACKEND,
  });
}

function backendUrl() {
  return ($("backend").value.trim() || DEFAULT_BACKEND).replace(/\/$/, "");
}

async function refreshWhoami() {
  const email = $("email").value.trim();
  if (!email) return setWhoami("Enter your email to load your profile.");
  try {
    const res = await fetch(`${backendUrl()}/api/v1/extension/profile?email=${encodeURIComponent(email)}`);
    if (!res.ok) return setWhoami("No profile found — complete intake in the web app.", true);
    const p = await res.json();
    setWhoami(`${p.full_name} · ${(p.skills || []).slice(0, 3).join(", ") || "resume loaded"}`);
  } catch (_) {
    setWhoami("Backend not reachable — is it running on " + backendUrl() + "?", true);
  }
}

function setWhoami(text, warn) {
  const el = $("whoami");
  el.textContent = text;
  el.style.color = warn ? "#fca5a5" : "#9ca3af";
}

async function onScan() {
  persist();
  const title = $("title").value.trim();
  if (!$("email").value.trim()) return notify("Enter your email first.");
  setNotice("Scanning open tabs…", "ok");
  $("scan").disabled = true;
  try {
    const res = await chrome.runtime.sendMessage({ cmd: "scan", title });
    scanned = (res && res.tabs) || [];
    renderTabs();
    const matches = scanned.filter((t) => t.matched).length;
    setNotice(`Found ${scanned.length} tab(s), ${matches} matching "${title || "any title"}".`, "ok");
  } catch (e) {
    setNotice("Scan failed: " + e, "err");
  } finally {
    $("scan").disabled = false;
  }
}

function renderTabs() {
  const ul = $("tabs");
  ul.innerHTML = "";
  for (const t of scanned) {
    const li = document.createElement("li");
    li.className = "tab" + (t.matched ? " matched" : "");
    li.dataset.tabId = t.tabId;
    const badge = t.unreadable ? " · unreadable" : t.fieldCount ? ` · ${t.fieldCount} fields` : " · no form";
    li.innerHTML =
      `<input type="checkbox" ${t.matched && !t.unreadable ? "checked" : ""} ${t.unreadable ? "disabled" : ""}/>` +
      `<div><div class="t-title">${esc(t.title || "(untitled)")}</div>` +
      `<div class="t-meta">${esc(t.company || hostOf(t.url))}${badge}</div>` +
      `<div class="t-status" id="st-${t.tabId}"></div></div>`;
    ul.appendChild(li);
  }
  $("apply").disabled = scanned.filter((t) => t.matched && !t.unreadable).length === 0;
}

function selectedTabIds() {
  return Array.from(document.querySelectorAll(".tab")).flatMap((li) => {
    const cb = li.querySelector('input[type="checkbox"]');
    return cb && cb.checked ? [Number(li.dataset.tabId)] : [];
  });
}

async function onApply() {
  persist();
  const tabIds = selectedTabIds();
  if (!tabIds.length) return notify("Select at least one tab.");
  $("apply").disabled = true;
  $("scan").disabled = true;
  setNotice(`Applying to ${tabIds.length} tab(s)…`, "ok");
  for (const id of tabIds) setStatus(id, "running", "Queued…");
  try {
    const res = await chrome.runtime.sendMessage({
      cmd: "apply",
      email: $("email").value.trim(),
      backendUrl: backendUrl(),
      autonomy: $("autonomy").value,
      tabIds,
    });
    const results = (res && res.results) || [];
    const applied = results.filter((r) => r.status === "applied").length;
    setNotice(`Done — ${applied}/${results.length} submitted. See the dashboard for the record.`, "ok");
    $("summary").textContent = `${applied} applied`;
  } catch (e) {
    setNotice("Apply failed: " + e, "err");
  } finally {
    $("apply").disabled = false;
    $("scan").disabled = false;
  }
}

function onProgress(msg) {
  if (!msg || msg.cmd !== "progress") return;
  const label = {
    scanning: "Reading page…",
    preparing: "Tailoring resume + answers…",
    filling: "Filling form…",
    done: statusText(msg.status, msg.filledCount),
    error: "Error: " + (msg.error || "unknown"),
  }[msg.phase];
  const kind = msg.phase === "done" ? msg.status : msg.phase === "error" ? "failed" : "running";
  setStatus(msg.tabId, kind, label);
}

function statusText(status, filled) {
  if (status === "applied") return `✅ Submitted (${filled || 0} fields)`;
  if (status === "skipped") return "⏭️ Skipped";
  if (status === "needs_review") return `📝 Filled ${filled || 0} — submit manually`;
  return status || "done";
}

function setStatus(tabId, kind, text) {
  const el = $(`st-${tabId}`);
  if (el) {
    el.textContent = text;
    el.className = "t-status s-" + kind;
  }
}

function setNotice(text, kind) {
  const el = $("notice");
  el.textContent = text;
  el.className = "notice" + (kind === "ok" ? " ok" : "");
  el.classList.remove("hidden");
}
function notify(text) {
  setNotice(text, "err");
}
function esc(s) {
  return String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch (_) {
    return "";
  }
}
