import type { Metadata } from "next";

import "leaflet/dist/leaflet.css";

import "./globals.css";

export const metadata: Metadata = {
  title: "AerialOps",
  description: "AI-powered drone inspection and geospatial intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
