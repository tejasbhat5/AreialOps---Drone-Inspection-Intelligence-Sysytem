import type { BackendHealth } from "@/lib/api";

type BackendStatusProps = {
  health: BackendHealth;
};

export function BackendStatus({ health }: BackendStatusProps) {
  return (
    <section
      aria-live="polite"
      className="rounded-2xl border border-[var(--panel-border)] bg-[var(--panel)] p-5 shadow-2xl shadow-black/20 backdrop-blur"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold tracking-[0.18em] text-[var(--muted)] uppercase">
            API connection
          </p>
          <p className="mt-2 text-lg font-semibold">
            {health.connected ? "FastAPI is online" : "FastAPI is unavailable"}
          </p>
        </div>
        <span
          className={`h-3 w-3 rounded-full ${
            health.connected
              ? "bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.9)]"
              : "bg-amber-400 shadow-[0_0_18px_rgba(251,191,36,0.75)]"
          }`}
        />
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
        {health.connected
          ? `Connected to ${health.data.service} v${health.data.version} through GET /health.`
          : health.message}
      </p>
    </section>
  );
}
