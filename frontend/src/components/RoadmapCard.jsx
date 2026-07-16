import {
  AlertTriangle,
  CalendarRange,
  Compass,
  Lightbulb,
  Map,
  Milestone,
  Sparkles,
} from 'lucide-react';

import UiCard from './UiCard';

function formatValue(value) {
  return value || value === 0 ? value : '—';
}

function ListSection({ badge, items, emptyText }) {
  const list = Array.isArray(items) ? items : [];

  return (
    <UiCard badge={badge}>
      {list.length > 0 ? (
        <ul className="space-y-3">
          {list.map((item, index) => (
            <li
              key={`${item}-${index}`}
              className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700"
            >
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">{emptyText}</p>
      )}
    </UiCard>
  );
}

export default function RoadmapCard({ roadmap }) {
  if (!roadmap) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-slate-50 p-10 text-center text-slate-500">
        Run Analyze Repository to load the roadmap prediction.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <Map className="h-3.5 w-3.5" />
            Roadmap Prediction
          </div>
        }
        bodyClassName="space-y-6 pt-6"
      >
        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Milestone className="h-4 w-4" />
            Current Stage
          </div>
          <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-900">
            {formatValue(roadmap.current_stage)}
          </p>
        </div>
      </UiCard>

      <ListSection
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <Compass className="h-3.5 w-3.5" />
            Recent Direction
          </div>
        }
        items={roadmap.recent_direction}
        emptyText="No recent direction available."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <ListSection
          badge={
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <CalendarRange className="h-3.5 w-3.5" />
              Future 3 Months
            </div>
          }
          items={roadmap.future_3_months}
          emptyText="No 3-month forecast available."
        />

        <ListSection
          badge={
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <CalendarRange className="h-3.5 w-3.5" />
              Future 6-12 Months
            </div>
          }
          items={roadmap.future_6_12_months}
          emptyText="No 6-12 month forecast available."
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ListSection
          badge={
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <Lightbulb className="h-3.5 w-3.5" />
              Opportunities
            </div>
          }
          items={roadmap.opportunities}
          emptyText="No opportunities available."
        />

        <ListSection
          badge={
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <AlertTriangle className="h-3.5 w-3.5" />
              Risks
            </div>
          }
          items={roadmap.risks}
          emptyText="No risks available."
        />
      </div>

      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <Sparkles className="h-3.5 w-3.5" />
            Prediction Reasoning
          </div>
        }
      >
        <p className="text-sm leading-7 text-slate-700">
          {formatValue(roadmap.prediction_reasoning)}
        </p>
      </UiCard>
    </div>
  );
}
