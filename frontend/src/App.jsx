import { useState } from 'react';
import { BarChart3, MessageSquareText } from 'lucide-react';

import Chat from './pages/Chat';
import Dashboard from './pages/Dashboard';

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
              AI Intelligence Agent
            </p>
            <h1 className="text-lg font-semibold tracking-tight text-slate-900">
              GitHub AI Intelligence Platform
            </h1>
          </div>

          <div className="inline-flex rounded-full border border-slate-200 bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => setActivePage('dashboard')}
              className={[
                'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition',
                activePage === 'dashboard'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900',
              ].join(' ')}
            >
              <BarChart3 className="h-4 w-4" />
              Dashboard
            </button>
            <button
              type="button"
              onClick={() => setActivePage('chat')}
              className={[
                'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition',
                activePage === 'chat'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900',
              ].join(' ')}
            >
              <MessageSquareText className="h-4 w-4" />
              Chat
            </button>
          </div>
        </div>
      </header>

      {activePage === 'dashboard' ? <Dashboard /> : <Chat />}
    </div>
  );
}
