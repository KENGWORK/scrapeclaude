"use client";
import { useEffect } from "react";
import { X, ExternalLink, Plane, Calendar, Clock, Timer } from "lucide-react";
import type { FlightRecord } from "@/app/api/flights/route";

interface Props {
  record: FlightRecord | null;
  accentColor: string;
  accentBg: string;
  accentBorder: string;
  onClose: () => void;
}

const AIRLINE_COLOR: Record<string, string> = {
  ANA:  "#1D4ED8",
  JAL:  "#DC2626",
  THAI: "#9333EA",
};

export default function FlightModal({ record, accentColor, accentBg, accentBorder, onClose }: Props) {
  useEffect(() => {
    if (!record) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [record, onClose]);

  if (!record) return null;

  const color = AIRLINE_COLOR[record.airline] ?? accentColor;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.35)", backdropFilter: "blur(4px)" }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md rounded-3xl shadow-2xl"
        style={{ background: "#FFFFFF", border: "1.5px solid var(--color-border-md)" }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Header bar */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4"
             style={{ borderBottom: "1px solid var(--color-border)" }}>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center"
                 style={{ background: color + "15", border: `1px solid ${color}30` }}>
              <Plane size={15} style={{ color }} />
            </div>
            <div>
              <div className="font-bold text-sm" style={{ color }}>
                {record.airline}
              </div>
              <div className="text-xs" style={{ color: "var(--color-muted)" }}>
                รายละเอียดเที่ยวบิน
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl flex items-center justify-center transition-colors cursor-pointer hover:bg-gray-100"
            aria-label="ปิด"
          >
            <X size={16} style={{ color: "var(--color-muted)" }} />
          </button>
        </div>

        {/* Price hero */}
        <div className="px-6 py-5" style={{ background: accentBg, borderBottom: "1px solid var(--color-border)" }}>
          <div className="text-xs font-semibold uppercase tracking-widest mb-1" style={{ color, opacity: 0.7 }}>
            ราคารวม (THB / ท่าน)
          </div>
          <div className="font-data text-5xl font-bold" style={{ color: "var(--color-text)" }}>
            ฿{record.price_thb.toLocaleString()}
          </div>
        </div>

        {/* Details */}
        <div className="px-6 py-5 space-y-4">

          {/* Date row */}
          <DetailRow icon={<Calendar size={15} style={{ color }} />} label="วันเดินทาง">
            <span className="font-data text-sm font-semibold">{record.departure_date}</span>
            <span className="mx-2 text-xs" style={{ color: "var(--color-muted)" }}>→</span>
            <span className="font-data text-sm font-semibold">{record.return_date}</span>
          </DetailRow>

          {/* Time row */}
          {record.dep_time && (
            <DetailRow icon={<Clock size={15} style={{ color }} />} label="เวลาออก–ถึง">
              <span className="font-data text-sm font-semibold">
                {record.dep_time} → {record.arr_time}
              </span>
            </DetailRow>
          )}

          {/* Duration */}
          {record.duration && (
            <DetailRow icon={<Timer size={15} style={{ color }} />} label="ระยะเวลาบิน">
              <span className="font-data text-sm font-semibold">{record.duration}</span>
            </DetailRow>
          )}

          {/* Scrape date note */}
          <div className="pt-1 text-xs" style={{ color: "var(--color-muted)" }}>
            ข้อมูล ณ {record.scrape_date.slice(0, 10)}
          </div>
        </div>

        {/* CTA */}
        <div className="px-6 pb-6 flex gap-3">
          {record.gf_link ? (
            <a
              href={record.gf_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl font-bold text-sm text-white transition-opacity hover:opacity-85 cursor-pointer"
              style={{ background: color }}
            >
              <ExternalLink size={15} />
              ดูบน Google Flights
            </a>
          ) : (
            <div className="flex-1 py-3 rounded-2xl text-sm text-center font-medium"
                 style={{ background: "var(--color-surface-2)", color: "var(--color-muted)" }}>
              ไม่มีลิงก์
            </div>
          )}
          <button
            onClick={onClose}
            className="px-5 py-3 rounded-2xl text-sm font-semibold transition-colors cursor-pointer hover:bg-gray-100"
            style={{ border: "1.5px solid var(--color-border-md)", color: "var(--color-muted)" }}
          >
            ปิด
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ icon, label, children }: {
  icon: React.ReactNode; label: string; children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex-shrink-0">{icon}</div>
      <div>
        <div className="text-xs mb-0.5" style={{ color: "var(--color-muted)" }}>{label}</div>
        <div className="flex items-center flex-wrap">{children}</div>
      </div>
    </div>
  );
}
