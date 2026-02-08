import { Settings as SettingsIcon, Database, Webhook, Mail } from "lucide-react";

export default function Settings() {
  return (
    <div className="page-container">
      <h1 className="page-title">
        <SettingsIcon size={24} color="var(--text-secondary)" style={{ verticalAlign: "middle", marginRight: 8 }} />
        Settings
      </h1>

      <div className="flex-col gap-3">
        <div className="card" style={{ padding: 20 }}>
          <div className="flex-gap mb-2">
            <Database size={18} color="var(--accent-blue)" />
            <h3>Database</h3>
          </div>
          <p className="text-sm text-secondary">
            Connected to Replit PostgreSQL. All data stored locally for development.
          </p>
        </div>

        <div className="card" style={{ padding: 20 }}>
          <div className="flex-gap mb-2">
            <Webhook size={18} color="var(--accent-orange)" />
            <h3>Webhook Endpoint</h3>
          </div>
          <p className="text-sm text-secondary mb-2">
            Lead receiver webhook for Zapier / Google Chat integration.
          </p>
          <div
            style={{
              background: "var(--bg-input)",
              padding: "8px 12px",
              borderRadius: "var(--radius-sm)",
              fontFamily: "monospace",
              fontSize: 13,
              color: "var(--accent-green)",
            }}
          >
            POST /api/leads
          </div>
          <p className="text-xs text-muted mt-2">
            Accepts JSON: {"{ name, phone, email, notes }"}
          </p>
        </div>

        <div className="card" style={{ padding: 20 }}>
          <div className="flex-gap mb-2">
            <Mail size={18} color="var(--accent-orange)" />
            <h3>Email</h3>
          </div>
          <p className="text-sm text-secondary">
            SMTP email integration for notifications. Configure via environment variables.
          </p>
        </div>

        <div className="card" style={{ padding: 20, opacity: 0.6 }}>
          <h3 className="mb-2">Tenant</h3>
          <p className="text-sm text-secondary">
            Multi-tenant isolation active. All data filtered by tenant ID.
          </p>
        </div>
      </div>
    </div>
  );
}
