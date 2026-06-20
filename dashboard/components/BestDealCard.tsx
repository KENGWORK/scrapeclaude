"use client";
import { ExternalLink, Plane, Tag } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";
import type { RouteKey } from "./RouteView";

const NRT_AIRLINES = ["ANA", "JAL", "THAI"] as const;
const NRT_COLORS: Record<string, { accent: string; label: string }> = {
  ANA:  { accent: "#3B82F6", label: "All Nippon Airways" },
  JAL:  { accent: "#EF4444", label: "Japan Airlines" },
  THAI: { accent: "#A855F7", label: "Thai Airways" },
};

interface Props {
  data: FlightRecord[];
  routeKey: RouteKey;
}

export default function BestDealCards({ data, routeKey }: Props) {
  if (!data.length) return null;

  if (routeKey === "nrt") return <NrtCards data={data} />;
  if (routeKey === "cnx") return <CnxCards data={data} />;
  return null;
}

function NrtCards({ data }: { data: FlightRecord[] }) {
  const best: Record<string, FlightRecord> = {};
  data.forEach((r) => {
    if (!best[r.airline] || r.price_thb < best[r.airline].price_thb)
      best[r.airline] = r;
  });

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {NRT_AIRLINES.map((airline) => {
        const deal = best[airline];
        const { accent, label } = NRT_COLORS[airline];
        if (!deal) return (
          <EmptyCard key={airline} title={airline} subtitle={label} accent={accent} />
        );
        return <DealCard key={airline} deal={deal} title={airline} subtitle={label} accent={accent} />;
      })}
    </div>
  );
}

function CnxCards({ data }: { data: FlightRecord[] }) {
  const latestScrape = data.reduce((a, b) =>
    a.scrape_date > b.scrape_date ? a : b, data[0])?.scrape_date ?? "";
  const latest = data.filter((r) => r.scrape_date === latestScrape);

  const bestPerDate: Record<string, FlightRecord> = {};
  latest.forEach((r) => {
    const key = r.departure_date + "|" + r.airline;
    if (!bestPerDate[key] || r.price_thb < bestPerDate[key].price_thb)
      bestPerDate[key] = r;
  });

  const top3 = Object.values(bestPerDate)
    .sort((a, b) => a.price_thb - b.price_thb)
    .slice(0, 3);

  const accent = "#10B981";
  const medals = ["ถูกสุด", "ถูกสุด 2", "ถูกสุด 3"];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {top3.map((deal, i) => (
        <DealCard
          key={i}
          deal={deal}
          title={deal.airline}
          subtitle={medals[i]}
          accent={accent}
          badge={i === 0 ? "Best Deal" : undefined}
        />
      ))}
    </div>
  );
}

function DealCard({
  deal, title, subtitle, accent, badge,
}: {
  deal: FlightRecord;
  title: string;
  subtitle: string;
  accent: string;
  badge?: string;
}) {
  return (
    <div className="relative rounded-xl p-5 space-y-3 transition-all duration-200 cursor-pointer hover:scale-[1.01]"
         style={{
           background: `linear-gradient(135deg, ${accent}12 0%, transparent 100%)`,
           border: `1px solid ${accent}30`,
         }}>
      {badge && (
        <span className="absolute top-3 right-3 text-xs font-bold px-2 py-0.5 rounded-full"
              style={{ background: accent + "30", color: accent }}>
          {badge}
        </span>
      )}
      <div className="flex items-center gap-2">
        <Plane size={14} style={{ color: accent }} />
        <div>
          <div className="font-bold text-sm" style={{ color: accent }}>{title}</div>
          <div className="text-xs" style={{ color: "var(--color-muted)" }}>{subtitle}</div>
        </div>
      </div>
      <div className="font-data text-3xl font-bold text-white">
        ฿{deal.price_thb.toLocaleString()}
      </div>
      <div className="space-y-1 text-xs" style={{ color: "var(--color-muted)" }}>
        <div className="flex items-center gap-1.5">
          <Tag size={11} />
          <span>ออก {deal.departure_date} · กลับ {deal.return_date}</span>
        </div>
        {deal.dep_time && (
          <div className="font-data">{deal.dep_time} → {deal.arr_time} ({deal.duration})</div>
        )}
      </div>
      {deal.gf_link && (
        <a href={deal.gf_link} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all duration-150 cursor-pointer"
           style={{ background: accent + "20", color: accent, border: `1px solid ${accent}30` }}>
          <ExternalLink size={11} />
          ดูบน Google Flights
        </a>
      )}
    </div>
  );
}

function EmptyCard({ title, subtitle, accent }: { title: string; subtitle: string; accent: string }) {
  return (
    <div className="rounded-xl p-5 flex flex-col items-center justify-center gap-2 min-h-[160px]"
         style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
      <Plane size={20} style={{ color: accent, opacity: 0.4 }} />
      <div className="text-center">
        <div className="text-sm font-semibold" style={{ color: "var(--color-muted)" }}>{title}</div>
        <div className="text-xs mt-0.5" style={{ color: "var(--color-muted)", opacity: 0.6 }}>{subtitle}</div>
      </div>
      <div className="text-xs" style={{ color: "var(--color-muted)", opacity: 0.5 }}>ยังไม่มีข้อมูล</div>
    </div>
  );
}
