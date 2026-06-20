"use client";
import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import type { FlightRecord } from "@/app/api/flights/route";
import type { RouteKey } from "./RouteView";

const NRT_COLORS: Record<string, string> = {
  ANA:  "#3B82F6",
  JAL:  "#EF4444",
  THAI: "#A855F7",
};

interface Props {
  data: FlightRecord[];
  routeKey: RouteKey;
  accentColor: string;
}

export default function PriceHistoryChart({ data, routeKey, accentColor }: Props) {
  if (routeKey === "dps") return <DpsHistoryChart data={data} accentColor={accentColor} />;
  return <MultiDateHistoryChart data={data} routeKey={routeKey} accentColor={accentColor} />;
}

function DpsHistoryChart({ data, accentColor }: { data: FlightRecord[]; accentColor: string }) {
  const chartData = [...data]
    .sort((a, b) => a.scrape_date.localeCompare(b.scrape_date))
    .map((r) => ({
      date: r.scrape_date.slice(0, 10),
      price: r.price_thb,
    }));

  const minPrice = Math.min(...chartData.map((d) => d.price));
  const minDate  = chartData.find((d) => d.price === minPrice)?.date;

  return (
    <ChartCard title="แนวโน้มราคา" subtitle="ราคาที่ดึงข้อมูลได้แต่ละวัน">
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="date" stroke="#475569" tick={{ fontSize: 10, fill: "#64748B" }} />
          <YAxis stroke="#475569" tick={{ fontSize: 10, fill: "#64748B" }}
            tickFormatter={(v) => `฿${(v / 1000).toFixed(1)}k`} />
          <Tooltip content={<SingleTooltip color={accentColor} label="ราคา" />} />
          {minDate && (
            <ReferenceLine x={minDate} stroke={accentColor} strokeDasharray="4 4" opacity={0.5} />
          )}
          <Line type="monotone" dataKey="price"
            stroke={accentColor} strokeWidth={2.5}
            dot={{ r: 3, fill: accentColor, strokeWidth: 0 }}
            activeDot={{ r: 5, fill: accentColor }}
          />
        </LineChart>
      </ResponsiveContainer>
      {minDate && (
        <p className="text-xs mt-2" style={{ color: "var(--color-muted)" }}>
          ราคาต่ำสุด ฿{minPrice.toLocaleString()} เมื่อ {minDate}
        </p>
      )}
    </ChartCard>
  );
}

function MultiDateHistoryChart({ data, routeKey, accentColor }: Props) {
  const departureDates = Array.from(new Set(data.map((r) => r.departure_date))).sort();
  const [selected, setSelected] = useState(departureDates[0] ?? "");

  const filtered = data.filter((r) => r.departure_date === selected);

  const byDate: Record<string, Record<string, number>> = {};
  filtered.forEach((r) => {
    const d = r.scrape_date.slice(0, 10);
    if (!byDate[d]) byDate[d] = {};
    byDate[d][r.airline] = r.price_thb;
  });

  const chartData = Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, prices]) => ({ date: date.slice(5), ...prices }));

  const airlines = routeKey === "nrt"
    ? ["ANA", "JAL", "THAI"]
    : Array.from(new Set(filtered.map((r) => r.airline)));

  const CNX_PALETTE = ["#10B981", "#F59E0B", "#3B82F6", "#EF4444", "#A855F7"];

  function getColor(airline: string, idx: number) {
    if (routeKey === "nrt") return NRT_COLORS[airline] ?? accentColor;
    return CNX_PALETTE[idx % CNX_PALETTE.length];
  }

  return (
    <ChartCard
      title="แนวโน้มราคาตามเวลา"
      subtitle={`ติดตามราคาวันออกเดินทาง ${selected}`}
      action={
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="text-xs px-2.5 py-1.5 rounded-lg cursor-pointer transition-colors"
          style={{
            background: "rgba(255,255,255,0.06)",
            border: "1px solid rgba(255,255,255,0.12)",
            color: "#E2E8F0",
            outline: "none",
          }}
        >
          {departureDates.map((d) => (
            <option key={d} value={d} style={{ background: "#1E293B" }}>{d}</option>
          ))}
        </select>
      }
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="date" stroke="#475569" tick={{ fontSize: 10, fill: "#64748B" }} />
          <YAxis stroke="#475569" tick={{ fontSize: 10, fill: "#64748B" }}
            tickFormatter={(v) => `฿${(v / 1000).toFixed(0)}k`} />
          <Tooltip content={<MultiTooltip getColor={getColor} />} />
          {airlines.map((airline, i) => (
            <Line key={airline} type="monotone" dataKey={airline}
              stroke={getColor(airline, i)} strokeWidth={2}
              dot={{ r: 3, fill: getColor(airline, i), strokeWidth: 0 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function ChartCard({ title, subtitle, action, children }: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl p-5"
         style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
      <div className="flex flex-col sm:flex-row sm:items-start gap-2 mb-4">
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-white">{title}</h2>
          <p className="text-xs mt-0.5" style={{ color: "var(--color-muted)" }}>{subtitle}</p>
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

function SingleTooltip({ active, payload, label, color, label: lbl }: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
  color: string;
  label: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-3 py-2 shadow-xl text-xs"
         style={{ background: "#1E293B", border: "1px solid rgba(255,255,255,0.1)" }}>
      <div style={{ color: "#94A3B8" }} className="mb-1">{label}</div>
      <div className="font-data font-bold" style={{ color }}>
        ฿{payload[0].value.toLocaleString()}
      </div>
    </div>
  );
}

function MultiTooltip({ active, payload, label, getColor }: {
  active?: boolean;
  payload?: { name: string; value: number }[];
  label?: string;
  getColor: (name: string, i: number) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-3 py-2 shadow-xl text-xs"
         style={{ background: "#1E293B", border: "1px solid rgba(255,255,255,0.1)" }}>
      <div className="font-semibold mb-1.5" style={{ color: "#94A3B8" }}>{label}</div>
      {payload.map((p, i) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: getColor(p.name, i) }} />
          <span style={{ color: "#CBD5E1" }}>{p.name}</span>
          <span className="font-data font-bold ml-auto pl-3" style={{ color: getColor(p.name, i) }}>
            ฿{p.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}
