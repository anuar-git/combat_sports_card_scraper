const GRADE_STYLES: Record<string, string> = {
  "PSA 10":  "bg-green-100 text-green-800",
  "PSA 9":   "bg-green-50 text-green-700",
  "BGS 9.5": "bg-blue-100 text-blue-800",
  "BGS 9":   "bg-blue-50 text-blue-700",
  "SGC 10":  "bg-purple-100 text-purple-800",
  "Raw":     "bg-gray-100 text-gray-700",
};

export function GradeBadge({ grade }: { grade: string }) {
  const styles = GRADE_STYLES[grade] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${styles}`}>
      {grade}
    </span>
  );
}
