import Link from "next/link";
import type { MarketOverviewItem } from "@/types";
import { GradeBadge } from "./GradeBadge";
import clsx from "clsx";

interface FighterCardProps {
  item: MarketOverviewItem;
}

function PctChange({ value }: { value: number | null }) {
  if (value === null) return <span className="text-gray-400 text-sm">—</span>;
  const isUp = value >= 0;
  return (
    <span
      className={clsx(
        "text-sm font-semibold flex items-center gap-0.5",
        isUp ? "text-green-600" : "text-red-600"
      )}
    >
      {isUp ? "▲" : "▼"} {Math.abs(value).toFixed(1)}%
    </span>
  );
}

export function FighterCard({ item }: FighterCardProps) {
  return (
    <Link
      href={`/fighter/${item.fighter_id}`}
      className="block bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md hover:border-gray-300 transition-all"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <span className="font-semibold text-gray-900 text-sm leading-tight">
          {item.fighter_name}
        </span>
        <span className="text-xs text-gray-400 shrink-0">{item.sport}</span>
      </div>
      <div className="mb-2">
        <GradeBadge grade={item.grade_label} />
      </div>
      <div className="flex items-end justify-between">
        <div>
          <div className="text-xs text-gray-500">30d VWAP</div>
          <div className="text-lg font-bold text-gray-900">
            {item.vwap_30d !== null ? `$${item.vwap_30d.toFixed(2)}` : "—"}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500 mb-0.5">7d change</div>
          <PctChange value={item.price_pct_change_7d} />
        </div>
      </div>
      <div className="mt-2 text-xs text-gray-400">
        {item.sale_count_30d} sale{item.sale_count_30d !== 1 ? "s" : ""} / 30d
      </div>
    </Link>
  );
}
