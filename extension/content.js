/**
 * Applywise Agent — universal content script.
 *
 * Injected on demand into a job tab. Two jobs:
 *   1. scan  → extract the job posting (title/company/description) and every
 *              fillable form field on the page (works on ANY site, no per-ATS
 *              hardcoding), plus safety flags (captcha/login/file-upload).
 *   2. fill  → fill the form from the backend's answers using React-safe value
 *              setters, then either auto-submit (safe forms, auto mode) or show a
 *              floating Approve / Skip panel for the user to decide (like Claude
 *              asking before an action).
 *
 * It never bypasses CAPTCHAs and never auto-submits login/captcha pages.
 */
(function () {
  if (window.__applywiseAgentInjected) return;
  window.__applywiseAgentInjected = true;

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    try {
      if (msg.cmd === "ping") return sendResponse({ ok: true });
      if (msg.cmd === "scan") return sendResponse(scanPage());
      if (msg.cmd === "fill") {
        fillAndDecide(msg.data).then(sendResponse).catch((e) =>
          sendResponse({ status: "error", error: String(e), filledCount: 0, submitted: false })
        );
        return true; // async response
      }
    } catch (e) {
      sendResponse({ status: "error", error: String(e) });
    }
  });

  // ── Scan ────────────────────────────────────────────────────────────────────
  function scanPage() {
    const job = extractJob();
    const fields = extractFields();
    return { job, fields, flags: computeFlags(), url: location.href };
  }

  // Safety flags used to decide what we must never auto-submit.
  function computeFlags() {
    return {
      captcha: hasCaptcha(),
      login: hasLoginWall(),
      fileUpload: !!document.querySelector('input[type="file"]'),
    };
  }

  function extractJob() {
    // 1) JSON-LD JobPosting — most reliable across Greenhouse/Lever/LinkedIn/Indeed.
    for (const node of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const data = JSON.parse(node.textContent);
        const posting = findJobPosting(data);
        if (posting) {
          const org = posting.hiringOrganization;
          return {
            title: clean(posting.title) || fallbackTitle(),
            company: clean(typeof org === "string" ? org : org && org.name) || fallbackCompany(),
            description: clean(stripHtml(posting.description)).slice(0, 6000) || fallbackDescription(),
          };
        }
      } catch (_) {}
    }
    // 2) Heuristic fallback.
    return {
      title: fallbackTitle(),
      company: fallbackCompany(),
      description: fallbackDescription(),
    };
  }

  function findJobPosting(data) {
    if (!data) return null;
    if (Array.isArray(data)) {
      for (const d of data) {
        const p = findJobPosting(d);
        if (p) return p;
      }
      return null;
    }
    if (data["@graph"]) return findJobPosting(data["@graph"]);
    const t = data["@type"];
    if (t === "JobPosting" || (Array.isArray(t) && t.includes("JobPosting"))) return data;
    return null;
  }

  function fallbackTitle() {
    const meta = metaContent("og:title");
    const h1 = document.querySelector("h1");
    return clean((h1 && h1.textContent) || meta || document.title).slice(0, 200);
  }

  function fallbackCompany() {
    return clean(
      metaContent("og:site_name") ||
        (document.querySelector('[class*="company" i], [data-company]') || {}).textContent ||
        location.hostname.replace(/^www\./, "")
    ).slice(0, 120);
  }

  function fallbackDescription() {
    const main = document.querySelector("main, article, [role='main']");
    const text = (main && main.innerText) || document.body.innerText || "";
    return clean(text).slice(0, 6000);
  }

  // ── Field extraction ─────────────────────────────────────────────────────────
  const SKIP_TYPES = new Set(["hidden", "submit", "button", "image", "reset", "search", "password"]);

  function extractFields() {
    const els = Array.from(document.querySelectorAll("input, textarea, select"));
    const fields = [];
    let i = 0;
    for (const el of els) {
      const type = (el.type || el.tagName).toLowerCase();
      if (SKIP_TYPES.has(type)) continue;
      if (!isVisible(el) || el.disabled || el.readOnly) continue;
      if (isHoneypot(el)) continue;
      const key = "aw_" + i++;
      el.setAttribute("data-aw", key); // stable handle for the fill phase
      const field = {
        name: key,
        label: labelFor(el).slice(0, 160),
        type: el.tagName.toLowerCase() === "select" ? "select" : type,
        required: el.required || el.getAttribute("aria-required") === "true",
        options: [],
      };
      if (field.type === "select") {
        field.options = Array.from(el.options || []).map((o) => clean(o.textContent)).filter(Boolean).slice(0, 40);
      }
      fields.push(field);
    }
    return fields;
  }

  function labelFor(el) {
    if (el.labels && el.labels.length) return labelText(el.labels[0]);
    const aria = el.getAttribute("aria-label");
    if (aria) return clean(aria);
    const labelledby = el.getAttribute("aria-labelledby");
    if (labelledby) {
      const ref = document.getElementById(labelledby);
      if (ref) return clean(ref.textContent);
    }
    if (el.placeholder) return clean(el.placeholder);
    const wrapLabel = el.closest("label");
    if (wrapLabel) return labelText(wrapLabel);
    // Preceding label/legend/text within the same field group.
    const group = el.closest("div, li, fieldset, section, p");
    if (group) {
      const lbl = group.querySelector("label, legend");
      if (lbl && !lbl.contains(el)) return labelText(lbl);
    }
    return humanize(el.name || el.id || "");
  }

  // Text of a label element WITHOUT any nested form controls / option text,
  // so a wrapping <label>Country <select>…</select></label> yields "Country".
  function labelText(labelEl) {
    const clone = labelEl.cloneNode(true);
    clone.querySelectorAll("input, select, textarea, button, option").forEach((n) => n.remove());
    return clean(clone.textContent);
  }

  // ── Fill + decide ─────────────────────────────────────────────────────────────
  async function fillAndDecide(data) {
    const answers = data.answers || {};
    const autonomy = data.autonomy || "review";
    let filledCount = 0;

    for (const [key, value] of Object.entries(answers)) {
      if (value == null || value === "") continue;
      const el = document.querySelector(`[data-aw="${key}"]`);
      if (!el) continue;
      if (fillField(el, String(value))) {
        highlight(el);
        filledCount++;
      }
    }

    const flags = computeFlags();
    const unsafe = flags.captcha || flags.login; // never auto-submit these
    const canAutoSubmit = autonomy === "auto" && !unsafe;

    const decision = await showOverlay({
      job: data.job || {},
      filledCount,
      flags,
      autoSubmit: canAutoSubmit,
    });

    if (decision === "skip") return { status: "skipped", filledCount, submitted: false, flags };

    // decision === "approve" → try to submit
    const submitted = clickSubmit();
    return {
      status: submitted ? "applied" : "needs_review",
      filledCount,
      submitted,
      flags,
    };
  }

  function fillField(el, value) {
    const tag = el.tagName.toLowerCase();
    try {
      if (tag === "select") {
        const opt = Array.from(el.options).find(
          (o) => clean(o.textContent).toLowerCase() === value.toLowerCase() || o.value.toLowerCase() === value.toLowerCase()
        );
        if (!opt) return false;
        el.value = opt.value;
        dispatch(el);
        return true;
      }
      if (el.type === "checkbox") {
        const on = /^(yes|true|on|1)$/i.test(value);
        if (el.checked !== on) {
          el.checked = on;
          dispatch(el);
        }
        return true;
      }
      if (el.type === "radio") return false; // leave grouped choices to the user
      setNativeValue(el, value);
      return true;
    } catch (_) {
      return false;
    }
  }

  // React/Vue-safe: use the native setter then fire input+change so frameworks notice.
  function setNativeValue(el, value) {
    const proto =
      el.tagName === "TEXTAREA"
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype;
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    el.focus();
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    dispatch(el);
    el.blur();
  }

  function dispatch(el) {
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function clickSubmit() {
    const candidates = Array.from(
      document.querySelectorAll('button, input[type="submit"], a[role="button"], [role="button"]')
    );
    const rx = /(submit|apply|send application|send|finish|continue|next)/i;
    for (const el of candidates) {
      const text = clean(el.innerText || el.value || el.getAttribute("aria-label") || "");
      if (rx.test(text) && isVisible(el) && !el.disabled) {
        el.scrollIntoView({ block: "center" });
        el.click();
        return true;
      }
    }
    return false;
  }

  // ── Approval overlay ──────────────────────────────────────────────────────────
  function showOverlay({ job, filledCount, flags, autoSubmit }) {
    return new Promise((resolve) => {
      document.getElementById("applywise-overlay")?.remove();
      const box = document.createElement("div");
      box.id = "applywise-overlay";
      box.style.cssText =
        "position:fixed;bottom:20px;right:20px;z-index:2147483647;width:340px;background:#13131f;color:#e2e8f0;" +
        "font-family:-apple-system,Segoe UI,sans-serif;border:1px solid #2a2a3e;border-radius:14px;padding:16px 18px;" +
        "box-shadow:0 12px 40px rgba(0,0,0,.5);font-size:13px;line-height:1.45";

      const warn = [];
      if (flags.captcha) warn.push("CAPTCHA present — solve it, then Approve.");
      if (flags.login) warn.push("Login wall detected.");
      if (flags.fileUpload) warn.push("Resume file upload — attach it manually.");

      box.innerHTML =
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">' +
        '<span style="font-size:16px">🤖</span><strong style="font-size:14px">Applywise Agent</strong></div>' +
        `<div style="color:#a78bfa;font-weight:600">${escapeHtml(job.title || "This role")}</div>` +
        `<div style="color:#9ca3af;margin-bottom:8px">${escapeHtml(job.company || location.hostname)}</div>` +
        `<div style="margin:8px 0">✅ Filled <b>${filledCount}</b> field(s).</div>` +
        (warn.length
          ? `<div style="background:#3a2a12;border:1px solid #6b4e18;border-radius:8px;padding:8px;margin:8px 0;color:#fbbf24;font-size:12px">⚠️ ${warn
              .map(escapeHtml)
              .join("<br>")}</div>`
          : "") +
        '<div style="display:flex;gap:8px;margin-top:12px">' +
        '<button id="aw-approve" style="flex:1;background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff;border:0;border-radius:8px;padding:9px;font-weight:600;cursor:pointer">Approve & submit</button>' +
        '<button id="aw-skip" style="background:#26263a;color:#cbd5e1;border:0;border-radius:8px;padding:9px 12px;cursor:pointer">Skip</button>' +
        "</div>" +
        '<div id="aw-count" style="color:#6b7280;font-size:11px;margin-top:8px;height:14px"></div>';

      document.body.appendChild(box);
      const done = (d) => {
        box.remove();
        resolve(d);
      };
      box.querySelector("#aw-approve").onclick = () => done("approve");
      box.querySelector("#aw-skip").onclick = () => done("skip");

      if (autoSubmit) {
        let n = 4;
        const el = box.querySelector("#aw-count");
        const tick = () => {
          n -= 1;
          if (!document.body.contains(box)) return;
          if (n <= 0) return done("approve");
          el.textContent = `Auto-submitting in ${n}s… (Skip to cancel)`;
          setTimeout(tick, 1000);
        };
        el.textContent = "Auto-submitting in 4s… (Skip to cancel)";
        setTimeout(tick, 1000);
      }
    });
  }

  // ── Small utilities ────────────────────────────────────────────────────────────
  function hasCaptcha() {
    const html = document.documentElement.innerHTML.toLowerCase();
    return ["recaptcha", "hcaptcha", "cf-turnstile", "g-recaptcha", "captcha"].some((s) => html.includes(s));
  }
  function hasLoginWall() {
    if (document.querySelector('input[type="password"]')) return true;
    const t = (document.body.innerText || "").toLowerCase().slice(0, 4000);
    return (t.includes("sign in") || t.includes("log in")) && !document.querySelector("textarea");
  }
  function isVisible(el) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return false;
    const s = getComputedStyle(el);
    return s.display !== "none" && s.visibility !== "hidden" && s.opacity !== "0";
  }
  function isHoneypot(el) {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return true;
    const name = (el.name || el.id || "").toLowerCase();
    return name.includes("honeypot") || name === "url" || name.includes("bot-field");
  }
  function metaContent(prop) {
    const m = document.querySelector(`meta[property="${prop}"], meta[name="${prop}"]`);
    return m ? m.getAttribute("content") : "";
  }
  function stripHtml(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.innerHTML = s;
    return d.textContent || "";
  }
  function clean(s) {
    return (s || "").replace(/\s+/g, " ").trim();
  }
  function humanize(s) {
    return clean(String(s).replace(/[_\-]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2"));
  }
  function highlight(el) {
    el.style.outline = "2px solid #7c3aed";
    el.style.outlineOffset = "1px";
    setTimeout(() => (el.style.outline = ""), 2500);
  }
  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
})();
