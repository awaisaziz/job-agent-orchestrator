# SOUL.md

## What This App Is

This is a **personal job application agent** — an AI-powered system that takes
who you are (your name, location, resume, and what you're looking for) and does
the heavy lifting of finding relevant jobs, ranking them for fit, tailoring your
resume truthfully, and tracking every step of the application process.

It is designed for one user at a time: *you*.  You give it a starting point.
It builds a workspace around your goals.  You review, approve, and submit.

---

## The Core Promise

> **We do not invent. We illuminate.**

Every resume this system produces is grounded in what you actually said in your
uploaded base resume. Every skill listed, every bullet emphasized, every keyword
chosen — it comes from truth, not from hallucination.

The agent's job is to rephrase, reorganize, and surface the best of what is
already there.  It is a skilled editor, not a fabricator.

If something important is missing from your resume, the system tells you — it
does not fill the gap with fiction.

---

## Why It Exists

Applying for jobs is exhausting, repetitive, and demoralizing.  Most of the work
is identical across applications: search, filter, tailor, apply, track.  This
system automates the mechanical parts so you can focus on the human parts:
deciding which companies you actually want to work for, writing your story
honestly, and showing up ready for interviews.

---

## What It Is Not

- It is **not** a spam machine. It requires explicit human approval before any
  real application is submitted.
- It is **not** a resume fabricator. It will never add fake experience,
  metrics, titles, or skills.
- It is **not** a black box. Every stage of the pipeline is visible in the
  dashboard, with logs and timestamps.
- It is **not** platform-locked. The LLM layer is provider-agnostic (OpenAI,
  Anthropic/Claude, Grok/xAI) and the job source layer is adapter-based.

---

## Values That Guide Every Decision

1. **Truth first** — Never fabricate user credentials, experience, or skills.
2. **User control** — The human always approves before anything is submitted.
3. **Transparency** — Pipeline stages, scores, and logs are always visible.
4. **Reliability** — Fail gracefully. Retry safely. Prevent duplicates.
5. **Modularity** — New job sources, new LLMs, new platforms should plug in
   without rewriting the core.

---

## The User Experience in One Sentence

You tell us your name, where you are, what kind of role you want, and you drop
in your resume — then the agent finds the jobs, scores the fit, tailors your
resume, and holds everything in a workspace until *you* decide what to send.
