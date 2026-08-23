"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  {
    href: "/dashboard",
    label: "Command center",
    description: "Overview and priorities",
    short: "01",
  },
  {
    href: "/sites",
    label: "Sites",
    description: "Assets and map",
    short: "02",
  },
  {
    href: "/inspections",
    label: "Inspections",
    description: "Field records and uploads",
    short: "03",
  },
  {
    href: "/assistant",
    label: "AI assistant",
    description: "Investigate operational data",
    short: "04",
  },
  {
    href: "/reports",
    label: "Reports",
    description: "Evidence and retrieval",
    short: "05",
  },
  {
    href: "/settings",
    label: "Settings",
    description: "Providers and safeguards",
    short: "06",
  },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sidebar">
      <Link
        className="brand"
        href="/dashboard"
        aria-label="AerialOps dashboard"
      >
        <span className="brand-mark" aria-hidden="true">
          A
        </span>
        <span>
          <strong>AerialOps</strong>
          <small>Inspection intelligence</small>
        </span>
      </Link>
      <span className="nav-section-label">Workspace</span>
      <nav aria-label="Primary navigation">
        {navigation.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              className={`nav-link${active ? " active" : ""}`}
              href={item.href}
              key={item.href}
              aria-current={active ? "page" : undefined}
            >
              <span className="nav-index">{item.short}</span>
              <span className="nav-copy">
                <strong>{item.label}</strong>
                <small>{item.description}</small>
              </span>
            </Link>
          );
        })}
      </nav>
      <div className="sidebar-status">
        <span className="status-pulse" aria-hidden="true" />
        <div>
          <strong>Operations online</strong>
          <small>API telemetry enabled</small>
        </div>
      </div>
    </aside>
  );
}
