const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getProjects: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<any[]>(`/projects${qs}`);
  },
  getProject: (id: string) => request<any>(`/projects/${id}`),
  createProject: (data: any) => request<any>("/projects", { method: "POST", body: JSON.stringify(data) }),
  updateProject: (id: string, data: any) =>
    request<any>(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProject: (id: string) => request<any>(`/projects/${id}`, { method: "DELETE" }),

  getLeads: () => request<any[]>("/leads"),
  getLead: (id: string) => request<any>(`/leads/${id}`),
  createLead: (data: any) => request<any>("/leads", { method: "POST", body: JSON.stringify(data) }),
  updateLead: (id: string, data: any) =>
    request<any>(`/leads/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  convertLead: (id: string) => request<any>(`/leads/${id}/convert`, { method: "POST" }),

  getPipeline: () => request<any>("/pipeline"),
  getDailySummary: () => request<any>("/daily-summary"),
  getContacts: () => request<any[]>("/contacts"),

  getLedger: () => request<any[]>("/ledger"),
  createLedgerEntry: (data: any) =>
    request<any>("/ledger", { method: "POST", body: JSON.stringify(data) }),

  getProjectHistory: (id: string) => request<any[]>(`/projects/${id}/history`),
  addProjectHistory: (id: string, data: any) =>
    request<any>(`/projects/${id}/history`, { method: "POST", body: JSON.stringify(data) }),

  getProjectTouches: (id: string) => request<any[]>(`/projects/${id}/touches`),
  addProjectTouch: (id: string, data: any) =>
    request<any>(`/projects/${id}/touches`, { method: "POST", body: JSON.stringify(data) }),

  updateProjectAction: (id: string, data: any) =>
    request<any>(`/projects/${id}/action`, { method: "PUT", body: JSON.stringify(data) }),
  clearProjectAction: (id: string) =>
    request<any>(`/projects/${id}/action`, { method: "DELETE" }),

  getCommission: (id: string) => request<any>(`/projects/${id}/commission`),
  saveCommission: (id: string, data: any) =>
    request<any>(`/projects/${id}/commission`, { method: "POST", body: JSON.stringify(data) }),

  getLogistics: (id: string) => request<any>(`/projects/${id}/logistics`),
  saveLogistics: (id: string, data: any) =>
    request<any>(`/projects/${id}/logistics`, { method: "POST", body: JSON.stringify(data) }),

  getAttachments: (id: string) => request<any[]>(`/projects/${id}/attachments`),
  uploadAttachments: async (id: string, files: File[], category: string) => {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    formData.append("category", category);
    const res = await fetch(`${BASE}/projects/${id}/attachments`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: res.statusText }));
      throw new Error(err.message || "Upload failed");
    }
    return res.json();
  },
  updateAttachment: (projectId: string, fileId: string, data: any) =>
    request<any>(`/projects/${projectId}/attachments/${fileId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAttachment: (projectId: string, fileId: string) =>
    request<any>(`/projects/${projectId}/attachments/${fileId}`, { method: "DELETE" }),

  getDriveFiles: (id: string) => request<any>(`/projects/${id}/drive`),
  linkDriveFolder: (id: string, data: any) =>
    request<any>(`/projects/${id}/drive`, { method: "PUT", body: JSON.stringify(data) }),

  search: (q: string) => request<any[]>(`/search?q=${encodeURIComponent(q)}`),
};
