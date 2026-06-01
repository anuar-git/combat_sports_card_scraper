import Link from "next/link";
import { api } from "@/lib/api";
import { SourceStatusBadge } from "@/components/SourceStatusBadge";
import { format, formatDistanceToNow } from "date-fns";
import type { PipelineStatus } from "@/types";

export const revalidate = 300;

async function getCoverage(): Promise<PipelineStatus | null> {
  try {
    return await api.getCoverage();
  } catch {
    return null;
  }
}

export default async function CoveragePage() {
  const data = await getCoverage();

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <Link href="/" className="text-sm text-gray-500 hover:underline mb-4 inline-block">
        ← Back to overview
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-1">Pipeline status</h1>
      <p className="text-sm text-gray-500 mb-6">
        Data is scraped from eBay and PWCC every 6 hours. It is cleaned and
        standardised using Apache Spark and dbt. This page shows the current
        health of that pipeline.
      </p>

      {!data ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
          Pipeline metrics unavailable.
        </div>
      ) : (
        <>
          {/* Overall banner */}
          <OverallBanner status={data} />

          {/* Per-source table */}
          <section className="mb-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              Sources
            </h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide text-left">
                    <th className="py-3 px-4 font-medium">Source</th>
                    <th className="py-3 px-4 font-medium">Status</th>
                    <th className="py-3 px-4 font-medium">Last scrape</th>
                    <th className="py-3 px-4 font-medium">Records</th>
                    <th className="py-3 px-4 font-medium">Invalid</th>
                    <th className="py-3 px-4 font-medium">Lag</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {Object.entries(data.sources).map(([name, src]) => (
                    <tr key={name} className="hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium text-gray-900 uppercase">
                        {name}
                      </td>
                      <td className="py-3 px-4">
                        <SourceStatusBadge status={src.status} />
                      </td>
                      <td className="py-3 px-4 text-gray-600">
                        {src.last_successful_scrape
                          ? formatDistanceToNow(new Date(src.last_successful_scrape), {
                              addSuffix: true,
                            })
                          : "—"}
                      </td>
                      <td className="py-3 px-4 text-gray-600">
                        {src.last_run_records_written.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-gray-600">
                        {src.last_run_records_invalid}
                      </td>
                      <td className="py-3 px-4 text-gray-600">
                        {src.lag_hours < 1
                          ? `${Math.round(src.lag_hours * 60)}m`
                          : `${src.lag_hours.toFixed(1)}h`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* dbt tests */}
          <section className="mb-6">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              dbt test results
            </h2>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-6 mb-3">
                <div>
                  <div className="text-xs text-gray-500 mb-0.5">Passed</div>
                  <div className="text-2xl font-bold text-green-600">
                    {data.dbt.tests_passed}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-0.5">Failed</div>
                  <div
                    className={`text-2xl font-bold ${
                      data.dbt.tests_failed > 0 ? "text-red-600" : "text-gray-300"
                    }`}
                  >
                    {data.dbt.tests_failed}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-0.5">Models run</div>
                  <div className="text-2xl font-bold text-gray-700">
                    {data.dbt.models_run}
                  </div>
                </div>
              </div>
              {data.dbt.last_run_at && (
                <p className="text-xs text-gray-400">
                  Last run:{" "}
                  {format(new Date(data.dbt.last_run_at), "MMM d, yyyy HH:mm 'UTC'")}
                </p>
              )}
            </div>
          </section>

          {/* Pipeline summary */}
          <section>
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
              Dataset summary
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="text-xs text-gray-500 mb-1">Total sales indexed</div>
                <div className="text-xl font-bold text-gray-900">
                  {data.pipeline.total_records_in_fct_card_sales.toLocaleString()}
                </div>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <div className="text-xs text-gray-500 mb-1">Fighters with coverage</div>
                <div className="text-xl font-bold text-gray-900">
                  {data.pipeline.fighters_with_coverage}
                </div>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function OverallBanner({ status }: { status: PipelineStatus }) {
  const updated = formatDistanceToNow(new Date(status.updated_at), {
    addSuffix: true,
  });

  const BANNER_STYLES: Record<string, string> = {
    healthy:  "bg-green-50 border-green-200 text-green-800",
    degraded: "bg-yellow-50 border-yellow-200 text-yellow-800",
    stale:    "bg-orange-50 border-orange-200 text-orange-800",
    error:    "bg-red-50 border-red-200 text-red-800",
  };

  const styles =
    BANNER_STYLES[status.pipeline.overall_status] ??
    "bg-gray-50 border-gray-200 text-gray-700";

  return (
    <div className={`rounded-xl border p-4 mb-6 ${styles}`}>
      <div className="flex items-center justify-between">
        <span className="font-semibold capitalize">
          {status.pipeline.overall_status}
        </span>
        <span className="text-sm opacity-70">Updated {updated}</span>
      </div>
    </div>
  );
}
