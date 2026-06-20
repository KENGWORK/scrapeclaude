"use client";
import { ExternalLink, Plane, TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";

interface Props {
  data: FlightRecord[];
  accentColor: string;
  accentBg: string;
  accentBorder: string;
}

export default function DpsPriceCard({ data, accentColor, accentBg, accentBorder }: Props) {
  if (!data.length) return null;
  const sorted = [...data].sort((a, b) => a.scrape_date.localeCompare(b.scrape_date));
  const latest = sorted[sorted.length - 1];
  const prev   = sorted.length > 1 ? sorted[sorted.length - 2] : null;
  const delta  = prev ? latest.price_thb - prev.price_thb : 0;
  const pct    = prev && prev.price_thb ? Math.abs((delta / prev.price_thb) * 100).toFixed(1) : null;
  const minPrice = Math.min(...data.map((r) => r.price_thb));
  const maxPrice = Math.max(...data.map((r) => r.price_thb));

  return (
    <div className="rounded-2xl p-6 space-y-5"
         style={{ background: accentBg, border: `1.5px solid ${accentBorder}`, boxShadow: "0 2px 12px rgba(0,0,0,0.05)" }}>

      {/* Airline row */}
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-xl flex items-center justify-center"
             style={{ background: accentColor + "15", border: `1px solid ${accentBorder}` }}>
          <Plane size={15} style={{ color: accentColor }} />
        </div>
        <div>
          <div className="font-bold text-sm" style={{ color: accentColor }}>{latest.airline}</div>
          <div className="text-xs" style={{ color: "var(--color-muted)" }}>
            HKT → DPS · ออก {latest.departure_date} · กลับ {latest.return_date}
          </div>
        </div>
      </div>

      {/* Big price */}
      <div className="flex items-end gap-3">
        <div className="font-data text-5xl font-bold" style={{ color: "var(--color-text)" }}>
          ฿{latest.price_thb.toLocaleString()}
        </div>
        {prev && delta !== 0 && (
          <div className="mb-1.5 flex items-center gap-1 text-sm font-bold"
               style={{ color: delta > 0 ? "#DC2626" : "#15803D" }}>
            {delta > 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {delta > 0 ? "+" : ""}{delta.toLocaleString()} THB ({pct}%)
            <span className="text-xs font-normal ml-0.5" style={{ color: "var(--color-muted)" }}>จากเมื่อวาน</span>
          </div>
        )}
        {prev && delta === 0 && (
          <div className="mb-1.5 flex items-center gap-1 text-sm" style={{ color: "var(--color-muted)" }}>
            <Minus size={14} /> ราคาเท่าเดิม
          </div>
        )}
      </div>

      {latest.dep_time && (
        <div className="font-data text-sm" style={{ color: "var(--color-muted)" }}>
          {latest.dep_time} → {latest.arr_time}
          {latest.duration && <span className="ml-2 text-xs">({latest.duration})</span>}
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "ราคาล่าสุด",          value: `฿${latest.price_thb.toLocaleString()}` },
          { label: "ต่ำสุดที่พบ",          value: `฿${minPrice.toLocaleString()}` },
          { label: "สูงสุดที่พบ",          value: `฿${maxPrice.toLocaleString()}` },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-xl p-3 text-center"
               style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)" }}>
            <div className="font-data font-bold" style={{ color: "var(--color-text)" }}>{value}</div>
            <div className="text-xs mt-0.5" style={{ color: "var(--color-muted)" }}>{label}</div>
          </div>
        ))}
      </div>

      {latest.gf_link && (
        <a href={latest.gf_link} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-xl transition-all duration-150 cursor-pointer hover:opacity-80"
           style={{ background: "#FFFFFF", color: accentColor, border: `1.5px solid ${accentBorder}` }}>
          <ExternalLink size={14} />
          ดูบน Google Flights
        </a>
      )}
    </div>
  );
}
