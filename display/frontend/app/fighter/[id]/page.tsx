"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { format } from "date-fns";
import { api } from "@/lib/api";
import { PriceChart } from "@/components/PriceChart";
import { GradeBadge } from "@/components/GradeBadge";
import type { FighterPriceHistory } from "@/types";

export default function FighterDetailPage() {
  const params = useParams<{ id: string }>();
  const fighterId = params.id;

  const [data, setData] = useState<FighterPriceHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const allGrades = data
    ? Array.from(new Set(data.price_history.map((p) => p.grade_label)))
    : [];
  const [visibleGrades, setVisibleGrades] = useState<string[]>([]);

  useEffect(() => {
    api
      .getFighter(fighterId)
      .then((d) => {
        setData(d);
        setVisibleGrades(
          Array.from(new Set(d.price_history.map((p) => p.grade_label)))
        );
      })
      .catch(() => setError("Fighter not found or data unavailable."))
      .finally(() => setLoading(false));
  }, [fighterId]);

  function toggleGrade(grade: string) {
    setVisibleGrades((prev) =>
      prev.includes(grade) ? prev.filter((g) => g !== grade) : [...prev, grade]
    );
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-gray-500">Loading…</div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <p className="text-red-600">{error ?? "Unknown error."}</p>
        <Link href="/" className="text-blue-600 hover:underline text-sm mt-4 inline-block">
          Back to overview
        </Link>
      </div>
    );
  }

  const lastSaleDate =
    data.recent_sales[0]?.sale_date
      ? format(new Date(data.recent_sales[0].sale_date), "MMM d, yyyy")
      : null;

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <Link href="/" className="text-sm text-gray-500 hover:underline mb-4 inline-block">
        ← Back to overview
      </Link>

      {/* Fighter header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">{data.fighter_name}</h1>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span className="text-sm bg-gray-100 text-gray-700 px-2.5 py-0.5 rounded-full font-medium">
            {data.sport}
          </span>
          {data.promotion && (
            <span className="text-sm bg-gray-100 text-gray-600 px-2.5 py-0.5 rounded-full">
              {data.promotion}
            </span>
          )}
          {lastSaleDate && (
            <span className="text-sm text-gray-400">Last sale: {lastSaleDate}</span>
          )}
        </div>
      </div>

      {/* Grade toggles */}
      <div className="flex items-center gap-2 flex-wrap mb-4">
        <span className="text-xs text-gray-500 uppercase tracking-wide">Show grades:</span>
        {allGrades.map((grade) => (
          <button
            key={grade}
            onClick={() => toggleGrade(grade)}
            className={`text-xs px-3 py-1 rounded-full border transition-all ${
              visibleGrades.includes(grade)
                ? "bg-gray-800 text-white border-gray-800"
                : "bg-white text-gray-500 border-gray-300 hover:border-gray-400"
            }`}
          >
            {grade}
          </button>
        ))}
      </div>

      {/* Price chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">
          Price history (90 days) — 30d VWAP
        </h2>
        {data.price_history.length > 0 ? (
          <PriceChart data={data.price_history} visibleGrades={visibleGrades} />
        ) : (
          <p className="text-gray-400 text-sm py-8 text-center">
            No price history available.
          </p>
        )}
      </div>

      {/* Recent sales */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Recent sales</h2>
        {data.recent_sales.length === 0 ? (
          <p className="text-gray-400 text-sm">No recent sales.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="py-2 pr-3 font-medium">Date</th>
                  <th className="py-2 pr-3 font-medium">Price</th>
                  <th className="py-2 pr-3 font-medium">Grade</th>
                  <th className="py-2 pr-3 font-medium">Type</th>
                  <th className="py-2 pr-3 font-medium">Source</th>
                  <th className="py-2 font-medium">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.recent_sales.map((sale, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="py-2 pr-3 text-gray-600 whitespace-nowrap">
                      {format(new Date(sale.sale_date), "MMM d, yyyy")}
                    </td>
                    <td className="py-2 pr-3 font-semibold text-gray-900">
                      ${sale.sale_price_usd.toFixed(2)}
                    </td>
                    <td className="py-2 pr-3">
                      <GradeBadge grade={sale.grade_label} />
                    </td>
                    <td className="py-2 pr-3 text-gray-600 capitalize">
                      {sale.sale_type}
                    </td>
                    <td className="py-2 pr-3">
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-medium uppercase">
                        {sale.source}
                      </span>
                    </td>
                    <td className="py-2">
                      {sale.listing_url ? (
                        <a
                          href={sale.listing_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline text-xs"
                        >
                          View ↗
                        </a>
                      ) : (
                        <span className="text-gray-300 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
