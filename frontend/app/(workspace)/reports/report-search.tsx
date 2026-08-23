"use client";

import Link from "next/link";
import { FormEvent, useState, useTransition } from "react";
import type { ReportCitation } from "@/types/domain";
import { searchReportsAction } from "./actions";

export function ReportSearch() {
  const [query, setQuery] = useState("");
  const [citations, setCitations] = useState<ReportCitation[]>([]);
  const [message, setMessage] = useState("");
  const [pending, startTransition] = useTransition();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    startTransition(async () => {
      const result = await searchReportsAction(query);
      if (!result.ok) {
        setMessage(result.message);
        setCitations([]);
        return;
      }
      setCitations(result.response.citations);
      setMessage(
        result.response.total
          ? `${result.response.total} source passage${result.response.total === 1 ? "" : "s"} found.`
          : "No indexed report matched that question.",
      );
    });
  }

  return (
    <section className="section-block report-search-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Grounded retrieval</span>
          <h2>Search inspection evidence</h2>
        </div>
      </div>
      <form className="report-search-form" onSubmit={submit}>
        <label htmlFor="report-query">Question or operational term</label>
        <div>
          <input
            id="report-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What was reported during the previous Solar Farm Alpha inspection?"
            minLength={2}
            maxLength={500}
            required
          />
          <button className="button button-primary" disabled={pending} type="submit">
            {pending ? "Searching…" : "Search reports"}
          </button>
        </div>
      </form>
      {message ? <p className="report-search-message">{message}</p> : null}
      {citations.length ? (
        <div className="citation-list">
          {citations.map((citation) => (
            <article key={`${citation.report_id}-${citation.chunk_index}`}>
              <div>
                <span>{citation.report_filename} · passage {citation.chunk_index + 1}</span>
                <strong>{citation.site_name}</strong>
              </div>
              <p>{citation.excerpt}</p>
              <footer>
                <span>Relevance {Math.round(citation.score * 100)}%</span>
                <Link href={`/inspections/${citation.inspection_id}`}>Open source inspection →</Link>
              </footer>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
