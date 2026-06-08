"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { FlightRecord } from "@/app/api/flights/route";

const AIRLINE_COLORS: Record<string, string> = {
  ANA:  "#60a5fa",
  JAL:  "#f87171",
  THAI: "#fbbf24",
};

interface Props { data: FlightRecord[] }

export default function PriceByDepartureChart({ data }: Props) {
  // Get latest scrape date
  const latestScrape = data.reduce((a, b) =>
    a.scrape_date > b.scrape_date ? a : b, data[0])?.scrape_date ?? "";

  const latest = data.filter((r) => r.scrape_date === latestScrape);

  // Build chart data keyed by departure_date
  const byDate: Record<string, Record<string, number>> = {};
  latest.forEach((r) => {
    if (!byDate[r.departure_date]) byDate[r.departure_date] = {};
    byDate[r.departure_date][r.airline] = r.price_thb;
  });

  const chartData = Object.entries(byDate)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, prices]) => ({
      date: date.slice(5), // MM-DD
      ...prices,
    }));

  return (
    <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
      <h2 className="text-lg font-bold mb-1 text-orange-300">📅 ราคาตามวันออกเดินทาง</h2>
      <p className="text-xs text-white/50 mb-4">ข้อมูล ณ {latestScrape}</p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 11 }} />
          <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }}
            tickFormatter={(v) => `฿${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "none", borderRadius: 8 }}
            formatter={(v: number) => [`฿${v.toLocaleString()}`, ""]}
          />
          <Legend />
          {Object.keys(AIRLINE_COLORS).map((airline) => (
            <Line
              key={airline}
              type="monotone"
              dataKey={airline}
              stroke={AIRLINE_COLORS[airline]}
              strokeWidth={2}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
