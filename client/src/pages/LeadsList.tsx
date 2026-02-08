import { useState } from "react";
import { useLeads, useCreateProject, useConvertLead } from "../hooks/useProjects";
import { useToast } from "../components/Toast";
import { SkeletonCard } from "../components/Skeleton";
import { formatDateTime } from "../lib/utils";
import { Plus, ChevronRight, Flame, X, UserPlus } from "lucide-react";
import type { Page } from "../App";

interface Props {
  onNavigate: (p: Page) => void;
}

export default function LeadsList({ onNavigate }: Props) {
  const toast = useToast();
  const { data: leads, isLoading } = useLeads();
  const createLead = useCreateProject();
  const convertLead = useConvertLead();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ clientName: "", primaryContactName: "", primaryContactPhone: "", primaryContactEmail: "", notes: "", siteAddress: "" });

  const handleCreate = async () => {
    if (!form.clientName.trim()) return;
    await createLead.mutateAsync({
      clientName: form.clientName,
      primaryContactName: form.primaryContactName,
      primaryContactPhone: form.primaryContactPhone,
      primaryContactEmail: form.primaryContactEmail,
      notes: form.notes,
      siteAddress: form.siteAddress,
      status: "New",
      source: "manual",
    });
    setForm({ clientName: "", primaryContactName: "", primaryContactPhone: "", primaryContactEmail: "", notes: "", siteAddress: "" });
    setShowCreate(false);
    toast("Lead created", "success");
  };

  const handleConvert = async (id: string) => {
    await convertLead.mutateAsync(id);
    toast("Lead promoted to Block A", "success");
  };

  return (
    <div className="page-container">
      <div className="flex-between mb-3">
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          <Flame size={24} color="var(--accent-orange)" style={{ verticalAlign: "middle", marginRight: 8 }} />
          Hot Leads
        </h1>
        <button className="btn-primary btn-small flex-gap" onClick={() => setShowCreate(true)}>
          <Plus size={14} /> New Lead
        </button>
      </div>

      {isLoading && <div className="flex-col gap-2"><SkeletonCard /><SkeletonCard /></div>}

      <div className="flex-col gap-2">
        {(leads || []).map((lead: any) => (
          <div key={lead.id} className="card" style={{ padding: "14px 16px" }}>
            <div className="flex-between">
              <div style={{ flex: 1 }}>
                <div className="font-bold">{lead.clientName || lead.name || "Unknown"}</div>
                <div className="text-sm text-secondary mt-1">
                  {lead.primaryContactPhone || lead.phone || ""}
                  {(lead.primaryContactEmail || lead.email) && ` • ${lead.primaryContactEmail || lead.email}`}
                </div>
                {lead.notes && <div className="text-sm text-muted mt-1" style={{ maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{lead.notes}</div>}
                <div className="text-xs text-muted mt-1">{formatDateTime(lead.createdAt)}</div>
              </div>
              <div className="flex-gap">
                <button
                  className="btn-small btn-primary flex-gap"
                  onClick={() => handleConvert(lead.id)}
                  title="Promote to Block A"
                >
                  <UserPlus size={14} /> Promote
                </button>
                <button
                  className="btn-icon"
                  onClick={() => onNavigate({ name: "project-detail", id: lead.id })}
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {!isLoading && (leads || []).length === 0 && (
        <div className="empty-state">
          <Flame size={48} />
          <p>No hot leads right now</p>
        </div>
      )}

      {showCreate && (
        <div className="modal-backdrop" onClick={() => setShowCreate(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="flex-between mb-3">
              <h3>New Lead</h3>
              <button className="btn-icon" onClick={() => setShowCreate(false)}><X size={18} /></button>
            </div>
            <div className="flex-col">
              <input placeholder="Name / Company" value={form.clientName} onChange={(e) => setForm({ ...form, clientName: e.target.value })} autoFocus />
              <input placeholder="Contact Name" value={form.primaryContactName} onChange={(e) => setForm({ ...form, primaryContactName: e.target.value })} />
              <div className="grid-2">
                <input placeholder="Phone" value={form.primaryContactPhone} onChange={(e) => setForm({ ...form, primaryContactPhone: e.target.value })} />
                <input placeholder="Email" value={form.primaryContactEmail} onChange={(e) => setForm({ ...form, primaryContactEmail: e.target.value })} />
              </div>
              <input placeholder="Site Address" value={form.siteAddress} onChange={(e) => setForm({ ...form, siteAddress: e.target.value })} />
              <textarea placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={3} />
              <button className="btn-primary" onClick={handleCreate} disabled={createLead.isPending}>
                {createLead.isPending ? "Creating..." : "Create Lead"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
