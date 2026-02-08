import {
  pgTable,
  uuid,
  varchar,
  text,
  boolean,
  timestamp,
  numeric,
  integer,
  serial,
  date,
  jsonb,
  index,
  customType,
} from "drizzle-orm/pg-core";
import { relations, sql } from "drizzle-orm";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";

export const projects = pgTable(
  "projects",
  {
    id: uuid("id").defaultRandom().primaryKey(),
    tenantId: uuid("tenant_id").notNull(),
    clientName: varchar("client_name", { length: 255 }).notNull(),
    status: varchar("status", { length: 50 }).notNull().default("New"),
    googleDriveLink: text("google_drive_link"),
    notes: text("notes"),
    source: varchar("source", { length: 50 }),
    createdAt: timestamp("created_at").defaultNow(),
    updatedAt: timestamp("updated_at").defaultNow(),
    visualizerSettings: jsonb("visualizer_settings").default({}),
    googleDriveFolderId: varchar("google_drive_folder_id", { length: 100 }),
    estimatedValue: numeric("estimated_value"),
    lastTouched: timestamp("last_touched"),
    logoUrl: text("logo_url"),
    isParked: boolean("is_parked").default(false),
    parkingType: varchar("parking_type", { length: 50 }),
    followUpDate: date("follow_up_date"),
    parkedReason: text("parked_reason"),
    originalStatus: varchar("original_status", { length: 50 }),
    parkedAt: timestamp("parked_at"),
    isActiveV3: boolean("is_active_v3").default(false),
    dateApplied: date("date_applied"),
    permitNumber: varchar("permit_number", { length: 100 }),
    permitOfficePhone: varchar("permit_office_phone", { length: 50 }),
    siteAddress: text("site_address"),
    commissionRate: numeric("commission_rate").default("10.0"),
    paidStatus: varchar("paid_status", { length: 50 }).default("unpaid"),
    designProofDriveId: varchar("design_proof_drive_id", { length: 255 }),
    designProofName: varchar("design_proof_name", { length: 255 }),
    proposalDriveId: varchar("proposal_drive_id", { length: 255 }),
    proposalName: varchar("proposal_name", { length: 255 }),
    noDesignRequired: boolean("no_design_required").default(false),
    depositInvoiceRequested: boolean("deposit_invoice_requested").default(false),
    depositInvoiceSent: boolean("deposit_invoice_sent").default(false),
    depositReceivedDate: date("deposit_received_date"),
    depositAmount: numeric("deposit_amount"),
    valueSource: varchar("value_source", { length: 20 }).default("estimated"),
    pendingAction: boolean("pending_action").default(false),
    actionNote: text("action_note"),
    actionDueDate: date("action_due_date"),
    statusUpdatedAt: timestamp("status_updated_at").default(sql`now()`),
    snoozeUntil: timestamp("snooze_until"),
    primaryContactName: varchar("primary_contact_name", { length: 255 }),
    primaryContactPhone: varchar("primary_contact_phone", { length: 50 }),
    primaryContactEmail: varchar("primary_contact_email", { length: 255 }),
    secondaryContactName: varchar("secondary_contact_name", { length: 255 }),
    secondaryContactPhone: varchar("secondary_contact_phone", { length: 50 }),
    secondaryContactEmail: varchar("secondary_contact_email", { length: 255 }),
    masterSpecFileId: varchar("master_spec_file_id", { length: 255 }),
    masterSpecFileName: varchar("master_spec_file_name", { length: 255 }),
    masterSpecLockedAt: timestamp("master_spec_locked_at"),
    productionLocked: boolean("production_locked").default(false),
    signedSpecFileId: varchar("signed_spec_file_id", { length: 255 }),
    signedSpecFileName: varchar("signed_spec_file_name", { length: 255 }),
  },
  (table) => [
    index("idx_projects_tenant_status").on(table.tenantId, table.status),
  ]
);

export const projectHistory = pgTable(
  "project_history",
  {
    id: serial("id").primaryKey(),
    projectId: uuid("project_id").notNull(),
    entryType: varchar("entry_type"),
    content: text("content"),
    createdAt: timestamp("created_at").default(sql`now()`),
  }
);

export const projectTouches = pgTable(
  "project_touches",
  {
    id: uuid("id").default(sql`gen_random_uuid()`).primaryKey(),
    projectId: uuid("project_id").notNull(),
    touchType: varchar("touch_type"),
    note: text("note"),
    touchedAt: timestamp("touched_at").default(sql`CURRENT_TIMESTAMP`),
    createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
  }
);

export const projectPhotos = pgTable(
  "project_photos",
  {
    id: uuid("id").default(sql`gen_random_uuid()`).primaryKey(),
    projectId: uuid("project_id").notNull(),
    filename: varchar("filename"),
    photoType: varchar("photo_type").default("markup"),
    createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
  }
);

export const projectProposals = pgTable(
  "project_proposals",
  {
    id: uuid("id").default(sql`gen_random_uuid()`).primaryKey(),
    projectId: uuid("project_id").notNull(),
    fileName: varchar("file_name"),
    filePath: varchar("file_path"),
    isPrimary: boolean("is_primary").default(false),
    scannedTotal: numeric("scanned_total"),
    scannedDeposit: numeric("scanned_deposit"),
    scanNotes: text("scan_notes"),
    uploadedAt: timestamp("uploaded_at").default(sql`now()`),
    createdAt: timestamp("created_at").default(sql`now()`),
  }
);

export const commissions = pgTable("commissions", {
  id: uuid("id").default(sql`gen_random_uuid()`).primaryKey(),
  projectId: uuid("project_id").notNull().unique(),
  totalValue: numeric("total_value"),
  depositAmount: numeric("deposit_amount"),
  depositReceivedDate: date("deposit_received_date"),
  commissionNotes: text("commission_notes"),
  createdAt: timestamp("created_at").default(sql`now()`),
  updatedAt: timestamp("updated_at").default(sql`now()`),
  finalPaymentDate: date("final_payment_date"),
  totalAmountReceived: numeric("total_amount_received"),
});

export const productionLogistics = pgTable("production_logistics", {
  id: uuid("id").default(sql`gen_random_uuid()`).primaryKey(),
  projectId: uuid("project_id").notNull().unique(),
  targetInstallationDate: date("target_installation_date"),
  productionStatus: varchar("production_status").default("waiting"),
  paintSamplesApproved: boolean("paint_samples_approved").default(false),
  siteMeasurementsVerified: boolean("site_measurements_verified").default(false),
  createdAt: timestamp("created_at").default(sql`now()`),
  updatedAt: timestamp("updated_at").default(sql`now()`),
});

export const projectAttachments = pgTable(
  "project_attachments",
  {
    id: uuid("id").default(sql`gen_random_uuid()`).primaryKey(),
    projectId: uuid("project_id").notNull(),
    filename: varchar("filename", { length: 500 }).notNull(),
    originalName: varchar("original_name", { length: 500 }).notNull(),
    mimeType: varchar("mime_type", { length: 100 }),
    fileSize: integer("file_size"),
    category: varchar("category", { length: 50 }).default("Other"),
    thumbnailPath: varchar("thumbnail_path", { length: 500 }),
    uploadedAt: timestamp("uploaded_at").default(sql`now()`),
  },
  (table) => [
    index("idx_attachments_project").on(table.projectId),
  ]
);

export const contacts = pgTable(
  "contacts",
  {
    id: uuid("id").default(sql`gen_random_uuid()`).primaryKey(),
    projectId: uuid("project_id").notNull(),
    isPrimary: boolean("is_primary"),
    name: varchar("name"),
    phone: varchar("phone"),
    email: varchar("email"),
    title: varchar("title"),
    notes: text("notes"),
    createdAt: timestamp("created_at"),
    updatedAt: timestamp("updated_at"),
  }
);

export const projectsRelations = relations(projects, ({ many, one }) => ({
  history: many(projectHistory),
  touches: many(projectTouches),
  photos: many(projectPhotos),
  proposals: many(projectProposals),
  attachments: many(projectAttachments),
  commission: one(commissions, { fields: [projects.id], references: [commissions.projectId] }),
  logistics: one(productionLogistics, { fields: [projects.id], references: [productionLogistics.projectId] }),
  contactsList: many(contacts),
}));

export const projectAttachmentsRelations = relations(projectAttachments, ({ one }) => ({
  project: one(projects, { fields: [projectAttachments.projectId], references: [projects.id] }),
}));

export const projectHistoryRelations = relations(projectHistory, ({ one }) => ({
  project: one(projects, { fields: [projectHistory.projectId], references: [projects.id] }),
}));

export const projectTouchesRelations = relations(projectTouches, ({ one }) => ({
  project: one(projects, { fields: [projectTouches.projectId], references: [projects.id] }),
}));

export const projectPhotosRelations = relations(projectPhotos, ({ one }) => ({
  project: one(projects, { fields: [projectPhotos.projectId], references: [projects.id] }),
}));

export const projectProposalsRelations = relations(projectProposals, ({ one }) => ({
  project: one(projects, { fields: [projectProposals.projectId], references: [projects.id] }),
}));

export const commissionsRelations = relations(commissions, ({ one }) => ({
  project: one(projects, { fields: [commissions.projectId], references: [projects.id] }),
}));

export const productionLogisticsRelations = relations(productionLogistics, ({ one }) => ({
  project: one(projects, { fields: [productionLogistics.projectId], references: [projects.id] }),
}));

export const contactsRelations = relations(contacts, ({ one }) => ({
  project: one(projects, { fields: [contacts.projectId], references: [projects.id] }),
}));

export type Project = typeof projects.$inferSelect;
export type InsertProject = typeof projects.$inferInsert;
export type ProjectHistory = typeof projectHistory.$inferSelect;
export type ProjectTouch = typeof projectTouches.$inferSelect;
export type ProjectPhoto = typeof projectPhotos.$inferSelect;
export type ProjectProposal = typeof projectProposals.$inferSelect;
export type Commission = typeof commissions.$inferSelect;
export type ProductionLogistic = typeof productionLogistics.$inferSelect;
export type Contact = typeof contacts.$inferSelect;
export type ProjectAttachment = typeof projectAttachments.$inferSelect;
