import type { Metadata } from "next";
import { getAssistantCapabilities } from "@/lib/api";
import { AssistantWorkspace } from "./assistant-workspace";

export const metadata: Metadata = { title: "AI Assistant | AerialOps" };

export default async function AssistantPage() {
  const capabilities = await getAssistantCapabilities();
  return (
    <div className="page assistant-page">
      <section className="hero-row assistant-hero">
        <div className="page-heading">
          <span className="eyebrow">Controlled intelligence</span>
          <h1>Operational answers, grounded in live data.</h1>
          <p>
            A bounded assistant for site risk, inspections, and anomaly triage—with every
            application tool call made visible.
          </p>
        </div>
        <div className="agent-status-card">
          <span className="status-pulse" aria-hidden="true" />
          <div>
            <strong>{capabilities.model_configured ? "Model agent ready" : "Local agent ready"}</strong>
            <small>
              {capabilities.model_configured
                ? `OpenAI · ${capabilities.model}`
                : "Deterministic planner · model fallback"}
            </small>
          </div>
        </div>
      </section>
      <AssistantWorkspace capabilities={capabilities} />
    </div>
  );
}
