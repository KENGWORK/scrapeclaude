"use client";
import { ExternalLink, Plane, TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";

interface Props {
  data: FlightRecord[];
  accentColor: string;
}

export default function DpsPriceCard({ data, accentColor }: Props) {
  if (!data.length) return null;

  const sorted = [...data].sort((a, b) => a.scrape_date.localeCompare(b.scrape_date));
  const latest = sorted[sorted.length - 1];
  const prev   = sorted.length > 1 ? sorted[sorted.length - 2] : null;

  const delta = prev ? latest.price_thb - prev.price_thb : 0;
  const pct   = prev ? Math.abs((delta / prev.price_thb) * 100).toFixed(1) : null;

  return (
    <div className="rounded-xl p-6 space-y-4"
         style={{
           background: `linear-gradient(135deg, ${accentColor}10 0%, transparent 100%)`,
           border: `1px solid ${accentColor}30`,
         }}>
      {/* Airline + route */}
      <div className="flex items-center gap-2">
        <Plane size={16} style={{ color: accentColor }} />
        <div>
          <div className="font-semibold text-sm" style={{ color: accentColor }}>
            {latest.airline}
          </div>
          <div className="text-xs" style={{ color: "var(--color-muted)" }}>
            HKT → DPS · ออก {latest.departure_date} · กลับ {latest.return_date}
          </div>
        </div>
      </div>

      {/* Price + delta */}
      <div className="flex items-end gap-4">
        <div className="font-data text-5xl font-bold text-white">
          ฿{latest.price_thb.toLocaleString()}
        </div>
        {prev && delta !== 0 && (
          <div className="mb-1.5 flex items-center gap-1 text-sm font-semibold"
               style={{ color: delta > 0 ? "#EF4444" : "#10B981" }}>
            {delta > 0
              ? <TrendingUp size={16} />
              : <TrendingDown size={16} />}
            {delta > 0 ? "+" : ""}{delta.toLocaleString()} ({pct}%)
            <span className="text-xs font-normal ml-1" style={{ color: "var(--color-muted)" }}>
              จากเมื่อวาน
            </span>
          </div>
        )}
        {prev && delta === 0 && (
          <div className="mb-1.5 flex items-center gap-1 text-sm" style={{ color: "var(--color-muted)" }}>
            <Minus size={14} />
            ราคาเท่าเดิม
          </div>
        )}
      </div>

      {/* Flight detail */}
      {latest.dep_time && (
        <div className="font-data text-sm" style={{ color: "var(--color-muted)" }}>
          {latest.dep_time} → {latest.arr_time}
          {latest.duration && <span className="ml-2 text-xs">({latest.duration})</span>}
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 pt-2">
        {[
          { label: "ราคาล่าสุด", value: `฿${latest.price_thb.toLocaleString()}` },
          {
            label: "ราคาต่ำสุด (ทั้งหมด)",
            value: `฿${Math.min(...data.map((r) => r.price_thb)).toLocaleString()}`,
          },
          {
            label: "ราคาสูงสุด (ทั้งหมด)",
            value: `฿${Math.max(...data.map((r) => r.price_thb)).toLocaleString()}`,
          },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg p-3 text-center"
               style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
            <div className="font-data font-bold text-white">{value}</div>
            <div className="text-xs mt-0.5" style={{ color: "var(--color-muted)" }}>{label}</div>
          </div>
        ))}
      </div>

      {latest.gf_link && (
        <a href={latest.gf_link} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-lg transition-all duration-150 cursor-pointer"
           style={{ background: accentColor + "20", color: accentColor, border: `1px solid ${accentColor}40` }}>
          <ExternalLink size={14} />
          ดูบน Google Flights
        </a>
      )}
    </div>
  );
}
