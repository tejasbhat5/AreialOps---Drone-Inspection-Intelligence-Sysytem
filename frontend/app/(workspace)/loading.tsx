import { LoadingState } from "@/components/ui/states";

export default function Loading() {
  return (
    <div className="page">
      <div className="page-heading">
        <span className="eyebrow">Loading telemetry</span>
        <h1>Preparing operations view</h1>
      </div>
      <LoadingState />
    </div>
  );
}
