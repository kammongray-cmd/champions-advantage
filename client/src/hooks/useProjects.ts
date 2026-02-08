import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useProjects(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["projects", params],
    queryFn: () => api.getProjects(params),
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ["project", id],
    queryFn: () => api.getProject(id),
    enabled: !!id,
  });
}

export function usePipeline() {
  return useQuery({
    queryKey: ["pipeline"],
    queryFn: api.getPipeline,
  });
}

export function useDailySummary() {
  return useQuery({
    queryKey: ["daily-summary"],
    queryFn: api.getDailySummary,
  });
}

export function useLeads() {
  return useQuery({
    queryKey: ["leads"],
    queryFn: api.getLeads,
  });
}

export function useLedger() {
  return useQuery({
    queryKey: ["ledger"],
    queryFn: api.getLedger,
  });
}

export function useProjectHistory(id: string) {
  return useQuery({
    queryKey: ["project-history", id],
    queryFn: () => api.getProjectHistory(id),
    enabled: !!id,
  });
}

export function useAttachments(projectId: string) {
  return useQuery({
    queryKey: ["attachments", projectId],
    queryFn: () => api.getAttachments(projectId),
    enabled: !!projectId,
  });
}

export function useDriveFiles(projectId: string) {
  return useQuery({
    queryKey: ["drive", projectId],
    queryFn: () => api.getDriveFiles(projectId),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => api.createProject(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
      qc.invalidateQueries({ queryKey: ["leads"] });
    },
  });
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.updateProject(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["project"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

export function useConvertLead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.convertLead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

export function useDeleteAttachment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, fileId }: { projectId: string; fileId: string }) =>
      api.deleteAttachment(projectId, fileId),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: ["attachments", projectId] });
    },
  });
}

export function useUpdateAttachment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, fileId, data }: { projectId: string; fileId: string; data: any }) =>
      api.updateAttachment(projectId, fileId, data),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: ["attachments", projectId] });
    },
  });
}
