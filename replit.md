# Sign Shop Suite CRM

## Overview
Sign Shop Suite is a CRM and project management tool designed for KB Signs. Rebuilt from Streamlit/Python to React + Express/TypeScript with Drizzle ORM and PostgreSQL. Features a 5-stage pipeline, file attachment system, Google Drive integration, and a polished dark-theme UI.

## Architecture (React + Express rebuild - Feb 2026)
- **Stack**: React 19, Express 5, TypeScript, Drizzle ORM, PostgreSQL, TanStack Query
- **Frontend**: Vite-built React SPA served as static files from Express
- **Backend**: Express API on port 5000 (launched via main.py process replacement)
- **Database**: Replit PostgreSQL (Neon-backed), accessed via Drizzle ORM
- **Workflow**: `streamlit run main.py --server.port 5000` (main.py uses os.execvp to replace with Express)

### Directory Structure
- `/server` - Express backend (index.ts, routes.ts, storage.ts, db.ts, upload.ts, drive.ts, seed.ts)
- `/client/src` - React frontend (pages/, components/, hooks/, lib/)
- `/shared` - Shared schema (schema.ts with Drizzle table definitions)
- `/uploads` - File uploads storage (with /thumbnails subdirectory)
- `/dist/public` - Built React app (served by Express static middleware)

### Key Technical Decisions
- **Process Replacement**: main.py can't be changed; it uses `os.execvp("npx", ["npx", "tsx", "server/index.ts"])` to replace Streamlit process with Express
- **Express v5**: Uses `/{*splat}` syntax for catch-all routes instead of `*`
- **UUID Generation**: projects table lacks default UUID, so createProject explicitly generates UUIDs via `crypto.randomUUID()`
- **WebSocket Mock**: Express intercepts Streamlit client reconnection attempts at `/_stcore/stream`
- **File Uploads**: Multer handles multipart uploads, Sharp generates thumbnails for images
- **Google Drive**: Uses Replit's Google Drive connection (connector) for OAuth token management

### Database Tables
- projects, project_history, project_touches, project_photos, project_proposals
- commissions, production_logistics, contacts
- project_attachments (new - for file upload system)
- Multi-tenant: all queries filtered by tenant_id

### Features Implemented
1. **Dashboard**: 5-block pipeline visualization, Hot Leads, Urgent items, Marching Orders, Victory Lap
2. **Project Detail**: Hero banner, photo gallery, file management with drag-drop upload, categorized attachments, timeline view, status management, action items, production lockdown
3. **File System**: Upload files with categories (Design Mockup, Customer Photo, Proposal, Production File, Permit, Other), auto-thumbnails, lightbox preview, download, delete
4. **Google Drive**: Link Drive folders to projects, view Drive contents inline
5. **Hot Leads**: Lead intake via webhook (POST /api/leads), manual creation, promote to Block A
6. **Finance Ledger**: Commission tracking with deposit/final payment entries
7. **Spotlight Search**: Cmd+K to search all projects instantly
8. **Toast Notifications**: Success/error/info toasts for all actions
9. **Loading Skeletons**: Shimmer loading states instead of spinners
10. **Keyboard Shortcuts**: Cmd+K (search), / (search), N (projects)

## User Preferences
- Prefers dark theme with professional polish ("$10,000 custom build" feel)
- Wants the app to feel alive with smooth transitions and animations
- Mobile experience should feel native
- No changes to .streamlit/config.toml
- Direct communication, ask before major changes

## External Dependencies
- PostgreSQL (Replit built-in)
- Google Drive API (via Replit connector)
- Sharp (image thumbnail generation)
- Multer (file upload handling)
