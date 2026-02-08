import { usePipeline, useDailySummary, useLeads } from "../hooks/useProjects";
import { getStatusBadgeClass, getStatusLabel, formatCurrency, timeAgo } from "../lib/utils";
import { Flame, Clock, Trophy, ChevronRight, AlertTriangle, Zap } from "lucide-react";
import { SkeletonPipeline, SkeletonCard } from "../components/Skeleton";
import type { Page } from "../App";

interface Props {
  onNavigate: (p: Page) => void;
}

export default function Dashboard({ onNavigate }: Props) {
  const pipeline = usePipeline();
  const summary = useDailySummary();
  const leads = useLeads();

  const pipelineData = pipeline.data || { stages: [], total: 0 };
  const summaryData = summary.data || { actionItems: [], urgentItems: [], victoryLap: [] };
  const hotLeads = leads.data || [];

  return (
    <div className="page-container">
      {pipeline.isLoading ? (
        <SkeletonPipeline />
      ) : (
        <div className="pipeline-grid mb-4">
          {(pipelineData.stages || []).map((stage: any) => (
            <div
              key={stage.label}
              className="pipeline-card"
              style={{ borderTop: `3px solid ${stage.color || "var(--accent-orange)"}` }}
              onClick={() => onNavigate({ name: "projects" })}
            >
              <div className="count" style={{ color: stage.color || "var(--accent-orange)" }}>
                {stage.count}
              </div>
              <div className="label">{stage.label}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: 16,
        padding: "8px 0",
      }}>
        <Zap size={16} color="var(--accent-orange)" />
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
          {pipelineData.total} active projects
        </span>
        <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
          Press <kbd style={{
            background: "var(--bg-card-hover)",
            border: "1px solid var(--border-color)",
            borderRadius: 4,
            padding: "1px 5px",
            fontSize: 10,
          }}>⌘K</kbd> to search
        </span>
      </div>

      {hotLeads.length > 0 && (
        <div className="mb-4">
          <div className="section-header">
            <Flame size={18} color="var(--accent-orange)" />
            <h3>Hot Leads</h3>
            <span className="count-badge">{hotLeads.length}</span>
          </div>
          <div className="flex-col gap-2">
            {hotLeads.map((lead: any) => (
              <div
                key={lead.id}
                className="card card-hover"
                onClick={() => onNavigate({ name: "project-detail", id: lead.id })}
                style={{ padding: "12px 16px" }}
              >
                <div className="flex-between">
                  <div>
                    <span className="font-bold">{lead.clientName || lead.name || "Unknown"}</span>
                    <div className="text-sm text-secondary mt-1">
                      {lead.primaryContactPhone || lead.phone || ""}{" "}
                      {lead.primaryContactEmail || lead.email ? `\u2022 ${lead.primaryContactEmail || lead.email}` : ""}
                    </div>
                  </div>
                  <ChevronRight size={18} color="var(--text-muted)" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {summary.isLoading ? (
        <div className="flex-col gap-2 mb-4">
          <SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      ) : (
        <>
          {(summaryData.urgentItems || []).length > 0 && (
            <div className="mb-4">
              <div className="section-header">
                <AlertTriangle size={18} color="var(--accent-red)" />
                <h3 style={{ color: "var(--accent-red)" }}>Urgent</h3>
                <span className="count-badge">{summaryData.urgentItems.length}</span>
              </div>
              <div className="flex-col gap-2">
                {summaryData.urgentItems.map((item: any) => (
                  <div
                    key={item.id}
                    className="card card-hover"
                    onClick={() => onNavigate({ name: "project-detail", id: item.id })}
                    style={{
                      padding: "12px 16px",
                      borderLeft: "3px solid var(--accent-red)",
                    }}
                  >
                    <div className="flex-between">
                      <div>
                        <span className="font-bold">{item.clientName}</span>
                        {item.actionNote && (
                          <div className="text-sm text-secondary mt-1">{item.actionNote}</div>
                        )}
                      </div>
                      <div className="flex-gap">
                        <span className={`status-badge ${getStatusBadgeClass(item.status)}`}>
                          {getStatusLabel(item.status)}
                        </span>
                        <ChevronRight size={18} color="var(--text-muted)" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(summaryData.actionItems || []).length > 0 && (
            <div className="mb-4">
              <div className="section-header">
                <Clock size={18} color="var(--accent-yellow)" />
                <h3>Marching Orders</h3>
                <span className="count-badge">{summaryData.actionItems.length}</span>
              </div>
              <div className="flex-col gap-2">
                {summaryData.actionItems.map((item: any) => (
                  <div
                    key={item.id}
                    className="card card-hover"
                    onClick={() => onNavigate({ name: "project-detail", id: item.id })}
                    style={{ padding: "12px 16px" }}
                  >
                    <div className="flex-between">
                      <div>
                        <div className="flex-gap">
                          <span className={`status-badge ${getStatusBadgeClass(item.status)}`}>
                            {getStatusLabel(item.status)}
                          </span>
                          <span className="font-bold">{item.clientName}</span>
                        </div>
                        {item.actionNote && (
                          <div className="text-sm text-secondary mt-1">{item.actionNote}</div>
                        )}
                        {item.actionDueDate && (
                          <div className="text-xs text-muted mt-1">
                            Due: {new Date(item.actionDueDate).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                      <div className="flex-gap">
                        {item.estimatedValue && (
                          <span className="text-sm" style={{ color: "var(--accent-green)" }}>
                            {formatCurrency(item.estimatedValue)}
                          </span>
                        )}
                        <ChevronRight size={18} color="var(--text-muted)" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(summaryData.victoryLap || []).length > 0 && (
            <div className="mb-4">
              <div className="section-header">
                <Trophy size={18} color="var(--accent-green)" />
                <h3 style={{ color: "var(--accent-green)" }}>Victory Lap</h3>
              </div>
              <div className="flex-col gap-2">
                {summaryData.victoryLap.map((item: any) => (
                  <div
                    key={item.id}
                    className="card card-hover"
                    onClick={() => onNavigate({ name: "project-detail", id: item.id })}
                    style={{
                      padding: "12px 16px",
                      borderLeft: "3px solid var(--accent-green)",
                    }}
                  >
                    <span className="font-bold">{item.clientName}</span>
                    <div className="text-sm text-secondary mt-1">Installed \u2014 send thank you!</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {!pipeline.isLoading &&
        hotLeads.length === 0 &&
        (summaryData.actionItems || []).length === 0 &&
        (summaryData.urgentItems || []).length === 0 && (
          <div className="empty-state">
            <Trophy size={48} />
            <p>All clear! No pending actions.</p>
          </div>
        )}
    </div>
  );
}
