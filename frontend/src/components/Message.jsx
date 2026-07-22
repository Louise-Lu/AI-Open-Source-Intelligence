import ToolTrace from './ToolTrace';

function UserMessage({ content }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-3xl rounded-br-md bg-slate-900 px-4 py-3 text-sm leading-7 text-white shadow-sm sm:max-w-[70%]">
        <p className="whitespace-pre-wrap break-words">{content}</p>
      </div>
    </div>
  );
}

function AssistantMessage({ content, trace, task }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-4 rounded-3xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-sm leading-7 text-slate-800 shadow-sm sm:max-w-[80%]">
        {task ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-6 text-slate-600">
            <p className="mb-1 font-semibold uppercase tracking-wide text-slate-500">Task</p>
            <pre className="whitespace-pre-wrap break-words">{JSON.stringify(task, null, 2)}</pre>
          </div>
        ) : null}
        <ToolTrace trace={trace} />
        <div className="whitespace-pre-wrap break-words">{content}</div>
      </div>
    </div>
  );
}

export default function Message({ message }) {
  if (message?.role === 'user') {
    return <UserMessage content={message.content} />;
  }

  return <AssistantMessage content={message.content} trace={message.trace} task={message.task} />;
}
