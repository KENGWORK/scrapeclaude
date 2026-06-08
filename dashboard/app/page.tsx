import { Plane } from "lucide-react";
import type { FlightRecord } from "./api/flights/route";
import BestDealCards from "@/components/BestDealCard";
import PriceByDepartureChart from "@/components/PriceByDepartureChart";
import PriceHistoryChart from "@/components/PriceHistoryChart";

export const revalidate = 3600;

async function getFlights(): Promise<FlightRecord[]> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL ?? "http://localhost:3000";
    const res = await fetch(`${baseUrl}/api/flights`, { next: { revalidate: 3600 } });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const data = await getFlights();
  const lastUpdated = data.length
    ? data.reduce((a, b) => (a.scrape_date > b.scrape_date ? a : b)).scrape_date
    : null;

  return (
    <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">

      {/* Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-3">
          <Plane size={32} className="text-orange-400" />
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
            BKK <span className="text-orange-400">→</span> NRT
          </h1>
          <Plane size={32} className="text-orange-400 scale-x-[-1]" />
        </div>
        <p className="text-white/60 text-sm">
          ANA · JAL · Thai Airways &nbsp;|&nbsp; ม.ค.–ก.พ. 2026 &nbsp;|&nbsp; 8 วัน 7 คืน
        </p>
        {lastUpdated && (
          <p className="text-white/40 text-xs">อัปเดตล่าสุด: {lastUpdated}</p>
        )}
      </div>

      {/* No data */}
      {!data.length && (
        <div className="bg-white/10 rounded-2xl p-12 text-center text-white/40 border border-white/20">
          <Plane size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg">ยังไม่มีข้อมูล</p>
          <p className="text-sm mt-1">รอ GitHub Actions รันครั้งแรก 23:00 ICT</p>
        </div>
      )}

      {/* Best Deals */}
      {data.length > 0 && (
        <>
          <section>
            <h2 className="text-xl font-bold mb-4 text-orange-300">🏆 ราคาถูกที่สุด</h2>
            <BestDealCards data={data} />
          </section>

          {/* Charts */}
          <section className="space-y-6">
            <PriceByDepartureChart data={data} />
            <PriceHistoryChart data={data} />
          </section>

          {/* Full table */}
          <section>
            <h2 className="text-xl font-bold mb-4 text-orange-300">📋 ข้อมูลทั้งหมด</h2>
            <div className="overflow-x-auto rounded-2xl border border-white/20">
              <table className="w-full text-sm">
                <thead className="bg-white/10 text-white/70">
                  <tr>
                    {["วันออกเดินทาง","วันกลับ","สายการบิน","ราคา (THB)","เวลาออก","เวลาถึง","ใช้เวลา",""].map((h) => (
                      <th key={h} className="px-4 py-3 text-left whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...data]
                    .sort((a, b) => a.price_thb - b.price_thb)
                    .map((r, i) => (
                      <tr key={i}
                        className="border-t border-white/10 hover:bg-white/5 transition-colors">
                        <td className="px-4 py-3 whitespace-nowrap">{r.departure_date}</td>
                        <td className="px-4 py-3 whitespace-nowrap">{r.return_date}</td>
                        <td className="px-4 py-3 font-semibold">
                          <span className={
                            r.airline === "ANA"  ? "text-blue-300" :
                            r.airline === "JAL"  ? "text-red-300"  :
                            "text-amber-300"
                          }>{r.airline}</span>
                        </td>
                        <td className="px-4 py-3 font-bold text-white">
                          ฿{r.price_thb.toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-white/70">{r.dep_time || "–"}</td>
                        <td className="px-4 py-3 text-white/70">{r.arr_time || "–"}</td>
                        <td className="px-4 py-3 text-white/70">{r.duration || "–"}</td>
                        <td className="px-4 py-3">
                          {r.gf_link && (
                            <a href={r.gf_link} target="_blank" rel="noopener noreferrer"
                              className="text-orange-400 hover:text-orange-300 text-xs underline">
                              Google Flights
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <footer className="text-center text-white/20 text-xs pb-4">
        ข้อมูลจาก Google Flights · อัปเดตทุกวัน 23:00 ICT
      </footer>
    </main>
  );
}
