import type { FlightRecord } from "./api/flights/route";
import RouteView from "@/components/RouteView";

export const revalidate = 3600;

async function fetchRoute(path: string): Promise<FlightRecord[]> {
  try {
    const base = process.env.NEXT_PUBLIC_BASE_URL ?? "http://localhost:3000";
    const res = await fetch(`${base}${path}`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const [nrtData, cnxData] = await Promise.all([
    fetchRoute("/api/flights"),
    fetchRoute("/api/cnx"),
  ]);

  return (
    <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <RouteView nrtData={nrtData} cnxData={cnxData} />
    </main>
  );
}
