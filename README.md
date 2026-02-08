# Grayco Lite V3 - KB Signs Shop Management

A high-performance sign shop management tool designed for KB Signs, built with Streamlit and PostgreSQL.

## Overview

Grayco Lite V3 streamlines sign shop operations through a modular architecture, enhancing lead management, client communication, and project tracking. Key capabilities include:

- **Dual-Lane Lead System**: Automated Zapier webhooks and AI-powered Smart Intake
- **Unified Project Workflow**: Projects flow from New → Block A → Design → Pricing → Production → Completion
- **Approval Gates**: All outgoing emails reviewed before sending
- **AI Integration**: Google Gemini for lead extraction, email drafting, and invoice scanning
- **Mobile-First UI**: Dark theme optimized for field use (KB Green #39FF14 on black)

## Features

- **Hot Leads Section**: Quick contact actions that move leads into the project pipeline
- **Daily Action Hub**: Heat-map prioritization with URGENT/ACTIVE/PENDING categories
- **Cold Storage (Archive)**: Archive inactive projects to keep dashboard clean
- **Field Intelligence**: Mobile camera integration with GPS watermarking and photo markup
- **Google Drive Integration**: Automatic folder linking and file management
- **Commission Tracking**: Finance ledger with pay period grouping

## Technical Stack

- **Frontend**: Streamlit
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI**: Google Gemini API (gemini-2.0-flash, gemini-2.5-flash)
- **Email**: SMTP service with test mode
- **File Storage**: Google Drive API
- **Timezone**: All operations use Mountain Time (America/Denver)

## Status Workflow

```
New → Block A → Design → Pricing → Block D → ACTIVE PRODUCTION → Completed
                                          ↓
                                    Cold Storage (Archive)
```

## Environment Variables

Required secrets:
- `GOOGLE_API_KEY` - Google Gemini API
- `SUPABASE_URL` / `SUPABASE_KEY` - Database (if using Supabase)
- `SMTP_SERVER` / `SMTP_EMAIL` / `SMTP_PASSWORD` - Email service
- `SESSION_SECRET` - Session management

## Running Locally

```bash
streamlit run main.py --server.port 5000
```

## License

Proprietary - KB Signs
