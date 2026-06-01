export interface MarketOverviewItem {
  fighter_id: string;
  fighter_name: string;
  sport: string;
  grade_label: string;
  vwap_7d: number | null;
  vwap_30d: number | null;
  sale_count_30d: number;
  price_pct_change_7d: number | null;
  price_pct_change_30d: number | null;
}

export interface Fighter {
  fighter_id: string;
  fighter_name: string;
  sport: string;
  promotion: string | null;
  vwap_30d: number | null;
}

export interface PricePoint {
  date: string;
  grade_label: string;
  vwap_7d: number | null;
  vwap_30d: number | null;
  sale_count: number;
}

export interface RecentSale {
  listing_title: string;
  sale_price_usd: number;
  sale_date: string;
  sale_type: string;
  source: string;
  listing_url: string | null;
  grade_label: string;
}

export interface FighterPriceHistory {
  fighter_id: string;
  fighter_name: string;
  sport: string;
  promotion: string | null;
  price_history: PricePoint[];
  recent_sales: RecentSale[];
}

export interface Mover {
  fighter_id: string;
  fighter_name: string;
  grade_label: string;
  vwap_7d: number | null;
  vwap_30d: number | null;
  price_pct_change_7d: number;
  sale_count_7d: number;
}

export interface SourceStatus {
  last_successful_scrape: string | null;
  last_run_records_written: number;
  last_run_records_invalid: number;
  status: "healthy" | "degraded" | "stale" | "error";
  lag_hours: number;
}

export interface DbtStatus {
  last_run_at: string | null;
  tests_passed: number;
  tests_failed: number;
  models_run: number;
  status: "healthy" | "degraded" | "stale" | "error";
}

export interface PipelineSummary {
  overall_status: "healthy" | "degraded" | "stale" | "error";
  total_records_in_fct_card_sales: number;
  fighters_with_coverage: number;
}

export interface PipelineStatus {
  updated_at: string;
  sources: Record<string, SourceStatus>;
  dbt: DbtStatus;
  pipeline: PipelineSummary;
}

export type PipelineStatusValue = "healthy" | "degraded" | "stale" | "error";
