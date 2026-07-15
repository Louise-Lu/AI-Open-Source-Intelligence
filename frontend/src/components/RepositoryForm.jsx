import { Github, Search } from 'lucide-react';
import UiCard from './UiCard';

export default function RepositoryForm({
  title,
  owner,
  repo,
  onOwnerChange,
  onRepoChange,
  buttonLabel = 'Analyze Repository',
  buttonIcon: ButtonIcon = Search,
  loading = false,
  showButton = true,
  helperText,
}) {
  return (
    <UiCard
      badge={
        <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
          <Github className="h-3.5 w-3.5" />
          {title}
        </div>
      }
      subheader={helperText}
      bodyClassName="pt-6"
    >
      <div className={showButton ? 'grid gap-4 md:grid-cols-[1fr_1fr_auto]' : 'grid gap-4 md:grid-cols-2'}>
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-slate-700">Owner</span>
          <input
            type="text"
            value={owner}
            onChange={(event) => onOwnerChange(event.target.value)}
            placeholder="langchain-ai"
            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-slate-700">Repo</span>
          <input
            type="text"
            value={repo}
            onChange={(event) => onRepoChange(event.target.value)}
            placeholder="langgraph"
            className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
          />
        </label>

        {showButton ? (
          <div className="flex items-end">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400 md:w-auto"
            >
              <ButtonIcon className="h-4 w-4" />
              {loading ? 'Loading...' : buttonLabel}
            </button>
          </div>
        ) : null}
      </div>
    </UiCard>
  );
}
