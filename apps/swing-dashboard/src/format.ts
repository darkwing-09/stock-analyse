const inrFmt = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const inrFmt2 = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
const numFmt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

export const inr = (v: number | null | undefined, decimals = false) =>
  v == null || Number.isNaN(v) ? "—" : (decimals ? inrFmt2 : inrFmt).format(v);
export const num = (v: number | null | undefined) => (v == null ? "—" : numFmt.format(v));
export const pct = (v: number | null | undefined, signed = true) =>
  v == null || Number.isNaN(v) ? "—" : `${signed && v > 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
export const compactInr = (v: number) => (Math.abs(v) >= 1e7 ? `₹${(v / 1e7).toFixed(1)}Cr` : `₹${(v / 1e5).toFixed(1)}L`);
export const day = (iso: string | null | undefined) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—";
export const shortDay = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
export const ticker = (symbol: string) => symbol.replace(/\.(NS|BO)$/, "");
export const sectorName = (code: string) =>
  ({
    NIFTYIT: "IT", BANKNIFTY: "Banks", FINNIFTY: "Financials", NIFTYAUTO: "Auto", NIFTYPHARMA: "Pharma",
    NIFTYFMCG: "FMCG", NIFTYMETAL: "Metals", NIFTYENERGY: "Energy", NIFTYREALTY: "Realty",
    NIFTYPSUBANK: "PSU Banks", NIFTYINFRA: "Infra", NIFTYCONSUMPTION: "Consumption", OTHER: "Other",
  })[code] ?? code;
