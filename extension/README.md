# Applywise Agent — Chrome extension

An AI job-apply agent that lives in your browser. Open several job postings in
tabs, tell it a target job title, and it will — for each matching tab — pull your
stored resume + profile from your local Applywise backend, tailor a resume,
answer the actual form fields on the page, fill them in, and (with your approval)
submit.

It runs in **your real, logged-in browser session**, so it can act on pages the
backend's headless automation can't (sites where you're already signed in).

## Prerequisites

1. The Applywise **backend must be running** (`uvicorn app.main:app --port 8000`).
2. You must have **completed profile intake** in the web app (`http://localhost:3000`)
   at least once — that's where your resume, name, email, and phone are stored.
   The extension identifies you by that email.

## Install (load unpacked)

1. Open `chrome://extensions`.
2. Toggle **Developer mode** (top-right) on.
3. Click **Load unpacked** and select this `extension/` folder.
4. Pin the **Applywise Agent** icon to your toolbar.

## Use

1. Open the job postings you're interested in, each in its own tab.
2. Click the extension icon.
3. Enter the **email** you used in the web app, and a **target job title** (e.g.
   "Backend Engineer"). Choose the apply mode:
   - **Ask me before each submit** (default) — it fills every matching form and
     shows an Approve / Skip panel on each page so you review before it submits.
   - **Auto-submit safe forms** — it auto-submits simple forms after a short
     countdown, but still pauses for your approval on CAPTCHA / login pages.
4. Click **Scan open tabs** → matching tabs are highlighted and pre-selected.
5. Click **Apply to selected**. The extension walks each tab: reads the posting,
   asks the backend to tailor + answer the fields, fills them, highlights them,
   and applies per your chosen mode.
6. Everything it submits is recorded and shows up in your dashboard.

## What it does and does not do (honest limits)

**Works well on** standard application forms (Greenhouse, Lever, Ashby, and most
company career pages) — standard text/textarea/select fields fill reliably using
React-safe value setters.

**Assist-only** on multi-step wizards (Workday, LinkedIn Easy Apply, Indeed): it
fills the fields it can see on the current step; you advance through the steps.

**It will not:**
- **Bypass CAPTCHAs** — if a CAPTCHA is present it never auto-submits; you solve
  it, then click Approve.
- **Submit behind a login wall** — pages with a password field / sign-in are
  flagged and left for you.
- **Upload the resume file for you (yet)** — browsers block scripts from setting a
  file input's value, so if a form requires a resume file upload the panel tells
  you to attach it manually. (A `DataTransfer`-based upload of a generated resume
  file is a planned enhancement.)
- **Fill custom non-`<select>` dropdowns / radio groups** — those are left for you
  to confirm.

**Please also note:** some job sites' Terms of Service restrict automation, and
aggressive auto-submitting can risk your account. The default "Ask me before each
submit" mode keeps you in control. Use responsibly.

## Configuration

- **Backend URL** (Advanced) defaults to `http://localhost:8000`. Change it if you
  run the backend elsewhere.
- Your email, target title, and mode are remembered between sessions.

## How it fits together

```
Popup (you) ──▶ Background service worker ──▶ Backend  /extension/prepare-application
                      │  (tabs, orchestration)          (tailor resume + answer fields)
                      ▼
              Content script in each tab
              (extract posting, fill form, approval overlay, submit)
```

The backend does the thinking (your profile, resume tailoring, AI answers); the
extension is the hands inside your browser.
