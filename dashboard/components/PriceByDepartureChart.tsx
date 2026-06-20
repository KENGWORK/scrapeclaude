"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { FlightRecord } from "@/app/api/flights/route";
import type { RouteKey } from "./RouteView";

const NRT_SERIES = [
  { key: "ANA",  color: "#3B82F6" },
  { key: "JAL",  color: "#EF4444" },
  { key: "THAI", color: "#A855F7" },
];

interface Props {
  data: FlightRecord[];
  routeKey: RouteKey;
  accentColor: string;
}

export default function PriceByDepartureChart({ data, routeKey, accentColor }: Props) {
  const latestScrape = data.reduce((a, b) =>
    a.scrape_date > b.scrape_date ? a : b, data[0])?.scrape_date ?? "";
  const latest = data.filter((r) => r.scrape_date === latestScrape);

  if (routeKey === "nrt") {
    const byDate: Record<string, Record<string, number>> = {};
    latest.forEach((r) => {
      if (!byDate[r.departure_date]) byDate[r.departure_date] = {};
      byDate[r.departure_date][r.airline] = r.price_thb;
    });
    const chartData = Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, prices]) => ({ date: date.slice(5), ...prices }));

    return (
      <ChartCard title="ราคาตามวันออกเดินทาง" subtitle={`ข้อมูล ณ ${latestScrape}`}>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="date" stroke="#475569" tick={{ fontSize: 10, fill: "#64748B" }} />
            <YAxis stroke="#475569" tick={{ fontSize: 10, fill: "#64748B" }}
              tickFormatter={(v) => `฿${(v / 1000).toFixed(0)}k`} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 12, color: "#94A3B8" }} />
            {NRT_SERIES.map(({ key, color }) => (
              <Line key={key} type="monotone" dataKey={key}
                stroke={color} strokeWidth={2} dot={false} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    );
  }

  if (routeKey === "cnx") {
    const airlines = Array.from(new Set(latest.map((r) => r.airline)));
    const byDate: Record<string, Record<string, number>> = {};
    latest.forEach((r) => {
      if (!byDate[r.departure_date]) byDate[r.departure_date] = {};
      byDate[r.departure_date][r.airline] = r.price_thb;
    });
    const chartData = Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, prices]) => ({ date: date.slice(5), ...prices }));

    const CNX_PALETTE = ["#10B981", "#F59E0B", "#3B82F6", "#EF4444", "#A855F7"];

    return (
      <ChartCard title="ราคาตามวันออกเดินทาง" subtitle={`ข้อมูล ณ ${latestScrape}`}>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="date" stroke="#475569" tick={{ fontSize: 10, fill: "#64748B" }} />
            <YAxis stroke="#475569" tick={{ fontSize: 10, fill: "#64748B" }}
              tickFormatter={(v) => `฿${(v / 1000).toFixed(0)}k`} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11, color: "#94A3B8" }} />
            {airlines.map((airline, i) => (
              <Line key={airline} type="monotone" dataKey={airline}
                stroke={CNX_PALETTE[i % CNX_PALETTE.length]} strokeWidth={2} dot={false} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    );
  }

  return null;
}

function ChartCard({ title, subtitle, children }: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl p-5"
         style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        <p className="text-xs mt-0.5" style={{ color: "var(--color-muted)" }}>{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-3 py-2 shadow-xl text-xs"
         style={{ background: "#1E293B", border: "1px solid rgba(255,255,255,0.1)" }}>
      <div className="font-semibold mb-1.5" style={{ color: "#94A3B8" }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span style={{ color: "#CBD5E1" }}>{p.name}</span>
          <span className="font-data font-bold ml-auto pl-4" style={{ color: p.color }}>
            ฿{p.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}
