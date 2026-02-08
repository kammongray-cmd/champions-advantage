import { useEffect, useCallback } from "react";
import { X, ChevronLeft, ChevronRight } from "lucide-react";

interface LightboxImage {
  src: string;
  name: string;
  category?: string;
}

interface LightboxProps {
  images: LightboxImage[];
  currentIndex: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

export default function Lightbox({ images, currentIndex, onClose, onNavigate }: LightboxProps) {
  const current = images[currentIndex];
  const hasMultiple = images.length > 1;

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && hasMultiple) onNavigate((currentIndex - 1 + images.length) % images.length);
      if (e.key === "ArrowRight" && hasMultiple) onNavigate((currentIndex + 1) % images.length);
    },
    [currentIndex, images.length, hasMultiple, onClose, onNavigate]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (!current) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.9)",
        zIndex: 3000,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <button
        onClick={onClose}
        style={{
          position: "absolute",
          top: 16,
          right: 16,
          background: "rgba(255,255,255,0.1)",
          border: "none",
          borderRadius: "50%",
          padding: 8,
          cursor: "pointer",
          color: "var(--text-primary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <X size={24} />
      </button>

      <div style={{ display: "flex", alignItems: "center", gap: 16, maxWidth: "95vw" }}>
        {hasMultiple && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onNavigate((currentIndex - 1 + images.length) % images.length);
            }}
            style={{
              background: "rgba(255,255,255,0.1)",
              border: "none",
              borderRadius: "50%",
              padding: 8,
              cursor: "pointer",
              color: "var(--text-primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <ChevronLeft size={24} />
          </button>
        )}

        <img
          src={current.src}
          alt={current.name}
          style={{
            maxWidth: "90vw",
            maxHeight: "90vh",
            objectFit: "contain",
            borderRadius: "var(--radius-sm)",
          }}
        />

        {hasMultiple && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onNavigate((currentIndex + 1) % images.length);
            }}
            style={{
              background: "rgba(255,255,255,0.1)",
              border: "none",
              borderRadius: "50%",
              padding: 8,
              cursor: "pointer",
              color: "var(--text-primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <ChevronRight size={24} />
          </button>
        )}
      </div>

      <div style={{ marginTop: 16, textAlign: "center" }}>
        <div style={{ fontSize: 14, color: "var(--text-primary)", fontWeight: 500 }}>{current.name}</div>
        {current.category && (
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{current.category}</div>
        )}
        {hasMultiple && (
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            {currentIndex + 1} / {images.length}
          </div>
        )}
      </div>
    </div>
  );
}
