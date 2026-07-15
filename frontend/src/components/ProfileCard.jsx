import { BadgeCheck, FileText, GitFork, Globe, Scale, Star, Tag, Target } from 'lucide-react';

import UiCard from './UiCard';
import ScoreCard from './ScoreCard';

function formatValue(value) {
  return value || value === 0 ? value : '—';
}

export default function ProfileCard({ profile }) {
  if (!profile) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-slate-50 p-10 text-center text-slate-500">
        Run Analyze Repository to load the profile.
      </div>
    );
  }

  const topics = Array.isArray(profile.topics) ? profile.topics : [];

  return (
    <div className="space-y-6">
      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <BadgeCheck className="h-3.5 w-3.5" />
            Repository Profile
          </div>
        }
        bodyClassName="space-y-6 pt-6"
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(360px,1fr)] lg:items-start">
          <div>
            <h3 className="text-2xl font-semibold tracking-tight text-slate-900">{profile.full_name}</h3>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
              {formatValue(profile.description)}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Globe className="h-4 w-4" />
                Language
              </div>
              <p className="mt-2 text-lg font-semibold text-slate-900">
                {formatValue(profile.language)}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Scale className="h-4 w-4" />
                License
              </div>
              <p className="mt-2 text-lg font-semibold text-slate-900">
                {formatValue(profile.license)}
              </p>
            </div>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Star className="h-4 w-4" />
              Stars
            </div>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
              {formatValue(profile.stars)}
            </p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <GitFork className="h-4 w-4" />
              Forks
            </div>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
              {formatValue(profile.forks)}
            </p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Globe className="h-4 w-4" />
              Language
            </div>
            <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">
              {formatValue(profile.language)}
            </p>
          </div>
        </div>
      </UiCard>

      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <Tag className="h-3.5 w-3.5" />
            Topics
          </div>
        }
      >
        <div className="flex flex-wrap gap-2">
          {topics.length > 0 ? (
            topics.map((topic) => (
              <span
                key={topic}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-700"
              >
                {topic}
              </span>
            ))
          ) : (
            <span className="text-sm text-slate-500">No topics available.</span>
          )}
        </div>
      </UiCard>

      <div className="grid gap-4 lg:grid-cols-3">
        <ScoreCard label="Maintenance Score" value={profile.maintenance_score} />
        <ScoreCard label="Enterprise Score" value={profile.enterprise_score} />
        <ScoreCard label="Community Score" value={profile.community_score} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <UiCard
          badge={
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <FileText className="h-3.5 w-3.5" />
              Summary
            </div>
          }
        >
          <p className="text-sm leading-7 text-slate-700">{formatValue(profile.summary)}</p>
        </UiCard>

        <UiCard
          badge={
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <Target className="h-3.5 w-3.5" />
              Recommendation
            </div>
          }
        >
          <p className="text-sm leading-7 text-slate-700">{formatValue(profile.recommendation)}</p>
        </UiCard>
      </div>
    </div>
  );
}
