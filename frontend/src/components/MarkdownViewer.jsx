import ReactMarkdown from 'react-markdown';
import { FileText } from 'lucide-react';

import UiCard from './UiCard';

export default function MarkdownViewer({ title, content, emptyText = 'No content available.' }) {
  return (
    <UiCard
      badge={
        <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
          <FileText className="h-3.5 w-3.5" />
          {title}
        </div>
      }
      subheader="Rendered markdown content"
      bodyClassName="pt-6"
    >
      {content ? (
        <article className="space-y-4">
          <ReactMarkdown
            components={{
              h1: ({ children }) => (
                <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{children}</h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-xl font-semibold tracking-tight text-slate-900">{children}</h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-lg font-semibold tracking-tight text-slate-900">{children}</h3>
              ),
              p: ({ children }) => <p className="text-sm leading-7 text-slate-700">{children}</p>,
              ul: ({ children }) => (
                <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">{children}</ol>
              ),
              li: ({ children }) => <li className="leading-7 text-slate-700">{children}</li>,
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-slate-200 pl-4 text-sm italic text-slate-600">
                  {children}
                </blockquote>
              ),
              a: ({ children, href }) => (
                <a
                  href={href}
                  className="font-medium text-slate-900 underline underline-offset-4"
                  target="_blank"
                  rel="noreferrer"
                >
                  {children}
                </a>
              ),
              code: ({ inline, children }) =>
                inline ? (
                  <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[0.85em] text-slate-800">
                    {children}
                  </code>
                ) : (
                  <pre className="overflow-x-auto rounded-2xl bg-slate-950 p-4 text-sm text-slate-100">
                    <code>{children}</code>
                  </pre>
                ),
              hr: () => <hr className="border-slate-200" />,
            }}
          >
            {content}
          </ReactMarkdown>
        </article>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-sm text-slate-500">
          {emptyText}
        </div>
      )}
    </UiCard>
  );
}
