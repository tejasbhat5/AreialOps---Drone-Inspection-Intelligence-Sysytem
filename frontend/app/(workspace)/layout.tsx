import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";

export const dynamic = "force-dynamic";

export default function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="workspace">
        <Header />
        <main>{children}</main>
      </div>
    </div>
  );
}
