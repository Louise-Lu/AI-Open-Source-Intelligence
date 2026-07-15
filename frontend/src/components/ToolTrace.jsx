function formatValue(value) {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  return JSON.stringify(value, null, 2);
}

function TraceBlock({ label, value }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <pre className="whitespace-pre-wrap break-words rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-6 text-slate-700">
        {formatValue(value)}
      </pre>
    </div>
  );
}

export default function ToolTrace({ trace }) {
  if (!trace || trace.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4 rounded-3xl border border-amber-200 bg-amber-50/60 p-4">
      {trace.map((item, index) => (
        <div
          key={`${item?.tool || 'tool'}-${index}`}
          className="space-y-4 rounded-2xl border border-amber-200 bg-white p-4 shadow-sm"
        >
          <div className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
            🔧 Tool: {item?.tool || 'Unknown'}
          </div>

          <TraceBlock label="Input" value={item?.input} />
          <TraceBlock label="Output" value={item?.output} />
        </div>
      ))}
    </div>
  );
}
