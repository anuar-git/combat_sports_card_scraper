import type {
  FighterPriceHistory,
  Fighter,
  MarketOverviewItem,
  Mover,
  PipelineStatus,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 900 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  getMarketOverview: () =>
    apiFetch<MarketOverviewItem[]>("/market/overview"),

  searchFighters: (q: string) =>
    apiFetch<Fighter[]>(`/market/search?q=${encodeURIComponent(q)}`),

  getFighter: (id: string) =>
    apiFetch<FighterPriceHistory>(`/fighters/${encodeURIComponent(id)}`),

  listFighters: () =>
    apiFetch<Fighter[]>("/fighters"),

  getMovers: (direction: "up" | "down" | "both" = "both", limit = 10) =>
    apiFetch<Mover[]>(`/movers?direction=${direction}&limit=${limit}`),

  getCoverage: () =>
    apiFetch<PipelineStatus>("/coverage"),
};
