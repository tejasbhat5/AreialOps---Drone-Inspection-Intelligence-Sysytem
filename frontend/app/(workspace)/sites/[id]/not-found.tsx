import Link from "next/link";
import { EmptyState } from "@/components/ui/states";

export default function NotFound() {
  return (
    <div className="page">
      <EmptyState
        title="Site not found"
        message="This site does not exist or its identifier is no longer valid."
      />
      <div className="center-action">
        <Link className="button" href="/sites">
          Return to site registry
        </Link>
      </div>
    </div>
  );
}
