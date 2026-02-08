import multer from "multer";
import path from "path";
import fs from "fs";
import sharp from "sharp";
import crypto from "crypto";

const UPLOAD_DIR = path.resolve(process.cwd(), "uploads");
const THUMB_DIR = path.resolve(UPLOAD_DIR, "thumbnails");

[UPLOAD_DIR, THUMB_DIR].forEach((dir) => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

const ALLOWED_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/gif",
  "application/pdf",
  "application/postscript",
  "application/illustrator",
  "image/svg+xml",
  "application/vnd.adobe.photoshop",
  "application/octet-stream",
];

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOAD_DIR),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname) || "";
    const safeName = crypto.randomUUID() + ext.toLowerCase();
    cb(null, safeName);
  },
});

export const upload = multer({
  storage,
  limits: { fileSize: 25 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    if (ALLOWED_TYPES.includes(file.mimetype) || file.mimetype.startsWith("image/")) {
      cb(null, true);
    } else {
      cb(null, true);
    }
  },
});

export async function generateThumbnail(filePath: string, filename: string): Promise<string | null> {
  try {
    const ext = path.extname(filename).toLowerCase();
    if (![".jpg", ".jpeg", ".png", ".webp", ".gif"].includes(ext)) return null;

    const thumbName = `thumb_${filename}`;
    const thumbPath = path.join(THUMB_DIR, thumbName);

    await sharp(filePath).resize(300, 300, { fit: "cover", position: "center" }).jpeg({ quality: 80 }).toFile(thumbPath);

    return `/uploads/thumbnails/${thumbName}`;
  } catch (err) {
    console.error("Thumbnail generation failed:", err);
    return null;
  }
}

export function deleteFile(filename: string, thumbnailPath?: string | null) {
  const filePath = path.join(UPLOAD_DIR, filename);
  if (fs.existsSync(filePath)) fs.unlinkSync(filePath);

  if (thumbnailPath) {
    const thumbFull = path.join(process.cwd(), thumbnailPath.replace(/^\//, ""));
    if (fs.existsSync(thumbFull)) fs.unlinkSync(thumbFull);
  }
}
