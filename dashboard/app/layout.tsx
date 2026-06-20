import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Flight Price Monitor",
  description: "BKK→NRT · BKK→CNX · HKT→DPS — ติดตามราคาตั๋วเครื่องบินรายวัน",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th">
      <body className="min-h-screen antialiased"
            style={{ background: "var(--color-bg)", color: "var(--color-text)" }}>
        {children}
      </body>
    </html>
  );
}
