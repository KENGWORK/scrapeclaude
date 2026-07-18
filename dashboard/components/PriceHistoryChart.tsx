"use client";
import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import type { FlightRecord } from "@/app/api/flights/route";
import type { RouteKey } from "./RouteView";

const NRT_COLORS: Record<string, string> = { ANA: "#1D4ED8", JAL: "#DC2626", THAI: "#9333EA" };
const TOP_PALETTE = ["#15803D", "#D97706", "#1D4ED8", "#DC2626", "#9333EA"];

interface Props { data: FlightRecord[]; routeKey: RouteKey; accentColor: string; }

export default function PriceHistoryChart({ data, routeKey, accentColor }: Props) {
  return <MultiHistory data={data} routeKey={routeKey} accentColor={accentColor} />;
}

function MultiHistory({ data, routeKey, accentColor }: Props) {
  const departureDates = Array.from(new Set(data.map((r) => r.departure_date))).sort();
  const [selected, setSelected] = useState(departureDates[0] ?? "");

  const filtered = data.filter((r) => r.departure_date === selected);
  const byDate: Record<string, Record<string, number>> = {};
  filtered.forEach((r) => {
    const d = r.scrape_date.slice(0, 10);
    if (!byDate[d]) byDate[d] = {};
    byDate[d][r.airline] = r.price_thb;
  });
  const chartData = Object.entries(byDate).sort(([a], [b]) => a.localeCompare(b))
    .map(([date, prices]) => ({ date: date.slice(5), ...prices }));

  const airlines = routeKey === "nrt"
    ? ["ANA", "JAL", "THAI"]
    : Array.from(new Set(filtered.map((r) => r.airline)));

  function getColor(a: string, i: number) {
    return routeKey === "nrt" ? (NRT_COLORS[a] ?? accentColor) : TOP_PALETTE[i % TOP_PALETTE.length];
  }

  return (
    <ChartCard
      title="แนวโน้มราคาตามเวลา"
      subtitle={`วันออกเดินทาง ${selected}`}
      action={
        <select value={selected} onChange={(e) => setSelected(e.target.value)}
          className="text-xs px-2.5 py-1.5 rounded-lg cursor-pointer transition-colors"
          style={{ background: "#F9FAFB", border: "1px solid var(--color-border-md)", color: "var(--color-text)", outline: "none" }}>
          {departureDates.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      }
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
          <XAxis dataKey="date" stroke="#D1D5DB" tick={{ fontSize: 10, fill: "#9CA3AF" }} />
          <YAxis stroke="#D1D5DB" tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickFormatter={(v) => `฿${(v / 1000).toFixed(0)}k`} />
          <Tooltip content={<MultiTooltip getColor={getColor} />} />
          {airlines.map((a, i) => (
            <Line key={a} type="monotone" dataKey={a} stroke={getColor(a, i)} strokeWidth={2.5}
              dot={{ r: 3, fill: getColor(a, i), strokeWidth: 0 }} activeDot={{ r: 5 }} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function ChartCard({ title, subtitle, action, children }: {
  title: string; subtitle: string; action?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl p-5"
         style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)", boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }}>
      <div className="flex flex-col sm:flex-row sm:items-start gap-2 mb-4">
        <div className="flex-1">
          <h2 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>{title}</h2>
          <p className="text-xs mt-0.5" style={{ color: "var(--color-muted)" }}>{subtitle}</p>
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

function MultiTooltip({ active, payload, label, getColor }: {
  active?: boolean; payload?: { name: string; value: number }[]; label?: string;
  getColor: (n: string, i: number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl px-3 py-2.5 shadow-lg text-xs"
         style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)" }}>
      <div className="font-semibold mb-1.5" style={{ color: "var(--color-muted)" }}>{label}</div>
      {payload.map((p, i) => (
        <div key={p.name} className="flex items-center gap-2 py-0.5">
          <span className="w-2 h-2 rounded-full" style={{ background: getColor(p.name, i) }} />
          <span style={{ color: "var(--color-text)" }}>{p.name}</span>
          <span className="font-data font-bold ml-auto pl-3" style={{ color: getColor(p.name, i) }}>
            ฿{p.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}
