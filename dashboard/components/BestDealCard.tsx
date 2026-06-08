"use client";
import { ExternalLink, Plane } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";

const AIRLINE_COLORS: Record<string, string> = {
  ANA:  "from-blue-500/30 to-blue-900/30 border-blue-400/40",
  JAL:  "from-red-500/30 to-red-900/30 border-red-400/40",
  THAI: "from-amber-500/30 to-amber-900/30 border-amber-400/40",
};
const AIRLINE_TEXT: Record<string, string> = {
  ANA:  "text-blue-300",
  JAL:  "text-red-300",
  THAI: "text-amber-300",
};

interface Props { data: FlightRecord[] }

export default function BestDealCards({ data }: Props) {
  if (!data.length) return null;

  const best: Record<string, FlightRecord> = {};
  data.forEach((r) => {
    if (!best[r.airline] || r.price_thb < best[r.airline].price_thb) {
      best[r.airline] = r;
    }
  });

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {["ANA", "JAL", "THAI"].map((airline) => {
        const deal = best[airline];
        if (!deal) return (
          <div key={airline}
            className="bg-white/5 rounded-2xl p-5 border border-white/10 flex items-center justify-center text-white/30">
            ยังไม่มีข้อมูล {airline}
          </div>
        );

        return (
          <div key={airline}
            className={`bg-gradient-to-br ${AIRLINE_COLORS[airline]} rounded-2xl p-5 border backdrop-blur-md`}>
            <div className="flex items-center gap-2 mb-3">
              <Plane size={18} className={AIRLINE_TEXT[airline]} />
              <span className={`font-bold text-lg ${AIRLINE_TEXT[airline]}`}>{airline}</span>
            </div>
            <div className="text-3xl font-black text-white mb-1">
              ฿{deal.price_thb.toLocaleString()}
            </div>
            <div className="text-sm text-white/70 mb-1">
              🗓️ ออก {deal.departure_date}
            </div>
            <div className="text-sm text-white/70 mb-1">
              🔄 กลับ {deal.return_date}
            </div>
            {deal.dep_time && (
              <div className="text-sm text-white/70 mb-1">
                🕐 {deal.dep_time} → {deal.arr_time}
              </div>
            )}
            {deal.duration && (
              <div className="text-sm text-white/70 mb-3">
                ⏱️ {deal.duration}
              </div>
            )}
            {deal.gf_link && (
              <a
                href={deal.gf_link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 bg-orange-500 hover:bg-orange-400 transition-colors text-white text-sm font-semibold px-4 py-2 rounded-xl"
              >
                <ExternalLink size={14} />
                ดูบน Google Flights
              </a>
            )}
          </div>
        );
      })}
    </div>
  );
}
