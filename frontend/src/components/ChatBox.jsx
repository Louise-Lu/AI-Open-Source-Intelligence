import { useEffect, useRef, useState } from 'react';
import { Send, Sparkles } from 'lucide-react';

import { sendMessage } from '../api';
import Message from './Message';

export default function ChatBox() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello. Send me a message and I will reply.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, loading]);

  const handleSend = async (event) => {
    event.preventDefault();

    const trimmed = input.trim();
    if (!trimmed || loading) {
      return;
    }

    setMessages((current) => [...current, { role: 'user', content: trimmed }]);
    setInput('');
    setLoading(true);

    try {
      const response = await sendMessage(trimmed);
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: response?.answer || 'No answer returned from the server.',
          trace: Array.isArray(response?.trace) ? response.trace : [],
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: error?.message || 'Failed to send message.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(226,232,240,0.7),_transparent_40%),linear-gradient(180deg,_#f8fafc_0%,_#ffffff_100%)] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-4xl flex-col justify-center">
        <div className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.10)]">
          <header className="border-b border-slate-200 px-5 py-4 sm:px-6">
            <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
              <Sparkles className="h-3.5 w-3.5" />
              AI Intelligence Agent
            </div>
            <h1 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
              AI Intelligence Agent
            </h1>
            <p className="mt-2 text-sm leading-7 text-slate-500">
              Chat with the backend agent and render answers in a clean ChatGPT-style layout.
            </p>
          </header>

          <div className="grid min-h-[32rem] grid-rows-[1fr_auto]">
            <div className="space-y-4 overflow-y-auto px-4 py-5 sm:px-6">
              {messages.map((message, index) => (
                <Message key={`${message.role}-${index}`} message={message} />
              ))}

              {loading ? (
                <div className="flex justify-start">
                  <div className="rounded-3xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                    AI is typing...
                  </div>
                </div>
              ) : null}

              <div ref={bottomRef} />
            </div>

            <form onSubmit={handleSend} className="border-t border-slate-200 bg-slate-50 p-4 sm:p-6">
              <div className="flex flex-col gap-3 sm:flex-row">
                <input
                  type="text"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Type your message..."
                  className="flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-400"
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                >
                  <Send className="h-4 w-4" />
                  {loading ? 'Sending...' : 'Send'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
