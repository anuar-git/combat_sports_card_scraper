import Link from "next/link";
import type { Mover } from "@/types";
import { GradeBadge } from "./GradeBadge";
import clsx from "clsx";

interface TopMoversTableProps {
  movers: Mover[];
}

export function TopMoversTable({ movers }: TopMoversTableProps) {
  if (movers.length === 0) {
    return (
      <p className="text-gray-500 text-sm py-8 text-center">No movers found.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-500 text-xs uppercase tracking-wide">
            <th className="py-3 pr-4 font-medium">Fighter</th>
            <th className="py-3 pr-4 font-medium">7d change</th>
            <th className="py-3 pr-4 font-medium">Current VWAP</th>
            <th className="py-3 pr-4 font-medium">7d volume</th>
            <th className="py-3 font-medium">30d VWAP</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {movers.map((m, i) => {
            const isUp = m.price_pct_change_7d >= 0;
            return (
              <tr key={`${m.fighter_id}-${i}`} className="hover:bg-gray-50">
                <td className="py-3 pr-4">
                  <Link
                    href={`/fighter/${m.fighter_id}`}
                    className="font-medium text-gray-900 hover:underline"
                  >
                    {m.fighter_name}
                  </Link>
                  <div className="mt-0.5">
                    <GradeBadge grade={m.grade_label} />
                  </div>
                </td>
                <td className="py-3 pr-4">
                  <span
                    className={clsx(
                      "font-semibold",
                      isUp ? "text-green-600" : "text-red-600"
                    )}
                  >
                    {isUp ? "+" : ""}{m.price_pct_change_7d.toFixed(1)}%
                  </span>
                </td>
                <td className="py-3 pr-4 text-gray-900">
                  {m.vwap_7d !== null ? `$${m.vwap_7d.toFixed(2)}` : "—"}
                </td>
                <td className="py-3 pr-4 text-gray-600">
                  {m.sale_count_7d} sale{m.sale_count_7d !== 1 ? "s" : ""}
                </td>
                <td className="py-3 text-gray-600">
                  {m.vwap_30d !== null ? `$${m.vwap_30d.toFixed(2)}` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
