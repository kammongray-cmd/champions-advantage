import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAttachments, useDeleteAttachment } from "../hooks/useProjects";
import { useToast } from "../components/Toast";
import FileUpload from "../components/FileUpload";
import Lightbox from "../components/Lightbox";
import { getStatusBadgeClass, getStatusLabel, formatCurrency, formatDate, formatDateTime } from "../lib/utils";
import {
  ArrowLeft, Phone, Mail, MapPin, ChevronDown, ChevronUp,
  Clock, FileText, Shield, Save, Trash2, Trophy, X as XIcon,
  Image, FolderOpen, ExternalLink, Paperclip, Download,
  Camera, File, FileCheck, Upload, History
} from "lucide-react";
import type { Page } from "../App";

const CATEGORIES = ["Design Mockup", "Customer Photo", "Proposal", "Production File", "Permit", "Other"];

function getCategoryIcon(cat: string) {
  switch (cat) {
    case "Design Mockup": return <Image size={14} color="var(--accent-purple)" />;
    case "Customer Photo": return <Camera size={14} color="var(--accent-blue)" />;
    case "Proposal": return <FileCheck size={14} color="var(--accent-green)" />;
    case "Production File": return <File size={14} color="var(--accent-orange)" />;
    case "Permit": return <FileText size={14} color="var(--accent-yellow)" />;
    default: return <Paperclip size={14} color="var(--text-muted)" />;
  }
}

function formatFileSize(bytes: number | null) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function isImage(mime: string | null) {
  return mime?.startsWith("image/") || false;
}

function getTimelineClass(entryType: string) {
  const t = (entryType || "").toLowerCase();
  if (t.includes("status")) return "type-status";
  if (t.includes("file") || t.includes("upload")) return "type-file";
  if (t.includes("action") || t.includes("done")) return "type-action";
  if (t.includes("created")) return "type-created";
  return "";
}

interface Props {
  projectId: string;
  onNavigate: (p: Page) => void;
}

export default function ProjectDetail({ projectId, onNavigate }: Props) {
  const qc = useQueryClient();
  const toast = useToast();
  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });
  const { data: history } = useQuery({
    queryKey: ["project-history", projectId],
    queryFn: () => api.getProjectHistory(projectId),
  });
  const { data: attachments, refetch: refetchAttachments } = useAttachments(projectId);
  const deleteAttachment = useDeleteAttachment();

  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState<any>({});
  const [actionNote, setActionNote] = useState("");
  const [actionDue, setActionDue] = useState("");
  const [showBlocks, setShowBlocks] = useState<Record<string, boolean>>({
    files: true, action: true, identity: true, history: false, drive: false,
  });
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  const updateProject = useMutation({
    mutationFn: (data: any) => api.updateProject(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
      setEditing(false);
      toast("Project updated", "success");
    },
  });

  const updateAction = useMutation({
    mutationFn: (data: any) => api.updateProjectAction(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["daily-summary"] });
      toast("Action saved", "success");
    },
  });

  const clearAction = useMutation({
    mutationFn: () => api.clearProjectAction(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["daily-summary"] });
      setActionNote("");
      setActionDue("");
      toast("Action completed", "success");
    },
  });

  const handleDeleteAttachment = useCallback(async (fileId: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return;
    await deleteAttachment.mutateAsync({ projectId, fileId });
    toast("File deleted", "info");
  }, [projectId, deleteAttachment, toast]);

  if (isLoading) return <div className="loading-spinner" />;
  if (!project) return <div className="page-container"><p>Project not found</p></div>;

  const isLocked = project.productionLocked;
  const p = project;

  const imageAttachments = (attachments || []).filter((a: any) => isImage(a.mimeType));
  const lightboxImages = imageAttachments.map((a: any) => ({
    src: `/uploads/${a.filename}`,
    name: a.originalName,
    category: a.category,
  }));

  const heroImage = (attachments || []).find(
    (a: any) => a.category === "Design Mockup" && isImage(a.mimeType)
  ) || imageAttachments[0];

  const groupedAttachments: Record<string, any[]> = {};
  (attachments || []).forEach((a: any) => {
    const cat = a.category || "Other";
    if (!groupedAttachments[cat]) groupedAttachments[cat] = [];
    groupedAttachments[cat].push(a);
  });

  function startEdit() {
    setFormData({
      clientName: p.clientName || "",
      siteAddress: p.siteAddress || "",
      primaryContactName: p.primaryContactName || "",
      primaryContactPhone: p.primaryContactPhone || "",
      primaryContactEmail: p.primaryContactEmail || "",
      secondaryContactName: p.secondaryContactName || "",
      secondaryContactPhone: p.secondaryContactPhone || "",
      secondaryContactEmail: p.secondaryContactEmail || "",
      notes: p.notes || "",
      estimatedValue: p.estimatedValue || "",
    });
    setEditing(true);
  }

  function toggleBlock(name: string) {
    setShowBlocks((prev) => ({ ...prev, [name]: !prev[name] }));
  }

  const statuses = ["New", "Block A", "Block B", "Block C", "Block D", "ACTIVE PRODUCTION", "Archived", "Closed - Won", "Closed - Lost"];

  return (
    <div className="page-container">
      <button
        className="btn-icon mb-3"
        onClick={() => onNavigate({ name: "projects" })}
        style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)", fontSize: 14 }}
      >
        <ArrowLeft size={18} /> Back
      </button>

      {heroImage && (
        <div
          className="hero-banner"
          onClick={() => {
            const idx = imageAttachments.findIndex((a: any) => a.id === heroImage.id);
            setLightboxIndex(idx >= 0 ? idx : 0);
            setLightboxOpen(true);
          }}
          style={{ cursor: "pointer" }}
        >
          <img
            src={heroImage.thumbnailPath ? heroImage.thumbnailPath : `/uploads/${heroImage.filename}`}
            alt={heroImage.originalName}
          />
          <div className="hero-overlay">
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="file-category-tag">{heroImage.category}</span>
              <span style={{ fontSize: 12, color: "rgba(255,255,255,0.7)" }}>{heroImage.originalName}</span>
            </div>
          </div>
        </div>
      )}

      {isLocked && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.08)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-sm)",
            padding: "10px 16px",
            marginBottom: 16,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <Shield size={16} color="var(--accent-red)" />
          <span style={{ color: "var(--accent-red)", fontWeight: 600, fontSize: 13 }}>
            PRODUCTION LOCKED \u2014 Design changes require Change Order
          </span>
        </div>
      )}

      <div className="card mb-3" style={{ padding: 20 }}>
        <div className="flex-between">
          <div>
            <div className="flex-gap mb-2">
              <span className={`status-badge ${getStatusBadgeClass(p.status)}`}>{getStatusLabel(p.status)}</span>
              <button
                className="btn-small btn-secondary"
                style={{ fontSize: 11, padding: "2px 8px" }}
                onClick={() => setShowStatusModal(true)}
              >
                Change
              </button>
            </div>
            <h1 style={{ fontSize: 22, fontWeight: 700 }}>{p.clientName || "Untitled"}</h1>
          </div>
          {p.estimatedValue && (
            <div style={{ textAlign: "right" }}>
              <div className="text-xs text-muted">Value</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "var(--accent-green)" }}>
                {formatCurrency(p.estimatedValue)}
              </div>
              {p.valueSource === "validated" && (
                <span className="text-xs" style={{ color: "var(--accent-green)" }}>VAL</span>
              )}
            </div>
          )}
        </div>

        {p.siteAddress && (
          <div className="flex-gap mt-2 text-sm text-secondary">
            <MapPin size={14} />
            <a
              href={`https://maps.google.com/?q=${encodeURIComponent(p.siteAddress)}`}
              target="_blank"
              rel="noopener"
            >
              {p.siteAddress}
            </a>
          </div>
        )}

        <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
          {p.primaryContactPhone && (
            <a href={`tel:${p.primaryContactPhone}`} className="btn-secondary btn-small flex-gap" style={{ textDecoration: "none" }}>
              <Phone size={14} /> {p.primaryContactPhone}
            </a>
          )}
          {p.primaryContactEmail && (
            <a href={`mailto:${p.primaryContactEmail}`} className="btn-secondary btn-small flex-gap" style={{ textDecoration: "none" }}>
              <Mail size={14} /> {p.primaryContactEmail}
            </a>
          )}
          {p.googleDriveLink && (
            <a href={p.googleDriveLink} target="_blank" rel="noopener" className="btn-secondary btn-small flex-gap" style={{ textDecoration: "none" }}>
              <FolderOpen size={14} /> Drive
              <ExternalLink size={12} />
            </a>
          )}
        </div>
      </div>

      {imageAttachments.length > 1 && (
        <div className="mb-3">
          <div className="section-header" style={{ cursor: "default" }}>
            <Image size={16} color="var(--accent-purple)" />
            <h3>Gallery</h3>
            <span className="count-badge">{imageAttachments.length}</span>
          </div>
          <div className="photo-gallery">
            {imageAttachments.map((att: any, idx: number) => (
              <div
                key={att.id}
                className="photo-gallery-item"
                onClick={() => {
                  setLightboxIndex(idx);
                  setLightboxOpen(true);
                }}
              >
                <img
                  src={att.thumbnailPath || `/uploads/${att.filename}`}
                  alt={att.originalName}
                  loading="lazy"
                />
                <div className="overlay">{att.originalName}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card mb-3">
        <div className="section-header" onClick={() => toggleBlock("files")}>
          <Paperclip size={16} color="var(--accent-purple)" />
          <h3>Files & Attachments</h3>
          <span className="count-badge">{(attachments || []).length}</span>
          {showBlocks.files ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
        {showBlocks.files && (
          <div>
            <button
              className="btn-secondary btn-small flex-gap mb-3"
              onClick={() => setShowUpload(!showUpload)}
            >
              <Upload size={14} /> {showUpload ? "Close" : "Upload Files"}
            </button>

            {showUpload && (
              <div className="mb-3">
                <FileUpload
                  projectId={projectId}
                  onUploadComplete={() => {
                    refetchAttachments();
                    toast("Files uploaded", "success");
                    setShowUpload(false);
                  }}
                />
              </div>
            )}

            {Object.keys(groupedAttachments).length === 0 && (
              <p className="text-sm text-muted">No files uploaded yet</p>
            )}

            {CATEGORIES.filter((c) => groupedAttachments[c]).map((cat) => (
              <div key={cat} className="mb-3">
                <div className="flex-gap mb-2">
                  {getCategoryIcon(cat)}
                  <span className="text-sm font-bold">{cat}</span>
                  <span className="text-xs text-muted">({groupedAttachments[cat].length})</span>
                </div>
                <div className="flex-col" style={{ gap: 4 }}>
                  {groupedAttachments[cat].map((att: any) => (
                    <div
                      key={att.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "8px 12px",
                        borderRadius: "var(--radius-sm)",
                        background: "var(--bg-secondary)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      {isImage(att.mimeType) && att.thumbnailPath ? (
                        <img
                          src={att.thumbnailPath}
                          alt={att.originalName}
                          style={{
                            width: 40, height: 40, borderRadius: 6,
                            objectFit: "cover", cursor: "pointer",
                          }}
                          onClick={() => {
                            const idx = imageAttachments.findIndex((a: any) => a.id === att.id);
                            setLightboxIndex(idx >= 0 ? idx : 0);
                            setLightboxOpen(true);
                          }}
                        />
                      ) : (
                        <div style={{
                          width: 40, height: 40, borderRadius: 6,
                          background: "var(--bg-card-hover)",
                          display: "flex", alignItems: "center", justifyContent: "center",
                        }}>
                          <FileText size={18} color="var(--text-muted)" />
                        </div>
                      )}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="text-sm font-bold" style={{
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                        }}>
                          {att.originalName}
                        </div>
                        <div className="text-xs text-muted">
                          {formatFileSize(att.fileSize)} \u2022 {formatDate(att.uploadedAt)}
                        </div>
                      </div>
                      <div className="flex-gap">
                        <a
                          href={`/uploads/${att.filename}`}
                          download={att.originalName}
                          className="btn-icon"
                          style={{ padding: 4 }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Download size={14} />
                        </a>
                        <button
                          className="btn-icon"
                          style={{ padding: 4 }}
                          onClick={() => handleDeleteAttachment(att.id, att.originalName)}
                        >
                          <Trash2 size={14} color="var(--accent-red)" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card mb-3">
        <div className="section-header" onClick={() => toggleBlock("action")}>
          <Clock size={16} color="var(--accent-orange)" />
          <h3>Next Action</h3>
          {showBlocks.action ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
        {showBlocks.action && (
          <div>
            {p.pendingAction && p.actionNote && (
              <div
                style={{
                  background: "rgba(247, 147, 30, 0.08)",
                  border: "1px solid rgba(247, 147, 30, 0.3)",
                  borderRadius: "var(--radius-sm)",
                  padding: "10px 14px",
                  marginBottom: 12,
                }}
              >
                <div className="text-sm font-bold">{p.actionNote}</div>
                {p.actionDueDate && (
                  <div className="text-xs text-muted mt-1">Due: {formatDate(p.actionDueDate)}</div>
                )}
                <button
                  className="btn-small btn-primary mt-2"
                  onClick={() => clearAction.mutate()}
                >
                  Done
                </button>
              </div>
            )}
            <div className="flex-col">
              <input
                placeholder="Action note..."
                value={actionNote}
                onChange={(e) => setActionNote(e.target.value)}
              />
              <div className="flex-gap">
                <input type="date" value={actionDue} onChange={(e) => setActionDue(e.target.value)} />
                <button
                  className="btn-primary btn-small"
                  onClick={() => {
                    updateAction.mutate({
                      pendingAction: true,
                      actionNote: actionNote,
                      actionDueDate: actionDue || null,
                    });
                    setActionNote("");
                    setActionDue("");
                  }}
                  disabled={!actionNote}
                >
                  <Save size={14} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="card mb-3">
        <div className="section-header" onClick={() => toggleBlock("identity")}>
          <FileText size={16} color="var(--accent-blue)" />
          <h3>Project Details</h3>
          {showBlocks.identity ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
        {showBlocks.identity && (
          <div>
            {editing ? (
              <div className="flex-col">
                <input placeholder="Project / Client Name" value={formData.clientName} onChange={(e) => setFormData({ ...formData, clientName: e.target.value })} />
                <input placeholder="Site Address" value={formData.siteAddress} onChange={(e) => setFormData({ ...formData, siteAddress: e.target.value })} />
                <div className="grid-2">
                  <input placeholder="Primary Contact" value={formData.primaryContactName} onChange={(e) => setFormData({ ...formData, primaryContactName: e.target.value })} />
                  <input placeholder="Phone" value={formData.primaryContactPhone} onChange={(e) => setFormData({ ...formData, primaryContactPhone: e.target.value })} />
                </div>
                <input placeholder="Email" value={formData.primaryContactEmail} onChange={(e) => setFormData({ ...formData, primaryContactEmail: e.target.value })} />
                <div className="grid-2">
                  <input placeholder="Secondary Contact" value={formData.secondaryContactName} onChange={(e) => setFormData({ ...formData, secondaryContactName: e.target.value })} />
                  <input placeholder="Phone" value={formData.secondaryContactPhone} onChange={(e) => setFormData({ ...formData, secondaryContactPhone: e.target.value })} />
                </div>
                <input placeholder="Email" value={formData.secondaryContactEmail} onChange={(e) => setFormData({ ...formData, secondaryContactEmail: e.target.value })} />
                <input placeholder="Estimated Value" type="number" value={formData.estimatedValue} onChange={(e) => setFormData({ ...formData, estimatedValue: e.target.value })} />
                <textarea placeholder="Notes" value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} rows={4} />
                <div className="flex-gap">
                  <button className="btn-primary" onClick={() => updateProject.mutate(formData)}>
                    {updateProject.isPending ? "Saving..." : "Save"}
                  </button>
                  <button className="btn-secondary" onClick={() => setEditing(false)}>Cancel</button>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex-col" style={{ gap: 6 }}>
                  {p.primaryContactName && (
                    <div className="text-sm"><span className="text-muted">Contact:</span> {p.primaryContactName}</div>
                  )}
                  {p.secondaryContactName && (
                    <div className="text-sm"><span className="text-muted">Secondary:</span> {p.secondaryContactName} {p.secondaryContactPhone || ""}</div>
                  )}
                  {p.source && <div className="text-sm"><span className="text-muted">Source:</span> {p.source}</div>}
                  {p.notes && (
                    <div className="mt-2" style={{ whiteSpace: "pre-wrap", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                      {p.notes}
                    </div>
                  )}
                </div>
                <button className="btn-secondary btn-small mt-3" onClick={startEdit}>Edit Details</button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="card mb-3">
        <div className="section-header" onClick={() => toggleBlock("history")}>
          <History size={16} color="var(--text-secondary)" />
          <h3>Timeline</h3>
          <span className="count-badge">{(history || []).length}</span>
          {showBlocks.history ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
        {showBlocks.history && (
          <div className="timeline">
            {(history || []).map((h: any) => (
              <div key={h.id} className={`timeline-item ${getTimelineClass(h.entryType)}`}>
                <div className="flex-between">
                  <span className="text-sm">{h.content}</span>
                  <span className="text-xs text-muted" style={{ whiteSpace: "nowrap", marginLeft: 8 }}>
                    {formatDateTime(h.createdAt)}
                  </span>
                </div>
                <span className="text-xs text-muted">{h.entryType}</span>
              </div>
            ))}
            {(history || []).length === 0 && <p className="text-sm text-muted">No history yet</p>}
          </div>
        )}
      </div>

      <div className="flex-gap mt-4 mb-4" style={{ justifyContent: "center" }}>
        <button
          className="btn-danger btn-small"
          onClick={async () => {
            if (confirm("Move this project to Lost Deals?")) {
              await api.updateProject(projectId, { status: "Closed - Lost" });
              qc.invalidateQueries({ queryKey: ["project", projectId] });
              qc.invalidateQueries({ queryKey: ["projects"] });
              toast("Project marked as lost", "info");
            }
          }}
        >
          <XIcon size={14} /> Project Lost
        </button>
        {(p.status === "Block D" || p.status === "ACTIVE PRODUCTION") && (
          <button
            className="btn-primary btn-small flex-gap"
            style={{ background: "var(--accent-green)", color: "#000" }}
            onClick={async () => {
              await api.updateProject(projectId, { status: "Closed - Won" });
              qc.invalidateQueries({ queryKey: ["project", projectId] });
              qc.invalidateQueries({ queryKey: ["projects"] });
              toast("Project won!", "success");
            }}
          >
            <Trophy size={14} /> Project Won
          </button>
        )}
      </div>

      {showStatusModal && (
        <div className="modal-backdrop" onClick={() => setShowStatusModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-3">Change Status</h3>
            <div className="flex-col">
              {statuses.map((s) => (
                <button
                  key={s}
                  className={`btn-secondary ${s === p.status ? "btn-primary" : ""}`}
                  style={{ textAlign: "left" }}
                  onClick={async () => {
                    await api.updateProject(projectId, { status: s });
                    qc.invalidateQueries({ queryKey: ["project", projectId] });
                    qc.invalidateQueries({ queryKey: ["projects"] });
                    qc.invalidateQueries({ queryKey: ["pipeline"] });
                    setShowStatusModal(false);
                    toast(`Status changed to ${s}`, "success");
                  }}
                >
                  <span className={`status-badge ${getStatusBadgeClass(s)}`}>{getStatusLabel(s)}</span>
                  {" "}{s}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {lightboxOpen && lightboxImages.length > 0 && (
        <Lightbox
          images={lightboxImages}
          currentIndex={lightboxIndex}
          onClose={() => setLightboxOpen(false)}
          onNavigate={setLightboxIndex}
        />
      )}
    </div>
  );
}
