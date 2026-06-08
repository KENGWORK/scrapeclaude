"use client";
import { useState } from "react";
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

export default function PriceHistoryChart({ data }: Props) {
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

  return (
    <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
        <h2 className="text-lg font-bold text-orange-300 flex-1">📈 แนวโน้มราคาตามเวลา</h2>
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="bg-white/10 border border-white/30 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-orange-400"
        >
          {departureDates.map((d) => (
            <option key={d} value={d} className="bg-slate-800">{d}</option>
          ))}
        </select>
      </div>
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
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
