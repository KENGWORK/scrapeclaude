"use client";
import { ExternalLink, Plane, Tag } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";
import type { RouteKey } from "./RouteView";

const NRT_AIRLINES = ["ANA", "JAL", "THAI"] as const;
const NRT_META: Record<string, { color: string; label: string }> = {
  ANA:  { color: "#1D4ED8", label: "All Nippon Airways" },
  JAL:  { color: "#DC2626", label: "Japan Airlines" },
  THAI: { color: "#9333EA", label: "Thai Airways" },
};

interface Props {
  data: FlightRecord[];
  routeKey: RouteKey;
  accentColor: string;
  accentBg: string;
  accentBorder: string;
}

export default function BestDealCards({ data, routeKey, accentColor, accentBg, accentBorder }: Props) {
  if (!data.length) return null;
  if (routeKey === "nrt") return <NrtCards data={data} />;
  if (routeKey === "cnx") return <CnxCards data={data} accentColor={accentColor} accentBg={accentBg} accentBorder={accentBorder} />;
  return null;
}

function NrtCards({ data }: { data: FlightRecord[] }) {
  const best: Record<string, FlightRecord> = {};
  data.forEach((r) => {
    if (!best[r.airline] || r.price_thb < best[r.airline].price_thb) best[r.airline] = r;
  });
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {NRT_AIRLINES.map((a) => {
        const { color, label } = NRT_META[a];
        return best[a]
          ? <DealCard key={a} deal={best[a]} title={a} subtitle={label} color={color} bg={color + "0F"} border={color + "30"} />
          : <EmptyCard key={a} title={a} subtitle={label} color={color} />;
      })}
    </div>
  );
}

function CnxCards({ data, accentColor, accentBg, accentBorder }: {
  data: FlightRecord[]; accentColor: string; accentBg: string; accentBorder: string;
}) {
  const latestScrape = data.reduce((a, b) => a.scrape_date > b.scrape_date ? a : b, data[0])?.scrape_date ?? "";
  const latest = data.filter((r) => r.scrape_date === latestScrape);
  const bestPerCombo: Record<string, FlightRecord> = {};
  latest.forEach((r) => {
    const k = r.departure_date + "|" + r.airline;
    if (!bestPerCombo[k] || r.price_thb < bestPerCombo[k].price_thb) bestPerCombo[k] = r;
  });
  const top3 = Object.values(bestPerCombo).sort((a, b) => a.price_thb - b.price_thb).slice(0, 3);
  const badges = ["ถูกสุด", "อันดับ 2", "อันดับ 3"];
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {top3.map((deal, i) => (
        <DealCard key={i} deal={deal} title={deal.airline} subtitle={badges[i]}
          color={accentColor} bg={accentBg} border={accentBorder}
          badge={i === 0 ? "Best Deal" : undefined} />
      ))}
    </div>
  );
}

function DealCard({ deal, title, subtitle, color, bg, border, badge }: {
  deal: FlightRecord; title: string; subtitle: string;
  color: string; bg: string; border: string; badge?: string;
}) {
  return (
    <div className="relative rounded-2xl p-5 space-y-3 transition-transform duration-200 hover:scale-[1.01] cursor-pointer"
         style={{ background: bg, border: `1.5px solid ${border}`, boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
      {badge && (
        <span className="absolute top-3 right-3 text-xs font-bold px-2.5 py-0.5 rounded-full"
              style={{ background: color + "20", color }}>
          {badge}
        </span>
      )}
      <div className="flex items-center gap-2">
        <Plane size={15} style={{ color }} />
        <div>
          <div className="font-bold" style={{ color }}>{title}</div>
          <div className="text-xs" style={{ color: "var(--color-muted)" }}>{subtitle}</div>
        </div>
      </div>
      <div className="font-data text-3xl font-bold" style={{ color: "var(--color-text)" }}>
        ฿{deal.price_thb.toLocaleString()}
      </div>
      <div className="space-y-1 text-sm" style={{ color: "var(--color-muted)" }}>
        <div className="flex items-center gap-1.5">
          <Tag size={11} />
          ออก {deal.departure_date} · กลับ {deal.return_date}
        </div>
        {deal.dep_time && (
          <div className="font-data text-xs">
            {deal.dep_time} → {deal.arr_time} ({deal.duration})
          </div>
        )}
      </div>
      {deal.gf_link && (
        <a href={deal.gf_link} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded-xl transition-all duration-150 cursor-pointer"
           style={{ background: color + "15", color, border: `1px solid ${color}25` }}>
          <ExternalLink size={12} />
          ดูบน Google Flights
        </a>
      )}
    </div>
  );
}

function EmptyCard({ title, subtitle, color }: { title: string; subtitle: string; color: string }) {
  return (
    <div className="rounded-2xl p-5 flex flex-col items-center justify-center gap-2 min-h-[160px]"
         style={{ background: "#FFFFFF", border: "1px solid var(--color-border-md)" }}>
      <Plane size={20} style={{ color, opacity: 0.3 }} />
      <div className="font-semibold text-sm" style={{ color: "var(--color-muted)" }}>{title}</div>
      <div className="text-xs" style={{ color: "var(--color-muted)", opacity: 0.6 }}>{subtitle}</div>
      <div className="text-xs" style={{ color: "var(--color-muted)", opacity: 0.45 }}>ยังไม่มีข้อมูล</div>
    </div>
  );
}
