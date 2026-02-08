import { Router, type Request, type Response } from "express";
import { storage } from "./storage";
import { upload, generateThumbnail, deleteFile } from "./upload";
import { listDriveFolder } from "./drive";
import path from "path";

export const router = Router();

router.get("/projects", async (req: Request, res: Response) => {
  try {
    const { status, search, includeArchived } = req.query;
    const projects = await storage.getProjects({
      status: status as string | undefined,
      search: search as string | undefined,
      includeArchived: includeArchived === "true",
    });
    res.json(projects);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/projects/:id", async (req: Request, res: Response) => {
  try {
    const project = await storage.getProjectById(req.params.id);
    if (!project) return res.status(404).json({ message: "Project not found" });
    res.json(project);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/projects", async (req: Request, res: Response) => {
  try {
    const project = await storage.createProject(req.body);
    await storage.addProjectHistory(project.id, "CREATED", `Project created: ${project.clientName}`);
    res.status(201).json(project);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.put("/projects/:id", async (req: Request, res: Response) => {
  try {
    const existing = await storage.getProjectById(req.params.id);
    if (!existing) return res.status(404).json({ message: "Project not found" });

    const updated = await storage.updateProject(req.params.id, req.body);

    if (req.body.status && req.body.status !== existing.status) {
      await storage.addProjectHistory(
        req.params.id,
        "STATUS_CHANGE",
        `Status changed: ${existing.status} → ${req.body.status}`
      );
    }

    res.json(updated);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.delete("/projects/:id", async (req: Request, res: Response) => {
  try {
    const updated = await storage.softDeleteProject(req.params.id);
    if (!updated) return res.status(404).json({ message: "Project not found" });
    await storage.addProjectHistory(req.params.id, "DELETED", "Project soft-deleted");
    res.json({ message: "Project deleted", project: updated });
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/leads", async (_req: Request, res: Response) => {
  try {
    const leads = await storage.getLeads();
    res.json(leads);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/leads/:id", async (req: Request, res: Response) => {
  try {
    const project = await storage.getProjectById(req.params.id);
    if (!project) return res.status(404).json({ message: "Lead not found" });
    res.json(project);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/leads", async (req: Request, res: Response) => {
  try {
    const { name, phone, email, notes, client_name, phone_number, message, details } = req.body;

    const leadName = name || client_name || "";
    const leadPhone = phone || phone_number || "";
    const leadEmail = email || "";
    const leadNotes = notes || message || details || "";

    if (!leadName && !leadPhone && !leadEmail) {
      return res.status(400).json({ message: "No lead data provided" });
    }

    const project = await storage.createProject({
      clientName: leadName || "Unknown",
      status: "New",
      notes: leadNotes,
      source: req.body.source || "webhook",
      primaryContactName: leadName || undefined,
      primaryContactPhone: leadPhone || undefined,
      primaryContactEmail: leadEmail || undefined,
      siteAddress: req.body.site_address || req.body.siteAddress || undefined,
    });

    await storage.addProjectHistory(project.id, "CREATED", `Lead received via ${req.body.source || "webhook"}: ${leadName}`);

    res.status(201).json({ status: "success", message: `Lead created: ${leadName}`, project });
  } catch (err: any) {
    res.status(500).json({ status: "error", message: err.message });
  }
});

router.put("/leads/:id", async (req: Request, res: Response) => {
  try {
    const updated = await storage.updateProject(req.params.id, req.body);
    if (!updated) return res.status(404).json({ message: "Lead not found" });
    res.json(updated);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/leads/:id/convert", async (req: Request, res: Response) => {
  try {
    const converted = await storage.convertLeadToProject(req.params.id);
    if (!converted) return res.status(404).json({ message: "Lead not found" });
    await storage.addProjectHistory(req.params.id, "STATUS_CHANGE", "Lead promoted to Block A (Survey)");
    res.json({ message: "Lead converted to project", project: converted });
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/pipeline", async (_req: Request, res: Response) => {
  try {
    const pipeline = await storage.getPipelineCounts();
    res.json(pipeline);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/daily-summary", async (_req: Request, res: Response) => {
  try {
    const summary = await storage.getDailySummary();
    res.json(summary);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/contacts", async (_req: Request, res: Response) => {
  try {
    const allContacts = await storage.getContacts();
    res.json(allContacts);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/ledger", async (_req: Request, res: Response) => {
  try {
    const entries = await storage.getLedgerEntries();
    res.json(entries);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/ledger", async (req: Request, res: Response) => {
  try {
    const entry = await storage.createLedgerEntry(req.body);
    res.status(201).json(entry);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/projects/:id/history", async (req: Request, res: Response) => {
  try {
    const history = await storage.getProjectHistory(req.params.id);
    res.json(history);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/projects/:id/history", async (req: Request, res: Response) => {
  try {
    const { entryType, content } = req.body;
    const entry = await storage.addProjectHistory(req.params.id, entryType, content);
    res.status(201).json(entry);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/projects/:id/touches", async (req: Request, res: Response) => {
  try {
    const touches = await storage.getProjectTouches(req.params.id);
    res.json(touches);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/projects/:id/touches", async (req: Request, res: Response) => {
  try {
    const { touchType, note } = req.body;
    const touch = await storage.addProjectTouch(req.params.id, touchType, note);

    const project = await storage.getProjectById(req.params.id);
    if (project && project.status === "New") {
      await storage.updateProject(req.params.id, { status: "Block A", statusUpdatedAt: new Date() });
      await storage.addProjectHistory(req.params.id, "STATUS_CHANGE", "Status auto-changed: New → Block A (contact made)");
    }

    res.status(201).json(touch);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.put("/projects/:id/action", async (req: Request, res: Response) => {
  try {
    const updated = await storage.updateProjectAction(req.params.id, req.body);
    res.json(updated);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.delete("/projects/:id/action", async (req: Request, res: Response) => {
  try {
    const updated = await storage.clearProjectAction(req.params.id);
    await storage.addProjectHistory(req.params.id, "ACTION_DONE", "Action item completed");
    res.json(updated);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/projects/:id/commission", async (req: Request, res: Response) => {
  try {
    const comm = await storage.getCommission(req.params.id);
    res.json(comm || {});
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/projects/:id/commission", async (req: Request, res: Response) => {
  try {
    const comm = await storage.saveCommission(req.params.id, req.body);
    res.json(comm);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/projects/:id/logistics", async (req: Request, res: Response) => {
  try {
    const logistics = await storage.getLogistics(req.params.id);
    res.json(logistics || {});
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/projects/:id/logistics", async (req: Request, res: Response) => {
  try {
    const logistics = await storage.saveLogistics(req.params.id, req.body);
    res.json(logistics);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/projects/:id/attachments", async (req: Request, res: Response) => {
  try {
    const attachments = await storage.getAttachments(req.params.id);
    res.json(attachments);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.post("/projects/:id/attachments", upload.array("files", 10), async (req: Request, res: Response) => {
  try {
    const files = req.files as Express.Multer.File[];
    if (!files || files.length === 0) {
      return res.status(400).json({ message: "No files uploaded" });
    }

    const category = req.body.category || "Other";
    const results = [];

    for (const file of files) {
      const thumbnailPath = await generateThumbnail(file.path, file.filename);
      const attachment = await storage.createAttachment({
        projectId: req.params.id,
        filename: file.filename,
        originalName: file.originalname,
        mimeType: file.mimetype,
        fileSize: file.size,
        category,
        thumbnailPath,
      });
      results.push(attachment);
    }

    await storage.addProjectHistory(
      req.params.id,
      "FILE_UPLOAD",
      `${files.length} file(s) uploaded: ${files.map((f) => f.originalname).join(", ")}`
    );

    res.status(201).json(results);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.put("/projects/:id/attachments/:fileId", async (req: Request, res: Response) => {
  try {
    const updated = await storage.updateAttachment(req.params.fileId, req.body);
    if (!updated) return res.status(404).json({ message: "Attachment not found" });
    res.json(updated);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.delete("/projects/:id/attachments/:fileId", async (req: Request, res: Response) => {
  try {
    const attachment = await storage.getAttachment(req.params.fileId);
    if (!attachment) return res.status(404).json({ message: "Attachment not found" });

    deleteFile(attachment.filename, attachment.thumbnailPath);
    await storage.deleteAttachment(req.params.fileId);

    await storage.addProjectHistory(
      req.params.id,
      "FILE_DELETE",
      `File deleted: ${attachment.originalName}`
    );

    res.json({ message: "Attachment deleted" });
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/projects/:id/drive", async (req: Request, res: Response) => {
  try {
    const project = await storage.getProjectById(req.params.id);
    if (!project) return res.status(404).json({ message: "Project not found" });

    const folderId = project.googleDriveFolderId;
    if (!folderId) {
      return res.json({ linked: false, folderId: null, files: [], driveLink: project.googleDriveLink });
    }

    const files = await listDriveFolder(folderId);
    return res.json({
      linked: true,
      folderId,
      driveLink: project.googleDriveLink || `https://drive.google.com/drive/folders/${folderId}`,
      files,
    });
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.put("/projects/:id/drive", async (req: Request, res: Response) => {
  try {
    const { folderId, driveLink } = req.body;
    const updated = await storage.updateProject(req.params.id, {
      googleDriveFolderId: folderId || null,
      googleDriveLink: driveLink || null,
    } as any);
    res.json(updated);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});

router.get("/search", async (req: Request, res: Response) => {
  try {
    const q = (req.query.q as string) || "";
    if (!q || q.length < 2) return res.json([]);
    const results = await storage.searchAllProjects(q);
    res.json(results);
  } catch (err: any) {
    res.status(500).json({ message: err.message });
  }
});
