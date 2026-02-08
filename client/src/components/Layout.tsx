import { Home, FolderKanban, Users, DollarSign, Settings, Search } from "lucide-react";
import type { Page } from "../App";

interface LayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onNavigate: (page: Page) => void;
  onSpotlight?: () => void;
}

const navItems = [
  { name: "dashboard", label: "Home", icon: Home },
  { name: "projects", label: "Projects", icon: FolderKanban },
  { name: "leads", label: "Leads", icon: Users },
  { name: "ledger", label: "Ledger", icon: DollarSign },
  { name: "settings", label: "Settings", icon: Settings },
] as const;

export default function Layout({ children, currentPage, onNavigate, onSpotlight }: LayoutProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <div className="header-brand">
            <span className="brand-logo">KB</span>
            <span className="brand-name">SIGNS</span>
            <div className="brand-divider" />
            <span className="brand-tagline">Sign Shop Suite</span>
          </div>
          <button className="spotlight-trigger" onClick={onSpotlight}>
            <Search size={14} />
            <span>Search</span>
            <kbd>⌘K</kbd>
          </button>
        </div>
      </header>

      <main className="app-main">{children}</main>

      <nav className="app-nav">
        {navItems.map((item) => {
          const isActive =
            currentPage === item.name ||
            (item.name === "projects" && currentPage === "project-detail");
          const Icon = item.icon;
          return (
            <button
              key={item.name}
              className={`nav-item ${isActive ? "nav-active" : ""}`}
              onClick={() => onNavigate({ name: item.name } as Page)}
            >
              <Icon size={20} strokeWidth={isActive ? 2.5 : 1.5} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
