import { useEffect, useState } from "react";

export type Load<T> =
  | { state: "loading" }
  | { state: "error"; message: string }
  | { state: "empty" }
  | { state: "ready"; data: T };

export function useApi<T>(path: string): Load<T> {
  const [result, setResult] = useState<Load<T>>({ state: "loading" });
  useEffect(() => {
    let alive = true;
    fetch(path)
      .then((r) => {
        if (!r.ok) throw new Error(`Server answered ${r.status}`);
        return r.json();
      })
      .then((body: { available: boolean; data: T }) => {
        if (alive) setResult(body.available ? { state: "ready", data: body.data } : { state: "empty" });
      })
      .catch((e: Error) => alive && setResult({ state: "error", message: e.message }));
    return () => {
      alive = false;
    };
  }, [path]);
  return result;
}

export interface Candidate {
  symbol: string; name: string; score: number; entry: number; stop: number; target: number;
  reward_risk: number; atr: number; sector: string; setup: string; as_of: string; components: Record<string, number>;
}
export interface RankData {
  as_of: string; risk_on: boolean; universe_size: number; candidates: Candidate[]; portfolio: Candidate[];
}
export interface Position {
  symbol: string; qty: number; entry_price: number; entry_date: string; stop: number; target: number;
  sector: string; last_price: number; market_value: number; unrealized_pnl: number; unrealized_pct: number; bars_held: number;
}
export interface Order { symbol: string; qty: number; stop: number; target: number; sector: string; ref_price: number }
export interface Trade {
  symbol: string; sector: string; qty: number; entry_date: string; entry_price: number; exit_date: string;
  exit_price: number; exit_reason: string; costs: number; net_pnl: number; r_multiple: number; bars_held: number;
}
export interface CurvePoint { date: string; equity: number; benchmark?: number }
export interface PortfolioData {
  started_on: string; last_session: string; capital: number; cash: number; equity: number; total_return: number;
  realized_pnl: number; max_drawdown: number; win_rate: number; positions: Position[]; pending_orders: Order[];
  pending_exits: Record<string, string>; trades: Trade[]; equity_curve: CurvePoint[];
}
export interface BacktestSummary {
  start: string; end: string; initial_capital: number; final_equity: number; post_tax_final_equity: number;
  cagr: number; benchmark_cagr: number; max_drawdown: number; benchmark_max_drawdown: number; sharpe: number;
  trades: number; win_rate: number; avg_win: number; avg_loss: number; profit_factor: number; avg_r: number;
  avg_bars_held: number; total_costs: number; estimated_tax: number; exit_reasons: Record<string, number>;
  yearly: Record<string, { strategy: number; benchmark: number | null }>;
  in_sample?: { cagr: number; benchmark_cagr: number; max_drawdown: number };
  out_of_sample?: { cagr: number; benchmark_cagr: number; max_drawdown: number };
}
export interface BacktestData { summary: BacktestSummary; equity: CurvePoint[]; trades: Trade[] }
export interface MarketData { date: string; markdown: string }
