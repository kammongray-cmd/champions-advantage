import { useState } from "react";
import { useProjects, useCreateProject } from "../hooks/useProjects";
import { useToast } from "../components/Toast";
import { SkeletonCard } from "../components/Skeleton";
import { getStatusBadgeClass, getStatusLabel, formatCurrency, timeAgo } from "../lib/utils";
import { Search, Plus, ChevronRight, X } from "lucide-react";
import type { Page } from "../App";

interface Props {
  onNavigate: (p: Page) => void;
}

export default function ProjectsList({ onNavigate }: Props) {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newNotes, setNewNotes] = useState("");

  const params: Record<string, string> = {};
  if (search) params.search = search;
  if (statusFilter !== "all") params.status = statusFilter;

  const { data: projects, isLoading } = useProjects(params);
  const createProject = useCreateProject();

  const handleCreate = async () => {
    if (!newName.trim()) return;
    await createProject.mutateAsync({
      clientName: newName,
      notes: newNotes,
      status: "Block A",
    });
    setNewName("");
    setNewNotes("");
    setShowCreate(false);
    toast("Project created", "success");
  };

  return (
    <div className="page-container">
      <div className="flex-between mb-3">
        <h1 className="page-title" style={{ marginBottom: 0 }}>Projects</h1>
        <button className="btn-primary btn-small flex-gap" onClick={() => setShowCreate(true)}>
          <Plus size={14} /> New
        </button>
      </div>

      <div className="flex-gap mb-3">
        <div className="search-input" style={{ flex: 1 }}>
          <Search size={16} />
          <input
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ width: "auto", minWidth: 120 }}
        >
          <option value="all">All Status</option>
          <option value="New">New</option>
          <option value="Block A">Block A</option>
          <option value="Block B">Block B</option>
          <option value="Block C">Block C</option>
          <option value="Block D">Block D</option>
          <option value="ACTIVE PRODUCTION">Production</option>
          <option value="Closed - Won">Won</option>
          <option value="Closed - Lost">Lost</option>
          <option value="Archived">Archived</option>
        </select>
      </div>

      {isLoading && <div className="flex-col gap-2"><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>}

      <div className="flex-col gap-2">
        {(projects || []).map((p: any) => (
          <div
            key={p.id}
            className="card card-hover"
            onClick={() => onNavigate({ name: "project-detail", id: p.id })}
            style={{ padding: "12px 16px" }}
          >
            <div className="flex-between">
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="flex-gap">
                  <span className={`status-badge ${getStatusBadgeClass(p.status)}`}>
                    {getStatusLabel(p.status)}
                  </span>
                  <span className="font-bold" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {p.clientName || "Untitled"}
                  </span>
                </div>
                {p.primaryContactName && (
                  <div className="text-sm text-secondary mt-1">{p.primaryContactName}</div>
                )}
              </div>
              <div className="flex-gap">
                {p.estimatedValue && (
                  <span className="text-sm" style={{ color: "var(--accent-green)" }}>
                    {formatCurrency(p.estimatedValue)}
                  </span>
                )}
                <span className="text-xs text-muted">{timeAgo(p.lastTouched || p.updatedAt)}</span>
                <ChevronRight size={18} color="var(--text-muted)" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {!isLoading && (projects || []).length === 0 && (
        <div className="empty-state">
          <p>No projects found</p>
        </div>
      )}

      {showCreate && (
        <div className="modal-backdrop" onClick={() => setShowCreate(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="flex-between mb-3">
              <h3>New Project</h3>
              <button className="btn-icon" onClick={() => setShowCreate(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="flex-col">
              <input
                placeholder="Project / Client Name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                autoFocus
              />
              <textarea
                placeholder="Notes (optional)"
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
                rows={3}
              />
              <button className="btn-primary" onClick={handleCreate} disabled={createProject.isPending}>
                {createProject.isPending ? "Creating..." : "Create Project"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
