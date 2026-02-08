const shimmerStyle = `
  .skeleton {
    background: linear-gradient(90deg, #1a1a1a 25%, #2a2a2a 50%, #1a1a1a 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: var(--radius-sm);
  }
  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
`;

let styleInjected = false;
function injectStyle() {
  if (styleInjected) return;
  styleInjected = true;
  const el = document.createElement("style");
  el.textContent = shimmerStyle;
  document.head.appendChild(el);
}

export function SkeletonLine({ height = 16 }: { height?: number }) {
  injectStyle();
  return <div className="skeleton" style={{ height, width: "100%" }} />;
}

export function SkeletonCard() {
  injectStyle();
  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border-color)",
        borderRadius: "var(--radius)",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <SkeletonLine height={20} />
      <SkeletonLine height={14} />
      <SkeletonLine height={14} />
    </div>
  );
}

export function SkeletonPipeline() {
  injectStyle();
  return (
    <div className="pipeline-grid">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="pipeline-card" style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
          <SkeletonLine height={32} />
          <SkeletonLine height={12} />
        </div>
      ))}
    </div>
  );
}
