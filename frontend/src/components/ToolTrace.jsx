function formatValue(value) {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  return JSON.stringify(value, null, 2);
}

function formatAction(action) {
  if (!action) {
    return '';
  }

  const tool = action.tool || 'unknown_tool';
  const input = action.input;

  if (!input || Object.keys(input).length === 0) {
    return `${tool}()`;
  }

  const args = Object.values(input)
    .map((value) => JSON.stringify(value))
    .join(', ');

  return `${tool}(${args})`;
}

function TraceBlock({ label, value }) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

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
  const steps = Array.isArray(trace) ? trace : trace?.react_steps || trace?.steps;

  if (!Array.isArray(steps) || steps.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4 rounded-3xl border border-amber-200 bg-amber-50/60 p-4">
      {steps.map((step, index) => (
        <div
          key={`${step?.action?.tool || 'step'}-${index}`}
          className="space-y-4 rounded-2xl border border-amber-200 bg-white p-4 shadow-sm"
        >
          <TraceBlock label="Thought" value={step?.thought} />
          <TraceBlock label="Action" value={formatAction(step?.action)} />
          <TraceBlock label="Observation" value={step?.observation} />
          <TraceBlock label="Reflection" value={step?.reflection} />
          {!step?.action && (
            <p className="text-sm font-semibold text-amber-800">Finish.</p>
          )}
        </div>
      ))}
    </div>
  );
}
