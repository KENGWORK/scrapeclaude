import { google } from "googleapis";
import { NextResponse } from "next/server";

export const revalidate = 3600; // refresh every 1 hour

export interface FlightRecord {
  scrape_date: string;
  departure_date: string;
  return_date: string;
  airline: string;
  price_thb: number;
  dep_time: string;
  arr_time: string;
  duration: string;
  gf_link: string;
}

export async function GET() {
  try {
    const credsJson = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON!);
    const auth = new google.auth.GoogleAuth({
      credentials: credsJson,
      scopes: ["https://www.googleapis.com/auth/spreadsheets.readonly"],
    });

    const sheets = google.sheets({ version: "v4", auth });
    const res = await sheets.spreadsheets.values.get({
      spreadsheetId: process.env.GOOGLE_SHEET_ID!,
      range: "FlightPrices!A:I",
    });

    const rows = res.data.values ?? [];
    if (rows.length < 2) return NextResponse.json([]);

    const headers = rows[0] as string[];
    const data: FlightRecord[] = rows.slice(1).map((row) => {
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

    return NextResponse.json(data);
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Failed to fetch data" }, { status: 500 });
  }
}
