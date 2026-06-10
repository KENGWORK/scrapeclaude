"use client";

import { useState } from "react";
import { Plane } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";
import BestDealCards from "./BestDealCard";
import PriceByDepartureChart from "./PriceByDepartureChart";
import PriceHistoryChart from "./PriceHistoryChart";

interface RouteConfig {
  key: string;
  label: string;
  origin: string;
  dest: string;
  desc: string;
  schedule: string;
  data: FlightRecord[];
}

export default function RouteView({ nrtData, cnxData }: {
  nrtData: FlightRecord[];
  cnxData: FlightRecord[];
}) {
  const routes: RouteConfig[] = [
    {
      key: "nrt",
      label: "BKK → NRT",
      origin: "BKK",
      dest: "NRT",
      desc: "ANA · JAL · Thai Airways | ม.ค.–ก.พ. 2027 | 8 วัน 7 คืน",
      schedule: "14:00 & 23:00 ICT",
      data: nrtData,
    },
    {
      key: "cnx",
      label: "BKK → CNX",
      origin: "BKK",
      dest: "CNX",
      desc: "3 สายการบินถูกสุด | พ.ย. 2026–ม.ค. 2027 | 5 วัน 4 คืน",
      schedule: "11:00 ICT",
      data: cnxData,
    },
  ];

  const [activeKey, setActiveKey] = useState("nrt");
  const route = routes.find((r) => r.key === activeKey)!;
  const data = route.data;

  const lastUpdated = data.length
    ? data.reduce((a, b) => (a.scrape_date > b.scrape_date ? a : b)).scrape_date
    : null;

  return (
    <>
      {/* Tab switcher */}
      <div className="flex justify-center gap-3 flex-wrap">
        {routes.map((r) => (
          <button
            key={r.key}
            onClick={() => setActiveKey(r.key)}
            className={`px-6 py-3 rounded-2xl font-bold text-sm transition-all border ${
              activeKey === r.key
                ? "bg-orange-400 text-black border-orange-400 shadow-lg shadow-orange-400/30"
                : "bg-white/10 text-white/70 border-white/20 hover:bg-white/20"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-3">
          <Plane size={32} className="text-orange-400" />
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
            {route.origin} <span className="text-orange-400">→</span> {route.dest}
          </h1>
          <Plane size={32} className="text-orange-400 scale-x-[-1]" />
        </div>
        <p className="text-white/60 text-sm">{route.desc}</p>
        {lastUpdated && (
          <p className="text-white/40 text-xs">อัปเดตล่าสุด: {lastUpdated}</p>
        )}
      </div>

      {/* No data */}
      {!data.length && (
        <div className="bg-white/10 rounded-2xl p-12 text-center text-white/40 border border-white/20">
          <Plane size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg">ยังไม่มีข้อมูล</p>
          <p className="text-sm mt-1">รอ GitHub Actions รันครั้งแรก {route.schedule}</p>
        </div>
      )}

      {data.length > 0 && (
        <>
          <section>
            <h2 className="text-xl font-bold mb-4 text-orange-300">🏆 ราคาถูกที่สุด</h2>
            <BestDealCards data={data} />
          </section>

          <section className="space-y-6">
            <PriceByDepartureChart data={data} />
            <PriceHistoryChart data={data} />
          </section>

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
                      <tr key={i} className="border-t border-white/10 hover:bg-white/5 transition-colors">
                        <td className="px-4 py-3 whitespace-nowrap">{r.departure_date}</td>
                        <td className="px-4 py-3 whitespace-nowrap">{r.return_date}</td>
                        <td className="px-4 py-3 font-semibold">
                          <span className={
                            r.airline === "ANA"  ? "text-blue-300" :
                            r.airline === "JAL"  ? "text-red-300"  :
                            r.airline === "THAI" ? "text-purple-300" :
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
        ข้อมูลจาก Google Flights · อัปเดต {route.schedule}
      </footer>
    </>
  );
}
