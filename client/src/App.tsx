import { useState, useEffect } from "react";
import { ToastProvider } from "./components/Toast";
import Layout from "./components/Layout";
import Spotlight from "./components/Spotlight";
import Dashboard from "./pages/Dashboard";
import ProjectsList from "./pages/ProjectsList";
import ProjectDetail from "./pages/ProjectDetail";
import LeadsList from "./pages/LeadsList";
import Ledger from "./pages/Ledger";
import Settings from "./pages/Settings";

export type Page =
  | { name: "dashboard" }
  | { name: "projects" }
  | { name: "project-detail"; id: string }
  | { name: "leads" }
  | { name: "ledger" }
  | { name: "settings" };

export default function App() {
  const [page, setPage] = useState<Page>({ name: "dashboard" });
  const [spotlightOpen, setSpotlightOpen] = useState(false);

  function navigate(p: Page) {
    setPage(p);
    window.scrollTo(0, 0);
  }

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSpotlightOpen(true);
      }
      if (e.key === "n" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
        navigate({ name: "projects" });
      }
      if (e.key === "/" && !e.metaKey && !e.ctrlKey) {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
        e.preventDefault();
        setSpotlightOpen(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  function renderPage() {
    switch (page.name) {
      case "dashboard":
        return <Dashboard onNavigate={navigate} />;
      case "projects":
        return <ProjectsList onNavigate={navigate} />;
      case "project-detail":
        return <ProjectDetail projectId={page.id} onNavigate={navigate} />;
      case "leads":
        return <LeadsList onNavigate={navigate} />;
      case "ledger":
        return <Ledger />;
      case "settings":
        return <Settings />;
      default:
        return <Dashboard onNavigate={navigate} />;
    }
  }

  return (
    <ToastProvider>
      <Layout currentPage={page.name} onNavigate={navigate} onSpotlight={() => setSpotlightOpen(true)}>
        {renderPage()}
      </Layout>
      <Spotlight
        isOpen={spotlightOpen}
        onClose={() => setSpotlightOpen(false)}
        onSelect={(id) => {
          setSpotlightOpen(false);
          navigate({ name: "project-detail", id });
        }}
      />
    </ToastProvider>
  );
}
