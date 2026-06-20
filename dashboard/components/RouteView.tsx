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
  accent: string;       // text/icon color
  accentBg: string;     // pastel bg
  accentBorder: string; // border color
}

export default function RouteView({
  nrtData, cnxData, dpsData,
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
      origin: "BKK", dest: "NRT",
      meta: "ANA · JAL · Thai Airways | ม.ค.–ก.พ. 2027 | 8 วัน 7 คืน",
      schedule: "14:00 & 23:00 ICT",
      data: nrtData,
      accent: "#1D4ED8",
      accentBg: "#D4FAFF",
      accentBorder: "#93C5FD",
    },
    {
      key: "cnx",
      label: "BKK → CNX",
      sublabel: "กรุงเทพ → เชียงใหม่",
      origin: "BKK", dest: "CNX",
      meta: "3 สายการบินถูกสุด | พ.ย. 2026–ม.ค. 2027 | 5 วัน 4 คืน",
      schedule: "11:00 ICT",
      data: cnxData,
      accent: "#15803D",
      accentBg: "#D7F5D3",
      accentBorder: "#86EFAC",
    },
    {
      key: "dps",
      label: "HKT → DPS",
      sublabel: "ภูเก็ต → บาหลี",
      origin: "HKT", dest: "DPS",
      meta: "Indonesia AirAsia | 1–9 ก.ย. 2026 | 8 วัน 7 คืน",
      schedule: "11:00 ICT",
      data: dpsData,
      accent: "#7C3AED",
      accentBg: "#F1D4FF",
      accentBorder: "#C4B5FD",
    },
  ];

  const [activeKey, setActiveKey] = useState<RouteKey>("nrt");
  const route = routes.find((r) => r.key === activeKey)!;
  const data = route.data;
  const isDps = activeKey === "dps";

  const lastUpdated = data.length
    ? data.reduce((a, b) => (a.scrape_date > b.scrape_date ? a : b)).scrape_date
    : null;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-5">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
             style={{ background: "#D4FAFF", border: "1px solid #93C5FD" }}>
          <Plane size={18} style={{ color: "#1D4ED8" }} />
        </div>
        <div>
          <h1 className="text-xl font-bold" style={{ color: "var(--color-text)" }}>
            Flight Price Monitor
          </h1>
          <p className="text-sm" style={{ color: "var(--color-muted)" }}>
            ติดตามราคาตั๋วเครื่องบินอัตโนมัติ · อัปเดตทุกวัน
          </p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2 p-1.5 rounded-2xl"
           style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)", boxShadow: "0 1px 4px rgba(0,0,0,0.06)" }}>
        {routes.map((r) => {
          const isActive = activeKey === r.key;
          return (
            <button
              key={r.key}
              onClick={() => setActiveKey(r.key)}
              className="flex-1 flex flex-col items-center gap-0.5 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer"
              style={isActive ? {
                background: r.accentBg,
                color: r.accent,
                border: `1.5px solid ${r.accentBorder}`,
                boxShadow: `0 2px 8px ${r.accent}18`,
              } : {
                color: "var(--color-muted)",
                border: "1.5px solid transparent",
                background: "transparent",
              }}
            >
              <span className="font-bold tracking-wide text-base">{r.label}</span>
              <span className="text-xs font-normal opacity-75">{r.sublabel}</span>
            </button>
          );
        })}
      </div>

      {/* Info bar */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 px-4 py-2.5 rounded-xl text-sm"
           style={{ background: route.accentBg, border: `1px solid ${route.accentBorder}` }}>
        <span className="flex items-center gap-1.5" style={{ color: route.accent }}>
          <Calendar size={13} />
          {route.meta}
        </span>
        <span className="flex items-center gap-1.5 ml-auto" style={{ color: route.accent, opacity: 0.7 }}>
          <Clock size={13} />
          อัปเดต {route.schedule}
        </span>
        {lastUpdated && (
          <span className="flex items-center gap-1.5" style={{ color: route.accent, opacity: 0.7 }}>
            <RefreshCw size={13} />
            ล่าสุด {lastUpdated}
          </span>
        )}
      </div>

      {/* No data */}
      {!data.length && (
        <div className="flex flex-col items-center justify-center py-24 rounded-2xl"
             style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)" }}>
          <Plane size={40} style={{ color: route.accent, opacity: 0.25 }} className="mb-4" />
          <p className="font-semibold" style={{ color: "var(--color-muted)" }}>ยังไม่มีข้อมูล</p>
          <p className="text-sm mt-1" style={{ color: "var(--color-muted)", opacity: 0.7 }}>
            รอ GitHub Actions รันครั้งแรก · {route.schedule}
          </p>
        </div>
      )}

      {data.length > 0 && (
        <div className="space-y-5">

          {isDps ? (
            <DpsPriceCard data={data} accentColor={route.accent} accentBg={route.accentBg} accentBorder={route.accentBorder} />
          ) : (
            <>
              <SectionLabel icon={<TrendingDown size={14} />} title="ราคาถูกสุด" color={route.accent} />
              <BestDealCards data={data} routeKey={activeKey} accentColor={route.accent} accentBg={route.accentBg} accentBorder={route.accentBorder} />
            </>
          )}

          {!isDps && <PriceByDepartureChart data={data} routeKey={activeKey} accentColor={route.accent} />}
          <PriceHistoryChart data={data} routeKey={activeKey} accentColor={route.accent} />

          <SectionLabel icon={<Calendar size={14} />} title="ข้อมูลทั้งหมด" color={route.accent} />
          <DataTable data={data} accentColor={route.accent} />
        </div>
      )}
    </div>
  );
}

function SectionLabel({ icon, title, color }: { icon: React.ReactNode; title: string; color: string }) {
  return (
    <div className="flex items-center gap-2 pt-1">
      <span style={{ color }}>{icon}</span>
      <h2 className="text-sm font-bold uppercase tracking-widest" style={{ color, opacity: 0.85 }}>
        {title}
      </h2>
    </div>
  );
}

function DataTable({ data, accentColor }: { data: FlightRecord[]; accentColor: string }) {
  const sorted = [...data].sort((a, b) => {
    if (a.departure_date !== b.departure_date) return a.departure_date.localeCompare(b.departure_date);
    return a.price_thb - b.price_thb;
  });

  const AIRLINE_COLOR: Record<string, string> = {
    ANA: "#1D4ED8", JAL: "#DC2626", THAI: "#9333EA",
  };

  return (
    <div className="overflow-x-auto rounded-2xl"
         style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)", boxShadow: "0 1px 4px rgba(0,0,0,0.05)" }}>
      <table className="w-full text-sm">
        <thead>
          <tr style={{ borderBottom: "1px solid var(--color-border-md)" }}>
            {["วันที่ดึงข้อมูล", "วันออกเดินทาง", "วันกลับ", "สายการบิน", "ราคา (THB)", "เวลาออก", "เวลาถึง", "ระยะเวลา", ""].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider whitespace-nowrap"
                  style={{ color: "var(--color-muted)", background: "#FAFAFA" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => {
            const color = AIRLINE_COLOR[r.airline] ?? accentColor;
            return (
              <tr key={i} className="transition-colors"
                  style={{ borderBottom: "1px solid var(--color-border)", background: i % 2 === 0 ? "#FFFFFF" : "#FAFFFE" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#F8F9FF")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = i % 2 === 0 ? "#FFFFFF" : "#FAFFFE")}>
                <td className="px-4 py-3 font-data text-xs" style={{ color: "var(--color-muted)" }}>
                  {r.scrape_date.slice(0, 10)}
                </td>
                <td className="px-4 py-3 font-data text-xs whitespace-nowrap font-medium">{r.departure_date}</td>
                <td className="px-4 py-3 font-data text-xs whitespace-nowrap">{r.return_date}</td>
                <td className="px-4 py-3">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold"
                        style={{ background: color + "15", color }}>
                    {r.airline}
                  </span>
                </td>
                <td className="px-4 py-3 font-data font-bold whitespace-nowrap" style={{ color: "var(--color-text)" }}>
                  ฿{r.price_thb.toLocaleString()}
                </td>
                <td className="px-4 py-3 font-data text-xs" style={{ color: "var(--color-muted)" }}>{r.dep_time || "–"}</td>
                <td className="px-4 py-3 font-data text-xs" style={{ color: "var(--color-muted)" }}>{r.arr_time || "–"}</td>
                <td className="px-4 py-3 text-xs" style={{ color: "var(--color-muted)" }}>{r.duration || "–"}</td>
                <td className="px-4 py-3">
                  {r.gf_link && (
                    <a href={r.gf_link} target="_blank" rel="noopener noreferrer"
                       className="text-xs font-semibold cursor-pointer transition-opacity hover:opacity-70"
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
  );
}
