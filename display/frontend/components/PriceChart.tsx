"use client";

import { format } from "date-fns";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PricePoint } from "@/types";

const GRADE_COLORS: Record<string, string> = {
  "PSA 10":  "#22c55e",
  "PSA 9":   "#86efac",
  "BGS 9.5": "#3b82f6",
  "BGS 9":   "#93c5fd",
  "SGC 10":  "#a855f7",
  "Raw":     "#94a3b8",
};

interface PriceChartProps {
  data: PricePoint[];
  visibleGrades: string[];
}

function pivotByDate(data: PricePoint[]): Record<string, Record<string, number | null>> {
  const byDate: Record<string, Record<string, number | null>> = {};
  for (const pt of data) {
    if (!byDate[pt.date]) byDate[pt.date] = { date: pt.date as unknown as number };
    byDate[pt.date][pt.grade_label] = pt.vwap_30d;
  }
  return byDate;
}

export function PriceChart({ data, visibleGrades }: PriceChartProps) {
  const pivoted = Object.values(pivotByDate(data)).sort((a, b) =>
    String(a.date) < String(b.date) ? -1 : 1
  );

  const grades = Array.from(new Set(data.map((d) => d.grade_label))).filter((g) =>
    visibleGrades.includes(g)
  );

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={pivoted}>
        <XAxis
          dataKey="date"
          tickFormatter={(d: string) => {
            try { return format(new Date(d), "MMM d"); } catch { return d; }
          }}
          tick={{ fontSize: 12 }}
        />
        <YAxis
          tickFormatter={(v: number) => `$${v.toLocaleString()}`}
          tick={{ fontSize: 12 }}
          width={70}
        />
        <Tooltip
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(v: any) => [`$${Number(v).toFixed(2)}`, ""] as any}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          labelFormatter={(l: any) => {
            const s = String(l);
            try { return format(new Date(s), "MMM d, yyyy"); } catch { return s; }
          }}
        />
        <Legend />
        {grades.map((grade) => (
          <Line
            key={grade}
            type="monotone"
            dataKey={grade}
            stroke={GRADE_COLORS[grade] ?? "#6b7280"}
            dot={false}
            strokeWidth={2}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
