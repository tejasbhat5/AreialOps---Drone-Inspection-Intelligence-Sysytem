"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const sections = {
  dashboard: ["Command center", "Operational overview and priorities"],
  sites: ["Site registry", "Assets, locations, and risk"],
  inspections: ["Inspections", "Field activity and evidence"],
  assistant: ["AI assistant", "Grounded operational investigation"],
} as const;

export function Header() {
  const pathname = usePathname();
  const root = pathname.split("/")[1] as keyof typeof sections;
  const [title, description] = sections[root] ?? sections.dashboard;

  return (
    <header className="topbar">
      <div className="topbar-context">
        <span className="topbar-product">AerialOps</span>
        <span className="topbar-divider" aria-hidden="true" />
        <div>
          <strong>{title}</strong>
          <p>{description}</p>
        </div>
      </div>
      <Link className="button" href="/inspections#new-inspection">
        <span aria-hidden="true">+</span> New inspection
      </Link>
    </header>
  );
}
