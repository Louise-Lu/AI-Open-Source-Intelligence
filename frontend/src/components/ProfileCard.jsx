import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  FileText,
  Globe,
  Layers,
  Scale,
  Sparkles,
  Star,
  Tag,
  Target,
  ThumbsDown,
  ThumbsUp,
  Users,
  XCircle,
} from 'lucide-react';

import UiCard from './UiCard';
import ScoreCard from './ScoreCard';
import Loading from './Loading';
import {
  computeCommunityScore,
  computeEnterpriseScore,
  computeMaintenanceScore,
  extractLicense,
  extractPrimaryLanguage,
  extractStars,
} from '../utils/profileUtils';

/** @typedef {import('../types.js').ProfileResponse} ProfileResponse */

function formatValue(value) {
  return value || value === 0 ? value : '—';
}

function TagList({ items, emptyText = 'No items available.' }) {
  const list = Array.isArray(items) ? items : [];

  if (list.length === 0) {
    return <span className="text-sm text-slate-500">{emptyText}</span>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {list.map((item, index) => (
        <span
          key={`${item}-${index}`}
          className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-700"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function MetricTile({ icon: Icon, label, value }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
        {formatValue(value)}
      </p>
    </div>
  );
}

/**
 * @param {{ profile: ProfileResponse | null, loading?: boolean, error?: string }} props
 */
export default function ProfileCard({ profile, loading = false, error = '' }) {
  if (loading) {
    return (
      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <Sparkles className="h-3.5 w-3.5" />
            Loading Profile
          </div>
        }
      >
        <Loading />
      </UiCard>
    );
  }

  if (error) {
    return (
      <div className="flex items-start gap-3 rounded-3xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-semibold">Failed to load profile</p>
          <p className="mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-slate-50 p-10 text-center text-slate-500">
        Run Analyze Repository to load the profile.
      </div>
    );
  }

  const technicalStack = Array.isArray(profile.technical_stack) ? profile.technical_stack : [];
  const targetUsers = Array.isArray(profile.target_users) ? profile.target_users : [];
  const coreFeatures = Array.isArray(profile.core_features) ? profile.core_features : [];
  const strengths = Array.isArray(profile.strengths) ? profile.strengths : [];
  const weaknesses = Array.isArray(profile.weaknesses) ? profile.weaknesses : [];

  const projectType = profile.project_type || 'N/A';
  const primaryLanguage = extractPrimaryLanguage(technicalStack);
  const license = extractLicense(strengths);
  const stars = extractStars(profile);

  const enterpriseScore = computeEnterpriseScore(profile);
  const maintenanceScore = computeMaintenanceScore(profile);
  const communityScore = computeCommunityScore(profile);

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
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricTile icon={Layers} label="Project Type" value={projectType} />
          <MetricTile icon={Globe} label="Primary Language" value={primaryLanguage} />
          <MetricTile icon={Scale} label="License" value={license} />
          <MetricTile icon={Star} label="Stars" value={stars} />
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
        <TagList items={technicalStack} emptyText="No technical stack available." />
      </UiCard>

      <div className="grid gap-4 lg:grid-cols-3">
        <ScoreCard label="Maintenance Score" value={maintenanceScore} />
        <ScoreCard label="Enterprise Score" value={enterpriseScore} />
        <ScoreCard label="Community Score" value={communityScore} />
      </div>

      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <Users className="h-3.5 w-3.5" />
            Target Users
          </div>
        }
      >
        <TagList items={targetUsers} emptyText="No target users available." />
      </UiCard>

      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Core Features
          </div>
        }
      >
        {coreFeatures.length > 0 ? (
          <ol className="grid gap-3 sm:grid-cols-2">
            {coreFeatures.map((feature, index) => (
              <li
                key={`${feature}-${index}`}
                className="flex gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white">
                  {index + 1}
                </span>
                <span>{feature}</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-slate-500">No core features available.</p>
        )}
      </UiCard>

      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <Target className="h-3.5 w-3.5" />
            Strengths &amp; Weaknesses
          </div>
        }
      >
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-emerald-700">
              <ThumbsUp className="h-4 w-4" />
              Strengths
            </div>
            {strengths.length > 0 ? (
              <ul className="space-y-2">
                {strengths.map((item, index) => (
                  <li
                    key={`strength-${index}`}
                    className="flex gap-2 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-900"
                  >
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No strengths available.</p>
            )}
          </div>

          <div>
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-700">
              <ThumbsDown className="h-4 w-4" />
              Weaknesses
            </div>
            {weaknesses.length > 0 ? (
              <ul className="space-y-2">
                {weaknesses.map((item, index) => (
                  <li
                    key={`weakness-${index}`}
                    className="flex gap-2 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900"
                  >
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No weaknesses available.</p>
            )}
          </div>
        </div>
      </UiCard>

      <UiCard
        badge={
          <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
            <FileText className="h-3.5 w-3.5" />
            Summary
          </div>
        }
      >
        <p className="text-sm leading-7 text-slate-700">{formatValue(profile.summary)}</p>
        {profile.enterprise_readiness?.explanation ? (
          <p className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-7 text-slate-600">
            <span className="font-semibold text-slate-700">Enterprise Readiness: </span>
            {profile.enterprise_readiness.explanation}
          </p>
        ) : null}
      </UiCard>
    </div>
  );
}
