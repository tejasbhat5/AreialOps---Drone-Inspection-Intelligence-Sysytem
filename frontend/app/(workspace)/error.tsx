"use client";

import { ErrorState } from "@/components/ui/states";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="page">
      <ErrorState
        title="Operations data unavailable"
        message="We could not reach the AerialOps API. Confirm the backend is running, then retry."
        retry={reset}
      />
    </div>
  );
}
