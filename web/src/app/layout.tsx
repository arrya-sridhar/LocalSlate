import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LocalSlate — Zero-Cloud Intelligence Dashboard",
  description:
    "Offline-first intelligence processing pipeline. Extract structured incident reports from raw field notes — text, files, and voice. All processing runs in your browser. Zero cloud calls.",
  keywords: ["intelligence", "offline-first", "incident-report", "field-notes", "zero-trust"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <meta name="theme-color" content="#0a0e17" />
        <meta name="color-scheme" content="dark" />
        <link rel="icon" href="/icon.svg" />
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body>{children}</body>
    </html>
  );
}
