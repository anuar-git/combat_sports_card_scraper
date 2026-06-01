import Link from "next/link";
import { api } from "@/lib/api";
import { FighterCard } from "@/components/FighterCard";
import { SourceStatusBadge } from "@/components/SourceStatusBadge";
import type { MarketOverviewItem } from "@/types";

export const revalidate = 900;

async function getData() {
  const [overviewResult, coverageResult] = await Promise.allSettled([
    api.getMarketOverview(),
    api.getCoverage(),
  ]);
  return {
    overview: overviewResult.status === "fulfilled" ? overviewResult.value : [],
    coverage: coverageResult.status === "fulfilled" ? coverageResult.value : null,
  };
}

function HeroMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
    </div>
  );
}

export default async function HomePage() {
  const { overview, coverage } = await getData();

  const uniqueFighters = new Set(overview.map((o) => o.fighter_id)).size;
  const totalSales = overview.reduce((sum, o) => sum + o.sale_count_30d, 0);
  const topFighter = overview[0]?.fighter_name ?? "—";

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alt Cards Intelligence</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Combat sports trading card market data
          </p>
        </div>
        <div className="flex items-center gap-4">
          {coverage && (
            <SourceStatusBadge status={coverage.pipeline.overall_status} />
          )}
          <a
            href="https://github.com/anuar-git/combat_sports_card_scraper"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="GitHub repository"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
          </a>
          <Link href="/movers" className="text-sm text-blue-600 hover:underline">
            Top movers
          </Link>
          <Link href="/coverage" className="text-sm text-gray-500 hover:underline">
            Pipeline
          </Link>
        </div>
      </header>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <HeroMetric label="Fighters tracked" value={String(uniqueFighters)} />
        <HeroMetric label="Sales (30d)" value={totalSales.toLocaleString()} />
        <HeroMetric label="Most active fighter" value={topFighter} />
      </div>

      <FighterGrid items={overview} />
    </div>
  );
}

function FighterGrid({ items }: { items: MarketOverviewItem[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {items.map((item, i) => (
        <FighterCard
          key={`${item.fighter_id}-${item.grade_label}-${i}`}
          item={item}
        />
      ))}
      {items.length === 0 && (
        <p className="col-span-full text-gray-500 text-center py-16">
          No market data available. Check{" "}
          <Link href="/coverage" className="text-blue-600 hover:underline">
            pipeline status
          </Link>
          .
        </p>
      )}
    </div>
  );
}
