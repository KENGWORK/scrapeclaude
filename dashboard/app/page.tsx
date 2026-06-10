import { google } from "googleapis";
import type { FlightRecord } from "./api/flights/route";
import RouteView from "@/components/RouteView";

export const revalidate = 3600;

async function fetchSheet(range: string): Promise<FlightRecord[]> {
  try {
    const credsJson = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON!);
    const auth = new google.auth.GoogleAuth({
      credentials: credsJson,
      scopes: ["https://www.googleapis.com/auth/spreadsheets.readonly"],
    });
    const sheets = google.sheets({ version: "v4", auth });
    const res = await sheets.spreadsheets.values.get({
      spreadsheetId: process.env.GOOGLE_SHEET_ID!,
      range,
    });
    const rows = res.data.values ?? [];
    if (rows.length < 2) return [];
    const headers = rows[0] as string[];
    return rows.slice(1).map((row) => {
      const obj: Record<string, string> = {};
      headers.forEach((h, i) => (obj[h] = row[i] ?? ""));
      return {
        scrape_date:    obj.scrape_date,
        departure_date: obj.departure_date,
        return_date:    obj.return_date,
        airline:        obj.airline,
        price_thb:      Number(obj.price_thb) || 0,
        dep_time:       obj.dep_time,
        arr_time:       obj.arr_time,
        duration:       obj.duration,
        gf_link:        obj.gf_link,
      };
    });
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const [nrtData, cnxData] = await Promise.all([
    fetchSheet("FlightPrices!A:I"),
    fetchSheet("BKKCNXPrices!A:I"),
  ]);

  return (
    <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <RouteView nrtData={nrtData} cnxData={cnxData} />
    </main>
  );
}
