import type { PipelineStatusValue } from "@/types";

const STATUS_STYLES: Record<
  PipelineStatusValue,
  { dot: string; label: string; text: string }
> = {
  healthy:  { dot: "bg-green-400",  label: "Healthy",  text: "text-green-700" },
  degraded: { dot: "bg-yellow-400", label: "Degraded", text: "text-yellow-700" },
  stale:    { dot: "bg-orange-400", label: "Stale",    text: "text-orange-700" },
  error:    { dot: "bg-red-400",    label: "Error",    text: "text-red-700" },
};

export function SourceStatusBadge({ status }: { status: PipelineStatusValue }) {
  const { dot, label, text } = STATUS_STYLES[status];
  return (
    <span className={`flex items-center gap-1.5 text-sm font-medium ${text}`}>
      <span className={`w-2 h-2 rounded-full ${dot} animate-pulse`} />
      {label}
    </span>
  );
}
