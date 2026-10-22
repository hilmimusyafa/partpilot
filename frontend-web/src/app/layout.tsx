import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PartPilot - Procurement AI",
  description: "PartPilot AI Spare Part Procurement & Requisition System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className="antialiased">{children}</body>
    </html>
  );
}
