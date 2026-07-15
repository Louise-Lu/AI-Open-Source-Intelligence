export default function ScoreCard({ label, value }) {
  const safeValue = Math.max(0, Math.min(10, Number(value ?? 0) || 0));
  const percent = safeValue * 10;

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="mb-3 flex items-center justify-between gap-4">
        <h4 className="text-sm font-semibold text-slate-700">{label}</h4>
        <span className="text-sm font-medium text-slate-500">{safeValue}/10</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-slate-900 transition-all duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
