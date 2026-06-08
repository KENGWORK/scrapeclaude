import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "✈️ BKK → NRT Flight Tracker",
  description: "ANA / JAL / Thai Airways price monitor Bangkok to Tokyo",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th">
      <body className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white">
        {children}
      </body>
    </html>
  );
}
