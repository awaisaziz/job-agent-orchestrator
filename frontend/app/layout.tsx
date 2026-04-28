import "./globals.css";

export const metadata = {
  title: "Job Agent Orchestrator",
  description: "Interactive dashboard for ingestion, matching, resume tailoring, approval, and application tracking.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
