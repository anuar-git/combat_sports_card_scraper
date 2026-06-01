"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { TopMoversTable } from "@/components/TopMoversTable";
import type { Mover } from "@/types";

type Direction = "up" | "down" | "both";
type LimitOption = 5 | 10 | 20;

export default function MoversPage() {
  const [direction, setDirection] = useState<Direction>("both");
  const [limit, setLimit] = useState<LimitOption>(10);
  const [movers, setMovers] = useState<Mover[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .getMovers(direction, limit)
      .then(setMovers)
      .catch(() => setMovers([]))
      .finally(() => setLoading(false));
  }, [direction, limit]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <Link href="/" className="text-sm text-gray-500 hover:underline mb-4 inline-block">
        ← Back to overview
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-1">Top movers</h1>
      <p className="text-sm text-gray-500 mb-6">
        Minimum 2 sales in 7 days required to appear.
      </p>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <div className="flex rounded-lg border border-gray-200 overflow-hidden">
          {(["both", "up", "down"] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDirection(d)}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                direction === d
                  ? "bg-gray-800 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              {d === "both" ? "All movers" : d === "up" ? "Gainers" : "Losers"}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Show:</span>
          {([5, 10, 20] as LimitOption[]).map((n) => (
            <button
              key={n}
              onClick={() => setLimit(n)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                limit === n
                  ? "bg-gray-800 text-white border-gray-800"
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        {loading ? (
          <p className="text-gray-400 text-sm py-8 text-center">Loading…</p>
        ) : (
          <TopMoversTable movers={movers} />
        )}
      </div>
    </div>
  );
}
