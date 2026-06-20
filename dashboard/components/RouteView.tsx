"use client";

import { useState } from "react";
import { Plane, Clock, Calendar, TrendingDown, RefreshCw } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";
import BestDealCards from "./BestDealCard";
import PriceByDepartureChart from "./PriceByDepartureChart";
import PriceHistoryChart from "./PriceHistoryChart";
import DpsPriceCard from "./DpsPriceCard";

export type RouteKey = "nrt" | "cnx" | "dps";

interface RouteConfig {
  key: RouteKey;
  label: string;
  sublabel: string;
  origin: string;
  dest: string;
  meta: string;
  schedule: string;
  data: FlightRecord[];
  accentColor: string;
}

export default function RouteView({
  nrtData,
  cnxData,
  dpsData,
}: {
  nrtData: FlightRecord[];
  cnxData: FlightRecord[];
  dpsData: FlightRecord[];
}) {
  const routes: RouteConfig[] = [
    {
      key: "nrt",
      label: "BKK → NRT",
      sublabel: "กรุงเทพ → โตเกียว",
      origin: "BKK",
      dest: "NRT",
      meta: "ANA · JAL · Thai Airways | ม.ค.–ก.พ. 2027 | 8 วัน 7 คืน",
      schedule: "14:00 & 23:00 ICT",
      data: nrtData,
      accentColor: "#3B82F6",
    },
    {
      key: "cnx",
      label: "BKK → CNX",
      sublabel: "กรุงเทพ → เชียงใหม่",
      origin: "BKK",
      dest: "CNX",
      meta: "3 สายการบินถูกสุด | พ.ย. 2026–ม.ค. 2027 | 5 วัน 4 คืน",
      schedule: "11:00 ICT",
      data: cnxData,
      accentColor: "#10B981",
    },
    {
      key: "dps",
      label: "HKT → DPS",
      sublabel: "ภูเก็ต → บาหลี",
      origin: "HKT",
      dest: "DPS",
      meta: "Indonesia AirAsia | 1–9 ก.ย. 2026 | 8 วัน 7 คืน",
      schedule: "11:00 ICT",
      data: dpsData,
      accentColor: "#F59E0B",
    },
  ];

  const [activeKey, setActiveKey] = useState<RouteKey>("nrt");
  const route = routes.find((r) => r.key === activeKey)!;
  const data = route.data;

  const lastUpdated = data.length
    ? data.reduce((a, b) => (a.scrape_date > b.scrape_date ? a : b)).scrape_date
    : null;

  const isDps = activeKey === "dps";

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center"
             style={{ background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.3)" }}>
          <Plane size={16} style={{ color: "#3B82F6" }} />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight">Flight Price Monitor</h1>
          <p className="text-xs" style={{ color: "var(--color-muted)" }}>
            ติดตามราคาตั๋วเครื่องบินอัตโนมัติ · อัปเดตทุกวัน
          </p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2 p-1 rounded-xl"
           style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
        {routes.map((r) => {
          const isActive = activeKey === r.key;
          return (
            <button
              key={r.key}
              onClick={() => setActiveKey(r.key)}
              className="flex-1 flex flex-col items-center gap-0.5 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 cursor-pointer"
              style={isActive ? {
                background: r.accentColor + "20",
                color: r.accentColor,
                border: `1px solid ${r.accentColor}40`,
              } : {
                color: "var(--color-muted)",
                border: "1px solid transparent",
              }}
            >
              <span className="font-bold tracking-wide">{r.label}</span>
              <span className="text-xs font-normal opacity-70">{r.sublabel}</span>
            </button>
          );
        })}
      </div>

      {/* Route info bar */}
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 rounded-xl text-xs"
           style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", color: "var(--color-muted)" }}>
        <span className="flex items-center gap-1.5">
          <Calendar size={12} />
          {route.meta}
        </span>
        <span className="flex items-center gap-1.5 ml-auto">
          <Clock size={12} />
          อัปเดต {route.schedule}
        </span>
        {lastUpdated && (
          <span className="flex items-center gap-1.5">
            <RefreshCw size={12} />
            ล่าสุด {lastUpdated}
          </span>
        )}
      </div>

      {/* No data state */}
      {!data.length && (
        <div className="flex flex-col items-center justify-center py-24 rounded-2xl"
             style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
          <Plane size={40} style={{ color: "var(--color-muted)", opacity: 0.4 }} className="mb-4" />
          <p className="font-semibold text-white/40">ยังไม่มีข้อมูล</p>
          <p className="text-sm mt-1" style={{ color: "var(--color-muted)" }}>
            รอ GitHub Actions รันครั้งแรก · {route.schedule}
          </p>
        </div>
      )}

      {data.length > 0 && (
        <div className="space-y-6">
          {/* Best deals */}
          {isDps ? (
            <DpsPriceCard data={data} accentColor={route.accentColor} />
          ) : (
            <>
              <SectionHeader icon={<TrendingDown size={15} />} title="ราคาถูกสุด" />
              <BestDealCards data={data} routeKey={activeKey} />
            </>
          )}

          {/* Charts */}
          {!isDps && <PriceByDepartureChart data={data} routeKey={activeKey} accentColor={route.accentColor} />}
          <PriceHistoryChart data={data} routeKey={activeKey} accentColor={route.accentColor} />

          {/* Data table */}
          <DataTable data={data} routeKey={activeKey} accentColor={route.accentColor} />
        </div>
      )}
    </div>
  );
}

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2">
      <span style={{ color: "var(--color-amber)" }}>{icon}</span>
      <h2 className="text-sm font-semibold tracking-wide uppercase"
          style={{ color: "var(--color-amber)", letterSpacing: "0.08em" }}>
        {title}
      </h2>
    </div>
  );
}

const AIRLINE_ACCENT: Record<string, string> = {
  ANA:  "#3B82F6",
  JAL:  "#EF4444",
  THAI: "#A855F7",
};

function airlineColor(airline: string, fallback: string): string {
  return AIRLINE_ACCENT[airline] ?? fallback;
}

function DataTable({ data, routeKey, accentColor }: {
  data: FlightRecord[];
  routeKey: RouteKey;
  accentColor: string;
}) {
  const sorted = [...data].sort((a, b) => {
    if (a.departure_date !== b.departure_date) return a.departure_date.localeCompare(b.departure_date);
    return a.price_thb - b.price_thb;
  });

  return (
    <div>
      <SectionHeader icon={<Calendar size={15} />} title="ข้อมูลทั้งหมด" />
      <div className="mt-3 overflow-x-auto rounded-xl"
           style={{ border: "1px solid var(--color-border)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: "var(--color-surface)", borderBottom: "1px solid var(--color-border)" }}>
              {["วันที่ scrape", "วันออกเดินทาง", "วันกลับ", "สายการบิน", "ราคา (THB)", "เวลาออก", "เวลาถึง", "ระยะเวลา", ""].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider whitespace-nowrap"
                    style={{ color: "var(--color-muted)" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => {
              const color = airlineColor(r.airline, accentColor);
              return (
                <tr key={i}
                    className="transition-colors duration-150 hover:bg-white/[0.03]"
                    style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td className="px-4 py-3 font-data text-xs" style={{ color: "var(--color-muted)" }}>
                    {r.scrape_date.slice(0, 10)}
                  </td>
                  <td className="px-4 py-3 font-data text-xs whitespace-nowrap">{r.departure_date}</td>
                  <td className="px-4 py-3 font-data text-xs whitespace-nowrap">{r.return_date}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-md text-xs font-semibold"
                          style={{ background: color + "20", color: color }}>
                      {r.airline}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-data font-bold text-white whitespace-nowrap">
                    ฿{r.price_thb.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-data text-xs" style={{ color: "var(--color-muted)" }}>
                    {r.dep_time || "–"}
                  </td>
                  <td className="px-4 py-3 font-data text-xs" style={{ color: "var(--color-muted)" }}>
                    {r.arr_time || "–"}
                  </td>
                  <td className="px-4 py-3 text-xs" style={{ color: "var(--color-muted)" }}>
                    {r.duration || "–"}
                  </td>
                  <td className="px-4 py-3">
                    {r.gf_link && (
                      <a href={r.gf_link} target="_blank" rel="noopener noreferrer"
                         className="text-xs font-medium transition-colors duration-150 cursor-pointer"
                         style={{ color: accentColor }}>
                        ดูราคา →
                      </a>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
