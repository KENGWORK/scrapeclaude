"use client";

import { useState } from "react";
import { Plane, Clock, Calendar, TrendingDown, RefreshCw, ChevronRight } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";
import BestDealCards from "./BestDealCard";
import PriceByDepartureChart from "./PriceByDepartureChart";
import PriceHistoryChart from "./PriceHistoryChart";
import FlightModal from "./FlightModal";

export type RouteKey = "nrt" | "kix";

interface RouteConfig {
  key: RouteKey;
  label: string;
  sublabel: string;
  meta: string;
  schedule: string;
  data: FlightRecord[];
  accent: string;
  accentBg: string;
  accentBorder: string;
}

export default function RouteView({
  nrtData, kixData,
}: {
  nrtData: FlightRecord[];
  kixData: FlightRecord[];
}) {
  const routes: RouteConfig[] = [
    {
      key: "nrt",
      label: "BKK → NRT",
      sublabel: "กรุงเทพ → โตเกียว",
      meta: "ANA · JAL · Thai Airways | ม.ค.–ก.พ. 2027 | 8 วัน 7 คืน",
      schedule: "14:00 & 23:00 ICT",
      data: nrtData,
      accent: "#1D4ED8", accentBg: "#D4FAFF", accentBorder: "#93C5FD",
    },
    {
      key: "kix",
      label: "BKK → KIX",
      sublabel: "กรุงเทพ → โอซาก้า",
      meta: "บินตรง · 3 สายการบินถูกสุด | ธ.ค. 2026–ก.พ. 2027 | 7 วัน 6 คืน",
      schedule: "13:00 ICT",
      data: kixData,
      accent: "#BE185D", accentBg: "#FCE0EC", accentBorder: "#F9A8D4",
    },
  ];

  const [activeKey, setActiveKey] = useState<RouteKey>("nrt");
  const [modalRecord, setModalRecord] = useState<FlightRecord | null>(null);

  const route = routes.find((r) => r.key === activeKey)!;
  const data = route.data;

  const latestScrape = data.length
    ? data.reduce((a, b) => (a.scrape_date > b.scrape_date ? a : b)).scrape_date
    : null;

  const bestPrice = data.length
    ? Math.min(...data.map((r) => r.price_thb))
    : null;

  return (
    <>
      {/* Sidebar + Content layout */}
      <div className="flex min-h-screen">

        {/* ── Sidebar ── */}
        <aside className="hidden md:flex flex-col w-64 flex-shrink-0 sticky top-0 h-screen"
               style={{ background: "#FFFFFF", borderRight: "1px solid var(--color-border-md)" }}>

          {/* App brand */}
          <div className="flex items-center gap-2.5 px-5 py-5"
               style={{ borderBottom: "1px solid var(--color-border)" }}>
            <div className="w-8 h-8 rounded-xl flex items-center justify-center"
                 style={{ background: "#D4FAFF", border: "1px solid #93C5FD" }}>
              <Plane size={16} style={{ color: "#1D4ED8" }} />
            </div>
            <div>
              <div className="font-bold text-sm" style={{ color: "var(--color-text)" }}>Flight Monitor</div>
              <div className="text-xs" style={{ color: "var(--color-muted)" }}>ราคาตั๋วรายวัน</div>
            </div>
          </div>

          {/* Route list */}
          <nav className="flex-1 px-3 py-4 space-y-1.5">
            <div className="text-xs font-bold uppercase tracking-widest px-2 mb-3"
                 style={{ color: "var(--color-muted)", opacity: 0.6 }}>
              เส้นทาง
            </div>
            {routes.map((r) => {
              const isActive = activeKey === r.key;
              const lastPrice = r.data.length
                ? Math.min(...r.data.map((d) => d.price_thb))
                : null;
              return (
                <button
                  key={r.key}
                  onClick={() => setActiveKey(r.key)}
                  className="w-full flex items-center gap-3 px-3 py-3 rounded-2xl transition-all duration-200 cursor-pointer text-left"
                  style={isActive ? {
                    background: r.accentBg,
                    border: `1.5px solid ${r.accentBorder}`,
                  } : {
                    background: "transparent",
                    border: "1.5px solid transparent",
                  }}
                >
                  <div className="w-8 h-8 flex-shrink-0 rounded-xl flex items-center justify-center"
                       style={{ background: isActive ? r.accent + "15" : "var(--color-surface-2)", border: `1px solid ${isActive ? r.accentBorder : "var(--color-border)"}` }}>
                    <Plane size={13} style={{ color: isActive ? r.accent : "var(--color-muted)" }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-sm truncate"
                         style={{ color: isActive ? r.accent : "var(--color-text)" }}>
                      {r.label}
                    </div>
                    <div className="text-xs truncate" style={{ color: "var(--color-muted)" }}>
                      {r.sublabel}
                    </div>
                  </div>
                  {lastPrice && (
                    <div className="text-xs font-data font-bold flex-shrink-0"
                         style={{ color: isActive ? r.accent : "var(--color-muted)" }}>
                      ฿{(lastPrice / 1000).toFixed(0)}k
                    </div>
                  )}
                  {!r.data.length && (
                    <div className="text-xs flex-shrink-0" style={{ color: "var(--color-muted)", opacity: 0.5 }}>–</div>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Sidebar footer */}
          <div className="px-5 py-4" style={{ borderTop: "1px solid var(--color-border)" }}>
            <div className="text-xs" style={{ color: "var(--color-muted)", opacity: 0.7 }}>
              <div className="flex items-center gap-1.5 mb-0.5">
                <RefreshCw size={10} />
                {latestScrape ? `อัปเดต ${latestScrape.slice(0, 10)}` : "ยังไม่มีข้อมูล"}
              </div>
              <div className="flex items-center gap-1.5">
                <Clock size={10} />
                {route.schedule}
              </div>
            </div>
          </div>
        </aside>

        {/* ── Mobile top tabs ── */}
        <div className="md:hidden fixed top-0 left-0 right-0 z-40 px-3 py-2"
             style={{ background: "#FFFFFF", borderBottom: "1px solid var(--color-border-md)", boxShadow: "0 1px 6px rgba(0,0,0,0.06)" }}>
          <div className="flex gap-1.5">
            {routes.map((r) => {
              const isActive = activeKey === r.key;
              return (
                <button key={r.key} onClick={() => setActiveKey(r.key)}
                  className="flex-1 py-2 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer"
                  style={isActive ? { background: r.accentBg, color: r.accent, border: `1px solid ${r.accentBorder}` }
                    : { background: "transparent", color: "var(--color-muted)", border: "1px solid transparent" }}>
                  {r.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Main content ── */}
        <main className="flex-1 min-w-0 md:overflow-y-auto px-5 py-6 md:py-8 mt-12 md:mt-0 space-y-6"
              style={{ background: "var(--color-bg)" }}>

          {/* Page header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold" style={{ color: "var(--color-text)" }}>
                {route.label}
              </h1>
              <p className="text-sm mt-0.5 flex items-center gap-1.5" style={{ color: "var(--color-muted)" }}>
                <Calendar size={12} />
                {route.meta}
              </p>
              {latestScrape && (
                <p className="text-xs mt-1.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-medium"
                   style={{ background: route.accentBg, color: route.accent, border: `1px solid ${route.accentBorder}` }}>
                  <RefreshCw size={11} />
                  ดึงข้อมูลล่าสุด {formatScrapeTime(latestScrape)}
                </p>
              )}
            </div>
            {bestPrice && (
              <div className="flex-shrink-0 text-right">
                <div className="text-xs font-semibold uppercase tracking-wider mb-0.5"
                     style={{ color: route.accent, opacity: 0.7 }}>ราคาต่ำสุด</div>
                <div className="font-data text-xl font-bold" style={{ color: "var(--color-text)" }}>
                  ฿{bestPrice.toLocaleString()}
                </div>
              </div>
            )}
          </div>

          {/* No data */}
          {!data.length && (
            <div className="flex flex-col items-center justify-center py-24 rounded-3xl"
                 style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)" }}>
              <Plane size={40} style={{ color: route.accent, opacity: 0.2 }} className="mb-4" />
              <p className="font-semibold" style={{ color: "var(--color-muted)" }}>ยังไม่มีข้อมูล</p>
              <p className="text-sm mt-1" style={{ color: "var(--color-muted)", opacity: 0.6 }}>
                รอ GitHub Actions รันครั้งแรก · {route.schedule}
              </p>
            </div>
          )}

          {data.length > 0 && (
            <div className="space-y-6">

              {/* Best deals */}
              <SectionLabel icon={<TrendingDown size={13} />} title="ราคาถูกสุด" color={route.accent} />
              <BestDealCards data={data} routeKey={activeKey}
                accentColor={route.accent} accentBg={route.accentBg} accentBorder={route.accentBorder} />

              {/* Charts */}
              <PriceByDepartureChart data={data} routeKey={activeKey} accentColor={route.accent} />
              <PriceHistoryChart data={data} routeKey={activeKey} accentColor={route.accent} />

              {/* Data table */}
              <SectionLabel icon={<Calendar size={13} />} title="ข้อมูลทั้งหมด" color={route.accent} />
              <DataTable data={data} accentColor={route.accent} onViewDetail={setModalRecord} />
            </div>
          )}
        </main>
      </div>

      {/* Modal */}
      <FlightModal
        record={modalRecord}
        accentColor={route.accent}
        accentBg={route.accentBg}
        accentBorder={route.accentBorder}
        onClose={() => setModalRecord(null)}
      />
    </>
  );
}

const TH_MONTHS = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."];

// scrape_date stored as "YYYY-MM-DD HH:MM" → "D เดือน YYYY เวลา HH:MM น."
function formatScrapeTime(raw: string): string {
  const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/);
  if (!m) return raw;
  const [, y, mo, d, hh, mm] = m;
  const day = parseInt(d, 10);
  const month = TH_MONTHS[parseInt(mo, 10) - 1] ?? mo;
  const datePart = `${day} ${month} ${y}`;
  return hh ? `${datePart} เวลา ${hh}:${mm} น.` : datePart;
}

function SectionLabel({ icon, title, color }: { icon: React.ReactNode; title: string; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span style={{ color }}>{icon}</span>
      <h2 className="text-xs font-bold uppercase tracking-widest" style={{ color, opacity: 0.8 }}>{title}</h2>
    </div>
  );
}

const AIRLINE_COLOR: Record<string, string> = {
  ANA: "#1D4ED8", JAL: "#DC2626", THAI: "#9333EA",
};

function DataTable({ data, accentColor, onViewDetail }: {
  data: FlightRecord[];
  accentColor: string;
  onViewDetail: (r: FlightRecord) => void;
}) {
  const sorted = [...data].sort((a, b) => {
    if (a.departure_date !== b.departure_date) return a.departure_date.localeCompare(b.departure_date);
    return a.price_thb - b.price_thb;
  });

  return (
    <div className="overflow-x-auto rounded-2xl"
         style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)", boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }}>
      <table className="w-full text-sm">
        <thead>
          <tr style={{ borderBottom: "1px solid var(--color-border-md)", background: "#FAFAFA" }}>
            {["วันออกเดินทาง", "วันกลับ", "สายการบิน", "ราคา (THB)", "เวลา", "ระยะเวลา", ""].map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider whitespace-nowrap"
                  style={{ color: "var(--color-muted)" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => {
            const color = AIRLINE_COLOR[r.airline] ?? accentColor;
            return (
              <tr key={i}
                  style={{ borderBottom: "1px solid var(--color-border)", background: i % 2 === 0 ? "#FFFFFF" : "#FAFFFE" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#F5F3FF")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = i % 2 === 0 ? "#FFFFFF" : "#FAFFFE")}>
                <td className="px-4 py-3 font-data text-xs font-medium">{r.departure_date}</td>
                <td className="px-4 py-3 font-data text-xs">{r.return_date}</td>
                <td className="px-4 py-3">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold"
                        style={{ background: color + "15", color }}>
                    {r.airline}
                  </span>
                </td>
                <td className="px-4 py-3 font-data font-bold" style={{ color: "var(--color-text)" }}>
                  ฿{r.price_thb.toLocaleString()}
                </td>
                <td className="px-4 py-3 font-data text-xs" style={{ color: "var(--color-muted)" }}>
                  {r.dep_time ? `${r.dep_time} → ${r.arr_time}` : "–"}
                </td>
                <td className="px-4 py-3 text-xs" style={{ color: "var(--color-muted)" }}>
                  {r.duration || "–"}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => onViewDetail(r)}
                    className="inline-flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all duration-150 cursor-pointer hover:opacity-80"
                    style={{ background: accentColor + "12", color: accentColor, border: `1px solid ${accentColor}25` }}
                  >
                    ดูราคา
                    <ChevronRight size={11} />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
