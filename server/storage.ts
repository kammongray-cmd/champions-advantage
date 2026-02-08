import { db } from "./db";
import { eq, and, desc, asc, sql, not, inArray } from "drizzle-orm";
import {
  projects, projectHistory, projectTouches, projectPhotos, projectProposals,
  commissions, productionLogistics, contacts, projectAttachments,
} from "../shared/schema";
import crypto from "crypto";

const DEFAULT_TENANT = "357145e4-b5a1-43e3-a9ba-f8e834b38034";

function tenantFilter(tenantId = DEFAULT_TENANT) {
  return eq(projects.tenantId, tenantId);
}

export const storage = {
  async getProjects(filters?: { status?: string; search?: string; includeArchived?: boolean }) {
    const conditions: any[] = [tenantFilter(), eq(projects.isActiveV3, true)];
    if (filters?.status) conditions.push(eq(projects.status, filters.status));
    if (!filters?.includeArchived) {
      conditions.push(
        not(inArray(sql`LOWER(${projects.status})`, ["archived", "closed - won", "closed - lost"]))
      );
    }

    let results = await db
      .select()
      .from(projects)
      .where(and(...conditions))
      .orderBy(desc(projects.lastTouched), desc(projects.createdAt));

    if (filters?.search) {
      const s = filters.search.toLowerCase();
      results = results.filter(
        (p) =>
          (p.clientName || "").toLowerCase().includes(s) ||
          (p.notes || "").toLowerCase().includes(s) ||
          (p.primaryContactName || "").toLowerCase().includes(s)
      );
    }

    return results;
  },

  async getProjectById(id: string) {
    const [project] = await db
      .select()
      .from(projects)
      .where(and(eq(projects.id, id), tenantFilter()));
    return project || null;
  },

  async createProject(data: Partial<typeof projects.$inferInsert>) {
    const [created] = await db
      .insert(projects)
      .values({
        ...data,
        id: crypto.randomUUID(),
        tenantId: DEFAULT_TENANT,
        clientName: data.clientName || "Unknown",
        status: data.status || "New",
        isActiveV3: true,
      } as any)
      .returning();
    return created;
  },

  async updateProject(id: string, data: Partial<typeof projects.$inferInsert>) {
    const [updated] = await db
      .update(projects)
      .set({ ...data, updatedAt: new Date() } as any)
      .where(and(eq(projects.id, id), tenantFilter()))
      .returning();
    return updated;
  },

  async softDeleteProject(id: string) {
    const [updated] = await db
      .update(projects)
      .set({ status: "Archived", updatedAt: new Date() })
      .where(and(eq(projects.id, id), tenantFilter()))
      .returning();
    return updated;
  },

  async getLeads() {
    return db
      .select()
      .from(projects)
      .where(
        and(
          tenantFilter(),
          eq(projects.status, "New"),
          eq(projects.isActiveV3, true)
        )
      )
      .orderBy(desc(projects.createdAt));
  },

  async convertLeadToProject(id: string) {
    return this.updateProject(id, {
      status: "Block A",
      statusUpdatedAt: new Date(),
      lastTouched: new Date(),
    });
  },

  async getPipelineCounts() {
    const all = await db
      .select({ status: projects.status })
      .from(projects)
      .where(
        and(
          tenantFilter(),
          eq(projects.isActiveV3, true),
          not(inArray(sql`LOWER(${projects.status})`, ["archived", "closed - won", "closed - lost"]))
        )
      );

    const counts: Record<string, number> = {};
    for (const p of all) {
      const s = p.status || "New";
      counts[s] = (counts[s] || 0) + 1;
    }

    return {
      total: all.length,
      stages: [
        { label: "Next Action", key: "New", count: counts["New"] || 0, color: "#FF6B35" },
        { label: "Survey", key: "Block A", count: counts["Block A"] || 0, color: "#00A8E8" },
        { label: "Design", key: "Block B", count: counts["Block B"] || 0, color: "#9B59B6" },
        { label: "Proposal", key: "Block C", count: (counts["Block C"] || 0) + (counts["Block D"] || 0), color: "#F7931E" },
        {
          label: "Production",
          key: "ACTIVE PRODUCTION",
          count: counts["ACTIVE PRODUCTION"] || 0,
          color: "#39FF14",
        },
      ],
    };
  },

  async getActionItems() {
    return db
      .select()
      .from(projects)
      .where(
        and(
          tenantFilter(),
          eq(projects.isActiveV3, true),
          eq(projects.pendingAction, true),
          not(inArray(sql`LOWER(${projects.status})`, ["archived", "closed - won", "closed - lost"]))
        )
      )
      .orderBy(asc(projects.actionDueDate), asc(projects.lastTouched));
  },

  async getDailySummary() {
    const actionItems = await this.getActionItems();

    const urgentItems = actionItems.filter((item) => {
      if (!item.actionDueDate) return false;
      const due = new Date(item.actionDueDate);
      const now = new Date();
      const diffMs = due.getTime() - now.getTime();
      const diffDays = diffMs / (1000 * 60 * 60 * 24);
      return diffDays <= 1;
    });

    const activeItems = actionItems.filter((item) => {
      if (!item.actionDueDate) return true;
      const due = new Date(item.actionDueDate);
      const now = new Date();
      const diffMs = due.getTime() - now.getTime();
      const diffDays = diffMs / (1000 * 60 * 60 * 24);
      return diffDays > 1;
    });

    return { actionItems: activeItems, urgentItems, victoryLap: [] };
  },

  async getProjectHistory(projectId: string) {
    return db
      .select()
      .from(projectHistory)
      .where(eq(projectHistory.projectId, projectId))
      .orderBy(desc(projectHistory.createdAt));
  },

  async addProjectHistory(projectId: string, entryType: string, content: string) {
    const [created] = await db
      .insert(projectHistory)
      .values({ projectId, entryType, content })
      .returning();
    return created;
  },

  async getProjectTouches(projectId: string) {
    return db
      .select()
      .from(projectTouches)
      .where(eq(projectTouches.projectId, projectId))
      .orderBy(desc(projectTouches.touchedAt));
  },

  async addProjectTouch(projectId: string, touchType: string, note: string) {
    const [created] = await db
      .insert(projectTouches)
      .values({ projectId, touchType, note })
      .returning();
    return created;
  },

  async updateProjectAction(projectId: string, data: { pendingAction: boolean; actionNote: string; actionDueDate: string | null }) {
    return this.updateProject(projectId, {
      pendingAction: data.pendingAction,
      actionNote: data.actionNote,
      actionDueDate: data.actionDueDate,
      lastTouched: new Date(),
    } as any);
  },

  async clearProjectAction(projectId: string) {
    return this.updateProject(projectId, {
      pendingAction: false,
      actionNote: null,
      actionDueDate: null,
      lastTouched: new Date(),
    } as any);
  },

  async getContacts() {
    return db.select().from(contacts).orderBy(desc(contacts.createdAt));
  },

  async getLedgerEntries() {
    const paid = await db
      .select({
        id: commissions.id,
        clientName: projects.clientName,
        status: projects.status,
        projectValue: commissions.totalValue,
        paymentAmount: commissions.depositAmount,
        commissionRate: projects.commissionRate,
        paymentDate: commissions.depositReceivedDate,
        commissionNotes: commissions.commissionNotes,
        paymentType: sql<string>`'deposit'`,
      })
      .from(commissions)
      .innerJoin(projects, eq(commissions.projectId, projects.id))
      .where(
        and(
          tenantFilter(),
          eq(projects.isActiveV3, true),
          sql`${commissions.depositReceivedDate} IS NOT NULL`
        )
      )
      .orderBy(desc(commissions.depositReceivedDate));

    return paid;
  },

  async getCommission(projectId: string) {
    const [comm] = await db
      .select()
      .from(commissions)
      .where(eq(commissions.projectId, projectId));
    return comm || null;
  },

  async saveCommission(projectId: string, data: Partial<typeof commissions.$inferInsert>) {
    const existing = await this.getCommission(projectId);
    if (existing) {
      const [updated] = await db
        .update(commissions)
        .set({ ...data, updatedAt: new Date() } as any)
        .where(eq(commissions.projectId, projectId))
        .returning();
      return updated;
    }
    const [created] = await db
      .insert(commissions)
      .values({ ...data, projectId } as any)
      .returning();
    return created;
  },

  async getLogistics(projectId: string) {
    const [logistics] = await db
      .select()
      .from(productionLogistics)
      .where(eq(productionLogistics.projectId, projectId));
    return logistics || null;
  },

  async saveLogistics(projectId: string, data: Partial<typeof productionLogistics.$inferInsert>) {
    const existing = await this.getLogistics(projectId);
    if (existing) {
      const [updated] = await db
        .update(productionLogistics)
        .set({ ...data, updatedAt: new Date() } as any)
        .where(eq(productionLogistics.projectId, projectId))
        .returning();
      return updated;
    }
    const [created] = await db
      .insert(productionLogistics)
      .values({ ...data, projectId } as any)
      .returning();
    return created;
  },

  async getAttachments(projectId: string) {
    return db
      .select()
      .from(projectAttachments)
      .where(eq(projectAttachments.projectId, projectId))
      .orderBy(desc(projectAttachments.uploadedAt));
  },

  async createAttachment(data: {
    projectId: string;
    filename: string;
    originalName: string;
    mimeType?: string;
    fileSize?: number;
    category?: string;
    thumbnailPath?: string | null;
  }) {
    const [created] = await db
      .insert(projectAttachments)
      .values(data as any)
      .returning();
    return created;
  },

  async updateAttachment(id: string, data: { category?: string; originalName?: string }) {
    const [updated] = await db
      .update(projectAttachments)
      .set(data as any)
      .where(eq(projectAttachments.id, id))
      .returning();
    return updated;
  },

  async deleteAttachment(id: string) {
    const [deleted] = await db
      .delete(projectAttachments)
      .where(eq(projectAttachments.id, id))
      .returning();
    return deleted;
  },

  async getAttachment(id: string) {
    const [att] = await db
      .select()
      .from(projectAttachments)
      .where(eq(projectAttachments.id, id));
    return att || null;
  },

  async searchAllProjects(query: string) {
    const s = query.toLowerCase();
    const all = await db
      .select()
      .from(projects)
      .where(and(tenantFilter(), eq(projects.isActiveV3, true)));
    return all.filter(
      (p) =>
        (p.clientName || "").toLowerCase().includes(s) ||
        (p.notes || "").toLowerCase().includes(s) ||
        (p.primaryContactName || "").toLowerCase().includes(s) ||
        (p.primaryContactEmail || "").toLowerCase().includes(s) ||
        (p.primaryContactPhone || "").toLowerCase().includes(s) ||
        (p.siteAddress || "").toLowerCase().includes(s)
    ).slice(0, 20);
  },
};
