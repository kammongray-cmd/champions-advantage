import { useState, useEffect, useRef, useCallback } from "react";
import { Search } from "lucide-react";
import { api } from "../lib/api";
import { getStatusBadgeClass, getStatusLabel } from "../lib/utils";

interface SpotlightProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (id: string) => void;
}

export default function Spotlight({ isOpen, onClose, onSelect }: SpotlightProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function handleGlobal(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
      }
    }
    window.addEventListener("keydown", handleGlobal);
    return () => window.removeEventListener("keydown", handleGlobal);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setResults([]);
      setActiveIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const doSearch = useCallback((q: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q.trim()) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await api.search(q);
        setResults(data);
        setActiveIndex(0);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && results[activeIndex]) {
      onSelect(results[activeIndex].id);
      onClose();
    }
  }

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        zIndex: 2000,
        display: "flex",
        justifyContent: "center",
        paddingTop: 80,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 600,
          maxHeight: "70vh",
          background: "var(--bg-card)",
          border: "1px solid var(--border-color)",
          borderRadius: "var(--radius)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
          alignSelf: "flex-start",
        }}
        onKeyDown={handleKeyDown}
      >
        <div style={{ display: "flex", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--border-color)", gap: 12 }}>
          <Search size={20} color="var(--text-muted)" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search projects..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              doSearch(e.target.value);
            }}
            style={{
              background: "transparent",
              border: "none",
              fontSize: 18,
              color: "var(--text-primary)",
              outline: "none",
              flex: 1,
              padding: 0,
            }}
          />
          <span style={{ fontSize: 12, color: "var(--text-muted)", background: "var(--bg-input)", padding: "2px 8px", borderRadius: 4 }}>ESC</span>
        </div>
        <div style={{ overflowY: "auto", flex: 1 }}>
          {loading && (
            <div style={{ padding: 20, textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>Searching...</div>
          )}
          {!loading && query && results.length === 0 && (
            <div style={{ padding: 20, textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>No results found</div>
          )}
          {results.map((item, i) => (
            <div
              key={item.id}
              onClick={() => {
                onSelect(item.id);
                onClose();
              }}
              style={{
                padding: "12px 16px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: i === activeIndex ? "var(--bg-card-hover)" : "transparent",
                borderBottom: "1px solid var(--border-subtle)",
                transition: "background 0.15s",
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{item.clientName || item.client_name}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                  {item.contactName || item.contact_name || ""}{item.contactPhone || item.contact_phone ? ` · ${item.contactPhone || item.contact_phone}` : ""}
                </div>
              </div>
              <span className={`status-badge ${getStatusBadgeClass(item.status)}`}>
                {getStatusLabel(item.status)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
