"use client";

import Link from "next/link";
import { FormEvent, useState, useTransition } from "react";
import { RiskBadge } from "@/components/ui/risk-badge";
import type {
  AssistantCapabilities,
  AssistantResponse,
  AssistantSite,
  ReportCitation,
  RiskFactors,
  RiskLevel,
} from "@/types/domain";
import { askAssistantAction } from "./actions";

type Exchange = { question: string; response: AssistantResponse };

const prompts = [
  "Show the highest-risk sites",
  "Compare the two highest-risk sites",
  "Why is Solar Farm Alpha high risk?",
  "Show unresolved findings for Solar Farm Alpha",
  "What was reported during the previous inspection at Solar Farm Alpha?",
];

export function AssistantWorkspace({
  capabilities,
}: {
  capabilities: AssistantCapabilities;
}) {
  const [message, setMessage] = useState("");
  const [conversationId, setConversationId] = useState<string>();
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [error, setError] = useState("");
  const [pending, startTransition] = useTransition();

  function runQuestion(value: string) {
    const question = value.trim();
    if (!question || pending) return;
    setError("");
    startTransition(async () => {
      const result = await askAssistantAction(question, conversationId);
      if (!result.ok) {
        setError(result.message);
        return;
      }
      setConversationId(result.response.conversation_id);
      setExchanges((current) => [...current, { question, response: result.response }]);
      setMessage("");
    });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    runQuestion(message);
  }

  return (
    <div className="assistant-shell">
      <section className="assistant-thread" aria-live="polite">
        {exchanges.length === 0 ? (
          <div className="assistant-empty">
            <span className="assistant-orbit" aria-hidden="true">AI</span>
            <h2>Ask about operational risk.</h2>
            <p>
              {capabilities.model_configured
                ? `The ${capabilities.model} model selects from validated AerialOps tools. `
                : "A deterministic local planner selects from validated AerialOps tools. "}
              Risk scores remain deterministic and tool activity stays visible.
            </p>
          </div>
        ) : (
          exchanges.map((exchange) => (
            <article className="assistant-exchange" key={exchange.response.request_id}>
              <div className="user-message">
                <span>You</span>
                <p>{exchange.question}</p>
              </div>
              <div className="assistant-message">
                <div className="assistant-answer-label">
                  <span>AerialOps agent</span>
                  <small>{exchange.response.provider}</small>
                </div>
                <p className="assistant-answer">{exchange.response.answer}</p>
                <StructuredResult response={exchange.response} />
                <div className="tool-audit">
                  {exchange.response.tool_activity.map((activity) => (
                    <span key={`${exchange.response.request_id}-${activity.tool_name}`}>
                      <i className={activity.status === "COMPLETED" ? "ok" : "failed"} />
                      {activity.label} · {activity.duration_ms.toFixed(1)} ms
                    </span>
                  ))}
                </div>
              </div>
            </article>
          ))
        )}
        {pending ? <div className="assistant-thinking">Running bounded operational tools…</div> : null}
      </section>

      <aside className="assistant-console">
        <div>
          <span className="eyebrow">Suggested operations</span>
          <div className="prompt-stack">
            {prompts.map((prompt) => (
              <button
                type="button"
                key={prompt}
                disabled={pending}
                onClick={() => {
                  setMessage(prompt);
                  runQuestion(prompt);
                }}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
        <form onSubmit={submit} className="assistant-form">
          <label htmlFor="assistant-message">Operational question</label>
          <textarea
            id="assistant-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask about a site, risk, inspection, or unresolved finding…"
            maxLength={2000}
            rows={5}
          />
          {error ? <p className="form-error">{error}</p> : null}
          <button className="button button-primary" type="submit" disabled={pending}>
            {pending ? "Working…" : "Run inquiry"}
          </button>
        </form>
        <p className="assistant-guardrail">
          Read-only · maximum {capabilities.max_tool_calls} tool calls · maximum{" "}
          {capabilities.max_model_rounds} model rounds · no autonomous mutations
        </p>
      </aside>
    </div>
  );
}

function StructuredResult({ response }: { response: AssistantResponse }) {
  const data = response.data ?? {};
  const citationsValue = data.citations ?? data.report_citations;
  const citations = Array.isArray(citationsValue)
    ? (citationsValue as ReportCitation[])
    : [];
  if (citations.length) {
    return (
      <div className="assistant-citations">
        {citations.map((citation) => (
          <Link
            href={`/inspections/${citation.inspection_id}`}
            key={`${citation.report_id}-${citation.chunk_index}`}
          >
            <div>
              <strong>{citation.site_name}</strong>
              <p>{citation.excerpt}</p>
            </div>
            <small>{Math.round(citation.score * 100)}% match</small>
          </Link>
        ))}
      </div>
    );
  }
  const sites = Array.isArray(data.sites) ? (data.sites as AssistantSite[]) : [];
  if (sites.length) {
    return (
      <div className="assistant-sites">
        {sites.map((site) => (
          <Link href={`/sites/${site.id}`} key={site.id}>
            <div>
              <strong>{site.name}</strong>
              <small>{site.location} · {site.unresolved_anomalies} unresolved</small>
            </div>
            <RiskBadge level={site.risk_level} score={site.risk_score} />
          </Link>
        ))}
      </div>
    );
  }
  if (response.response_type === "risk_explanation") {
    const factors = (data.factors ?? {}) as RiskFactors;
    return (
      <div className="assistant-risk-breakdown">
        <RiskBadge level={String(data.level) as RiskLevel} score={Number(data.score)} />
        <span>Severity {factors.severity_points ?? 0}</span>
        <span>Critical bonus {factors.critical_bonus ?? 0}</span>
        <span>Volume {factors.volume_points ?? 0}</span>
        <span>Recency {factors.recency_points ?? 0}</span>
      </div>
    );
  }
  return null;
}
