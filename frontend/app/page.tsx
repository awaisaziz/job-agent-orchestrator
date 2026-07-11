"use client";

import { useRouter } from "next/navigation";
import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useState, useTransition } from "react";

import { fetchFrontendConfig, intakeProfile, matchJobs, searchJobs } from "../lib/api";
import type { FrontendConfigResponse } from "../lib/api";

const LOCATION_GROUPS: { region: string; options: string[] }[] = [
  { region: "Anywhere", options: ["All locations", "Remote"] },
  {
    region: "United States",
    options: ["United States", "New York, NY", "San Francisco, CA", "Seattle, WA", "Austin, TX", "Boston, MA"],
  },
  {
    region: "Canada",
    options: ["Canada", "Toronto, ON", "Vancouver, BC", "Montreal, QC", "Ottawa, ON"],
  },
  {
    region: "Europe",
    options: ["Europe", "London, UK", "Berlin, DE", "Amsterdam, NL", "Dublin, IE", "Paris, FR"],
  },
  {
    region: "Middle East",
    options: ["Middle East", "Dubai, UAE", "Abu Dhabi, UAE", "Riyadh, SA", "Doha, QA"],
  },
];

export default function HomePage() {
  const router = useRouter();
  const [position, setPosition] = useState("");
  const [location, setLocation] = useState("All locations");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [resumeFileName, setResumeFileName] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [config, setConfig] = useState<FrontendConfigResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const defaultModel = config?.default_model ?? "Loading...";

  useEffect(() => {
    void (async () => {
      try {
        setConfig(await fetchFrontendConfig());
      } catch {
        setConfig(null);
      }
    })();
  }, []);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      setResumeFileName("");
      setResumeText("");
      return;
    }
    setResumeFileName(file.name);
    setResumeText(await file.text());
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    startTransition(() => {
      void (async () => {
        try {
          setError(null);
          if (!resumeText.trim()) {
            throw new Error("Upload a base resume file before searching.");
          }

          const intake = await intakeProfile({
            email,
            full_name: fullName || undefined,
            phone: phone || undefined,
            location: location === "All locations" ? undefined : location,
            resume_filename: resumeFileName || "resume.txt",
            resume_text: resumeText,
          });
          const search = await searchJobs({
            user_id: intake.profile.user_id,
            position,
            location: location === "All locations" ? undefined : location,
            email,
          });
          await matchJobs(search.search_id);
          router.push(`/search?searchId=${search.search_id}`);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Unable to start the job search workflow.");
        }
      })();
    });
  }

  return (
    <main className="page-shell">
      <section className="hero landing-hero">
        <div className="hero-grid">
          <div>
            <div className="eyebrow">Job agent orchestrator</div>
            <h1>Search the role, rank the jobs, tailor the resume, track every application.</h1>
            <p className="hero-copy">
              Start with a position, location, email, and a truthful base resume. The app pulls normalized jobs from a
              multi-source search layer, scores fit, queues the jobs you pick, generates tailored resume PDFs, and keeps
              a local audit trail for approval and apply.
            </p>
            <div className="hero-points">
              <span className="pill">LinkedIn + Indeed + company sites</span>
              <span className="pill">Truthful resume tailoring</span>
              <span className="pill">ATS scoring</span>
              <span className="pill">Approval-first application flow</span>
              <span className="pill">Default model: {defaultModel}</span>
            </div>
            {config ? (
              <div className={`mode-banner ${config.llm_live ? "mode-live" : "mode-demo"}`}>
                <strong>{config.llm_live ? "● Live mode" : "● Demo mode"}</strong>
                <span>
                  Jobs: {config.job_search_mode === "jsearch" ? "live (JSearch)" : "live web search"} · Tailoring:{" "}
                  {config.llm_live ? `live (${config.default_model})` : "deterministic"} · Apply: {config.auto_apply_mode} · Email:{" "}
                  {config.email_live ? "on" : "off"}
                </span>
                {!config.llm_live ? (
                  <span className="mode-hint">
                    Job search is live. Add an OpenAI, Grok, or Anthropic key to backend/.env and restart the backend for AI
                    resume tailoring.
                  </span>
                ) : null}
              </div>
            ) : null}
          </div>

          <aside className="control-card landing-card">
            <h2>Start a search</h2>
            <p className="control-copy">Upload the source resume, then move into the application workspace.</p>
            <form onSubmit={handleSubmit} className="landing-form">
              <div className="form-grid">
                <label className="field">
                  <span>Position name</span>
                  <input value={position} onChange={(event) => setPosition(event.target.value)} placeholder="Backend engineer" required />
                </label>
                <label className="field">
                  <span>Preferred location</span>
                  <select value={location} onChange={(event) => setLocation(event.target.value)}>
                    {LOCATION_GROUPS.map((group) => (
                      <optgroup key={group.region} label={group.region}>
                        {group.options.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Email</span>
                  <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required />
                </label>
                <label className="field">
                  <span>Full name</span>
                  <input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Optional" />
                </label>
                <label className="field">
                  <span>Phone</span>
                  <input type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+1 555 010 0100" />
                </label>
              </div>

              <label className="upload-card">
                <span className="upload-title">Base resume upload</span>
                <span className="upload-copy">Choose the truthful source resume. The current parser works best with text-based files.</span>
                <input type="file" accept=".txt,.md,.rtf,.doc,.docx,.pdf" onChange={handleFileChange} />
                <strong>{resumeFileName || "No file selected yet"}</strong>
              </label>

              <button className="button button-primary landing-submit" type="submit" disabled={pending}>
                {pending ? "Building workspace..." : "Search jobs and open workspace"}
              </button>

              {error ? <div className="notice notice-error">{error}</div> : null}
            </form>
          </aside>
        </div>
      </section>
    </main>
  );
}
