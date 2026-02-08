export function getStatusBadgeClass(status: string): string {
  const s = (status || "").toLowerCase().replace(/\s+/g, "-");
  const map: Record<string, string> = {
    new: "status-new",
    "block-a": "status-block-a",
    "block-b": "status-block-b",
    "block-c": "status-block-c",
    "block-d": "status-block-d",
    "active-production": "status-production",
    "closed---won": "status-won",
    "closed---lost": "status-lost",
    archived: "status-archived",
  };
  return map[s] || "status-block-a";
}

export function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    New: "NEW",
    "Block A": "A",
    "Block B": "B",
    "Block C": "C",
    "Block D": "D",
    "ACTIVE PRODUCTION": "PROD",
    "Closed - Won": "WON",
    "Closed - Lost": "LOST",
    Archived: "ARCH",
    completed: "DONE",
    Confirmed: "CONF",
  };
  return map[status] || (status || "").slice(0, 4).toUpperCase();
}

export function formatCurrency(value: number | string | null): string {
  if (!value) return "$0";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "$0";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 }).format(num);
}

export function formatDate(date: string | null): string {
  if (!date) return "";
  return new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function formatDateTime(date: string | null): string {
  if (!date) return "";
  return new Date(date).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function timeAgo(date: string | null): string {
  if (!date) return "";
  const now = new Date();
  const then = new Date(date);
  const diff = now.getTime() - then.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(date);
}
