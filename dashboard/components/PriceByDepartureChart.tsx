"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { FlightRecord } from "@/app/api/flights/route";
import type { RouteKey } from "./RouteView";

const NRT_SERIES = [
  { key: "ANA",  color: "#1D4ED8" },
  { key: "JAL",  color: "#DC2626" },
  { key: "THAI", color: "#9333EA" },
];
const CNX_PALETTE = ["#15803D", "#D97706", "#1D4ED8", "#DC2626", "#9333EA"];

interface Props { data: FlightRecord[]; routeKey: RouteKey; accentColor: string; }

export default function PriceByDepartureChart({ data, routeKey, accentColor }: Props) {
  const latestScrape = data.reduce((a, b) => a.scrape_date > b.scrape_date ? a : b, data[0])?.scrape_date ?? "";
  const latest = data.filter((r) => r.scrape_date === latestScrape);

  let series: { key: string; color: string }[] = [];
  let chartData: Record<string, string | number>[] = [];

  if (routeKey === "nrt") {
    series = NRT_SERIES;
    const byDate: Record<string, Record<string, number>> = {};
    latest.forEach((r) => {
      if (!byDate[r.departure_date]) byDate[r.departure_date] = {};
      byDate[r.departure_date][r.airline] = r.price_thb;
    });
    chartData = Object.entries(byDate).sort(([a], [b]) => a.localeCompare(b))
      .map(([date, prices]) => ({ date: date.slice(5), ...prices }));
  } else if (routeKey === "cnx") {
    const airlines = Array.from(new Set(latest.map((r) => r.airline)));
    series = airlines.map((a, i) => ({ key: a, color: CNX_PALETTE[i % CNX_PALETTE.length] }));
    const byDate: Record<string, Record<string, number>> = {};
    latest.forEach((r) => {
      if (!byDate[r.departure_date]) byDate[r.departure_date] = {};
      byDate[r.departure_date][r.airline] = r.price_thb;
    });
    chartData = Object.entries(byDate).sort(([a], [b]) => a.localeCompare(b))
      .map(([date, prices]) => ({ date: date.slice(5), ...prices }));
  } else {
    return null;
  }

  return (
    <ChartCard title="ราคาตามวันออกเดินทาง" subtitle={`ข้อมูล ณ ${latestScrape}`}>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
          <XAxis dataKey="date" stroke="#D1D5DB" tick={{ fontSize: 10, fill: "#9CA3AF" }} />
          <YAxis stroke="#D1D5DB" tick={{ fontSize: 10, fill: "#9CA3AF" }}
            tickFormatter={(v) => `฿${(v / 1000).toFixed(0)}k`} />
          <Tooltip content={<CustomTooltip series={series} />} />
          <Legend wrapperStyle={{ fontSize: 12, color: "#6B7280" }} />
          {series.map(({ key, color }) => (
            <Line key={key} type="monotone" dataKey={key} stroke={color}
              strokeWidth={2.5} dot={false} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl p-5"
         style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)", boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }}>
      <div className="mb-4">
        <h2 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>{title}</h2>
        <p className="text-xs mt-0.5" style={{ color: "var(--color-muted)" }}>{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function CustomTooltip({ active, payload, label, series }: {
  active?: boolean;
  payload?: { name: string; value: number }[];
  label?: string;
  series: { key: string; color: string }[];
}) {
  if (!active || !payload?.length) return null;
  const colorMap = Object.fromEntries(series.map((s) => [s.key, s.color]));
  return (
    <div className="rounded-xl px-3 py-2.5 shadow-lg text-xs"
         style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)" }}>
      <div className="font-semibold mb-1.5" style={{ color: "var(--color-muted)" }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2 py-0.5">
          <span className="w-2 h-2 rounded-full" style={{ background: colorMap[p.name] ?? "#888" }} />
          <span style={{ color: "var(--color-text)" }}>{p.name}</span>
          <span className="font-data font-bold ml-auto pl-4" style={{ color: colorMap[p.name] ?? "#888" }}>
            ฿{p.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}
