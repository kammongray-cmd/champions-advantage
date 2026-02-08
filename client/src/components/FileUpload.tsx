import { useState, useRef } from "react";
import { Upload, Image, FileText } from "lucide-react";
import { api } from "../lib/api";

const CATEGORIES = ["Design Mockup", "Customer Photo", "Proposal", "Production File", "Permit", "Other"];

interface FileUploadProps {
  projectId: string;
  onUploadComplete: () => void;
}

export default function FileUpload({ projectId, onUploadComplete }: FileUploadProps) {
  const [dragging, setDragging] = useState(false);
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) setSelectedFiles(files);
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (files.length) setSelectedFiles(files);
  }

  async function handleUpload() {
    if (!selectedFiles.length) return;
    setUploading(true);
    try {
      await api.uploadAttachments(projectId, selectedFiles, category);
      setSelectedFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      onUploadComplete();
    } catch {
    } finally {
      setUploading(false);
    }
  }

  function getFileIcon(name: string) {
    const ext = name.split(".").pop()?.toLowerCase() || "";
    if (["jpg", "jpeg", "png", "gif", "webp", "svg"].includes(ext)) {
      return <Image size={14} color="var(--accent-blue)" />;
    }
    return <FileText size={14} color="var(--text-muted)" />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? "var(--accent-orange)" : "var(--border-color)"}`,
          borderRadius: "var(--radius)",
          padding: 32,
          textAlign: "center",
          cursor: "pointer",
          background: dragging ? "rgba(247,147,30,0.05)" : "transparent",
          transition: "all 0.2s",
        }}
      >
        <Upload size={32} color={dragging ? "var(--accent-orange)" : "var(--text-muted)"} />
        <div style={{ marginTop: 8, fontSize: 14, color: "var(--text-secondary)" }}>
          Drop files here or click to browse
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          style={{ display: "none" }}
        />
      </div>

      {selectedFiles.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            {selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""} selected
          </div>
          {selectedFiles.map((f, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
              {getFileIcon(f.name)}
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
              <span style={{ color: "var(--text-muted)", fontSize: 11, flexShrink: 0 }}>
                {(f.size / 1024).toFixed(0)}KB
              </span>
            </div>
          ))}

          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{ flex: 1 }}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <button
              className="btn-primary btn-small"
              onClick={handleUpload}
              disabled={uploading}
              style={{ flexShrink: 0, opacity: uploading ? 0.6 : 1 }}
            >
              {uploading ? "Uploading..." : "Upload"}
            </button>
          </div>

          {uploading && (
            <div style={{ height: 4, borderRadius: 2, background: "var(--border-color)", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: "60%",
                  background: "var(--accent-orange)",
                  borderRadius: 2,
                  animation: "uploadProgress 1.5s ease-in-out infinite",
                }}
              />
              <style>{`
                @keyframes uploadProgress {
                  0% { width: 10%; }
                  50% { width: 80%; }
                  100% { width: 10%; }
                }
              `}</style>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
