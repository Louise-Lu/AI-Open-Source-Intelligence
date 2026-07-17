import { useState } from 'react';
import {
  AlertTriangle,
  ArrowRightLeft,
  BarChart3,
  GitPullRequest,
  Sparkles,
  FileText,
  GitBranch,
  Diff,
  Map,
} from 'lucide-react';

import { getAnalysis } from '../api/analysis';
import { getComparison } from '../api/comparison';
import { getProfile } from '../api/profile';
import { getReleaseDiff } from '../api/releaseDiff';
import { getRoadmap } from '../api/roadmap';
import Loading from '../components/Loading';
import MarkdownViewer from '../components/MarkdownViewer';
import ProfileCard from '../components/ProfileCard';
import RoadmapCard from '../components/RoadmapCard';
import RepositoryForm from '../components/RepositoryForm';
import UiCard from '../components/UiCard';

const tabs = [
  { id: 'profile', label: 'Profile', icon: FileText },
  { id: 'releaseDiff', label: 'Release Diff', icon: Diff },
  { id: 'roadmap', label: 'Roadmap', icon: Map },
  { id: 'analysis', label: 'Analysis', icon: BarChart3 },
  { id: 'comparison', label: 'Comparison', icon: ArrowRightLeft },
];

function extractMarkdown(payload, fallbackKey) {
  if (typeof payload === 'string') {
    return payload;
  }

  if (payload && typeof payload === 'object') {
    return payload[fallbackKey] || payload.analysis || payload.comparison || payload.content || '';
  }

  return '';
}

function Alert({ message }) {
  if (!message) {
    return null;
  }

  return (
    <div className="flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export default function Dashboard() {
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');

  const [profile, setProfile] = useState(null);
  const [profileError, setProfileError] = useState('');
  const [roadmap, setRoadmap] = useState(null);
  const [analysis, setAnalysis] = useState('');
  const [topError, setTopError] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState('profile');

  const [compareRepoAOwner, setCompareRepoAOwner] = useState('');
  const [compareRepoAName, setCompareRepoAName] = useState('');
  const [compareRepoBOwner, setCompareRepoBOwner] = useState('');
  const [compareRepoBName, setCompareRepoBName] = useState('');
  const [comparison, setComparison] = useState('');
  const [comparisonError, setComparisonError] = useState('');
  const [comparisonLoading, setComparisonLoading] = useState(false);

  const [releaseOwner, setReleaseOwner] = useState('');
  const [releaseRepo, setReleaseRepo] = useState('');
  const [oldTag, setOldTag] = useState('');
  const [newTag, setNewTag] = useState('');
  const [releaseDiff, setReleaseDiff] = useState('');
  const [releaseDiffError, setReleaseDiffError] = useState('');
  const [releaseDiffLoading, setReleaseDiffLoading] = useState(false);

  const handleAnalyze = async (event) => {
    event.preventDefault();

    const trimmedOwner = owner.trim();
    const trimmedRepo = repo.trim();

    if (!trimmedOwner || !trimmedRepo) {
      setTopError('Please enter both Owner and Repo before analyzing.');
      return;
    }

    setTopError('');
    setProfile(null);
    setProfileError('');
    setRoadmap(null);
    setAnalysis('');
    setIsAnalyzing(true);

    const [analysisResult, profileResult, roadmapResult] = await Promise.allSettled([
      getAnalysis(trimmedOwner, trimmedRepo),
      getProfile(trimmedOwner, trimmedRepo),
      getRoadmap(trimmedOwner, trimmedRepo),
    ]);

    const errors = [];

    if (analysisResult.status === 'fulfilled') {
      setAnalysis(extractMarkdown(analysisResult.value, 'analysis'));
    } else {
      errors.push(analysisResult.reason?.message || 'Failed to load analysis.');
    }

    if (profileResult.status === 'fulfilled') {
      setProfile(profileResult.value);
      setProfileError('');
    } else {
      const message = profileResult.reason?.message || 'Failed to load profile.';
      setProfileError(message);
      errors.push(message);
    }

    if (roadmapResult.status === 'fulfilled') {
      setRoadmap(roadmapResult.value);
    } else {
      errors.push(roadmapResult.reason?.message || 'Failed to load roadmap.');
    }

    setTopError(errors.join(' | '));
    setIsAnalyzing(false);
  };

  const handleComparison = async (event) => {
    event.preventDefault();

    const repo1 = `${compareRepoAOwner.trim()}/${compareRepoAName.trim()}`.replace(/^\/|\/$/g, '');
    const repo2 = `${compareRepoBOwner.trim()}/${compareRepoBName.trim()}`.replace(/^\/|\/$/g, '');

    if (!compareRepoAOwner.trim() || !compareRepoAName.trim() || !compareRepoBOwner.trim() || !compareRepoBName.trim()) {
      setComparisonError('Please complete Repository A and Repository B before comparing.');
      return;
    }

    setComparisonError('');
    setComparison('');
    setComparisonLoading(true);

    try {
      const result = await getComparison(repo1, repo2);
      setComparison(extractMarkdown(result, 'comparison'));
    } catch (error) {
      setComparisonError(error.message || 'Failed to compare repositories.');
    } finally {
      setComparisonLoading(false);
    }
  };

  const handleReleaseDiff = async (event) => {
    event.preventDefault();

    if (!releaseOwner.trim() || !releaseRepo.trim() || !oldTag.trim() || !newTag.trim()) {
      setReleaseDiffError('Please complete Owner, Repo, Old Tag, and New Tag before comparing releases.');
      return;
    }

    setReleaseDiffError('');
    setReleaseDiff('');
    setReleaseDiffLoading(true);

    try {
      const result = await getReleaseDiff(
        releaseOwner.trim(),
        releaseRepo.trim(),
        oldTag.trim(),
        newTag.trim(),
      );
      setReleaseDiff(extractMarkdown(result, 'comparison'));
    } catch (error) {
      setReleaseDiffError(error.message || 'Failed to compare releases.');
    } finally {
      setReleaseDiffLoading(false);
    }
  };

  const activeTabLabel = tabs.find((tab) => tab.id === activeTab)?.label || 'Profile';

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(226,232,240,0.55),_transparent_45%),linear-gradient(180deg,_#f8fafc_0%,_#ffffff_100%)]">
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.95fr]">
          <UiCard
            className="overflow-hidden"
            badge={
              <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                <GitBranch className="h-3.5 w-3.5" />
                GitHub AI Intelligence Platform
              </div>
            }
            bodyClassName="space-y-6 pt-6"
          >

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Profile</p>
                <p className="mt-2 text-sm text-slate-700">Repository metadata and score cards</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Release Diff
                </p>
                <p className="mt-2 text-sm text-slate-700">Compare release notes quickly</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Roadmap
                </p>
                <p className="mt-2 text-sm text-slate-700">Stage, direction, and risk forecast</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Analysis</p>
                <p className="mt-2 text-sm text-slate-700">Markdown intelligence report</p>
              </div>
            </div>

            <div className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-500">
              API Base URL: http://127.0.0.1:8000
            </div>
          </UiCard>

          <form onSubmit={handleAnalyze}>
            <RepositoryForm
              title="Repository"
              helperText="Enter the repository owner and name. Analyze Repository fetches Profile, Roadmap, and Analysis together."
              owner={owner}
              repo={repo}
              onOwnerChange={setOwner}
              onRepoChange={setRepo}
              buttonLabel="Analyze Repository"
              buttonIcon={Sparkles}
              loading={isAnalyzing}
              showButton
            />
          </form>
        </div>

        <section className="space-y-6">
          {isAnalyzing ? (
            <UiCard
              badge={
                <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                  <Sparkles className="h-3.5 w-3.5" />
                  Loading
                </div>
              }
            >
              <Loading />
            </UiCard>
          ) : null}
          <Alert message={topError} />

          <UiCard bodyClassName="px-0 py-0">
            <div className="border-b border-slate-200 px-4 pt-4 sm:px-6">
              <div className="flex flex-wrap gap-2">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;

                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setActiveTab(tab.id)}
                      className={[
                        'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition',
                        isActive
                          ? 'bg-slate-900 text-white shadow-sm'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
                      ].join(' ')}
                    >
                      <Icon className="h-4 w-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>
              <div className="pb-4 pt-4 text-sm text-slate-500">
                Active section: <span className="font-medium text-slate-700">{activeTabLabel}</span>
              </div>
            </div>

            <div className="space-y-6 p-4 sm:p-6">
              {activeTab === 'profile' ? (
                <ProfileCard profile={profile} error={profileError} />
              ) : null}

              {activeTab === 'roadmap' ? <RoadmapCard roadmap={roadmap} /> : null}

              {activeTab === 'analysis' ? (
                <MarkdownViewer
                  title="Analysis"
                  content={analysis}
                  emptyText="Run Analyze Repository to load the markdown analysis."
                />
              ) : null}

              {activeTab === 'comparison' ? (                <div className="space-y-6">
                  <div className="grid gap-4 xl:grid-cols-2">
                    <RepositoryForm
                      title="Repository A"
                      helperText="Enter the first repository to compare."
                      owner={compareRepoAOwner}
                      repo={compareRepoAName}
                      onOwnerChange={setCompareRepoAOwner}
                      onRepoChange={setCompareRepoAName}
                      showButton={false}
                    />
                    <RepositoryForm
                      title="Repository B"
                      helperText="Enter the second repository to compare."
                      owner={compareRepoBOwner}
                      repo={compareRepoBName}
                      onOwnerChange={setCompareRepoBOwner}
                      onRepoChange={setCompareRepoBName}
                      showButton={false}
                    />
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={handleComparison}
                      disabled={comparisonLoading}
                      className="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                    >
                      <ArrowRightLeft className="h-4 w-4" />
                      {comparisonLoading ? 'Comparing...' : 'Compare'}
                    </button>
                  </div>

                  <Alert message={comparisonError} />

                  <MarkdownViewer
                    title="Comparison"
                    content={comparison}
                    emptyText="Run Compare to render the markdown comparison."
                  />
                </div>
              ) : null}

              {activeTab === 'releaseDiff' ? (
                <div className="space-y-6">
                  <UiCard
                    badge={
                      <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                        <GitPullRequest className="h-3.5 w-3.5" />
                        Release Diff
                      </div>
                    }
                  >
                    <form onSubmit={handleReleaseDiff} className="space-y-6">
                      <div className="grid gap-4 md:grid-cols-2">
                        <label className="block">
                          <span className="mb-2 block text-sm font-medium text-slate-700">Owner</span>
                          <input
                            type="text"
                            value={releaseOwner}
                            onChange={(event) => setReleaseOwner(event.target.value)}
                            placeholder="langchain-ai"
                            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                          />
                        </label>

                        <label className="block">
                          <span className="mb-2 block text-sm font-medium text-slate-700">Repo</span>
                          <input
                            type="text"
                            value={releaseRepo}
                            onChange={(event) => setReleaseRepo(event.target.value)}
                            placeholder="langgraph"
                            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                          />
                        </label>

                        <label className="block">
                          <span className="mb-2 block text-sm font-medium text-slate-700">Old Tag</span>
                          <input
                            type="text"
                            value={oldTag}
                            onChange={(event) => setOldTag(event.target.value)}
                            placeholder="v0.1.0"
                            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                          />
                        </label>

                        <label className="block">
                          <span className="mb-2 block text-sm font-medium text-slate-700">New Tag</span>
                          <input
                            type="text"
                            value={newTag}
                            onChange={(event) => setNewTag(event.target.value)}
                            placeholder="v0.2.0"
                            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                          />
                        </label>
                      </div>

                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={releaseDiffLoading}
                          className="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                        >
                          <GitPullRequest className="h-4 w-4" />
                          {releaseDiffLoading ? 'Comparing Release...' : 'Compare Release'}
                        </button>
                      </div>
                    </form>
                  </UiCard>

                  <Alert message={releaseDiffError} />

                  <MarkdownViewer
                    title="Release Diff"
                    content={releaseDiff}
                    emptyText="Run Compare Release to render the markdown release diff."
                  />
                </div>
              ) : null}
            </div>
          </UiCard>
        </section>
      </main>
    </div>
  );
}
