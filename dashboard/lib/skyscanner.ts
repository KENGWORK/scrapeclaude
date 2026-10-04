// Skyscanner has no scrapeable/free price API (bot-gated), so we link out to
// the prefilled search page for the same route + dates instead.
export function skyscannerUrl(origin: string, dest: string, dep: string, ret: string): string | null {
  const yymmdd = (iso: string) => iso.replace(/-/g, "").slice(2);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dep) || !/^\d{4}-\d{2}-\d{2}$/.test(ret)) return null;
  return (
    `https://www.skyscanner.co.th/transport/flights/${origin.toLowerCase()}/${dest.toLowerCase()}/` +
    `${yymmdd(dep)}/${yymmdd(ret)}/?adultsv2=1&cabinclass=economy&rtn=1&currency=THB&market=TH&locale=th-TH`
  );
}
