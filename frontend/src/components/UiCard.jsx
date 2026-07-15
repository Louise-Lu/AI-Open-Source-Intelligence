export default function UiCard({
  children,
  className = '',
  header,
  subheader,
  badge,
  bodyClassName = '',
}) {
  return (
    <section className={`rounded-3xl border border-slate-200 bg-white shadow-soft ${className}`}>
      {(header || subheader || badge) ? (
        <div className="border-b border-slate-200 px-5 py-4 sm:px-6">
          {badge ? <div className="mb-2">{badge}</div> : null}
          {header ? <h3 className="text-base font-semibold tracking-tight text-slate-900">{header}</h3> : null}
          {subheader ? <p className="mt-1 text-sm leading-6 text-slate-600">{subheader}</p> : null}
        </div>
      ) : null}
      <div className={`px-5 py-5 sm:px-6 ${bodyClassName}`}>{children}</div>
    </section>
  );
}
