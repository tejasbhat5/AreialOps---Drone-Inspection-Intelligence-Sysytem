import type { Metadata } from "next";
import { getAssistantCapabilities, getBackendHealth } from "@/lib/api";

export const metadata: Metadata = { title: "Settings | AerialOps" };

export default async function SettingsPage() {
  const [capabilities, health] = await Promise.all([
    getAssistantCapabilities(),
    getBackendHealth(),
  ]);
  return (
    <div className="page">
      <section className="hero-row">
        <div className="page-heading">
          <span className="eyebrow">Runtime controls</span>
          <h1>Providers, limits, and safeguards.</h1>
          <p>Read-only operational configuration. Secrets are never returned to this page.</p>
        </div>
      </section>
      <div className="settings-grid">
        <section className="section-block settings-card">
          <span className="eyebrow">Backend</span>
          <h2>{health.connected ? "Connected" : "Unavailable"}</h2>
          <p>{health.connected ? `${health.data.service} · v${health.data.version}` : health.message}</p>
        </section>
        <section className="section-block settings-card">
          <span className="eyebrow">Agent provider</span>
          <h2>{capabilities.active_provider}</h2>
          <p>{capabilities.model ?? "Deterministic local planner"}</p>
        </section>
        <section className="section-block settings-card">
          <span className="eyebrow">Execution limits</span>
          <h2>{capabilities.max_tool_calls} tools</h2>
          <p>{capabilities.max_model_rounds} model rounds with deterministic fallback.</p>
        </section>
      </div>
      <section className="section-block guardrail-list">
        <div className="section-heading">
          <div><span className="eyebrow">Safety model</span><h2>Non-negotiable boundaries</h2></div>
        </div>
        <ul>
          <li>The LLM can call only allowlisted, typed application tools.</li>
          <li>Risk scores come from the deterministic risk service—not from model text.</li>
          <li>Report answers retain inspection and passage citations.</li>
          <li>Image analysis is explicitly assistive and requires human review.</li>
          <li>API keys remain server-side and are excluded from Git.</li>
        </ul>
      </section>
    </div>
  );
}
