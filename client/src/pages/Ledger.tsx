import { useLedger } from "../hooks/useProjects";
import { formatCurrency, formatDate } from "../lib/utils";
import { DollarSign } from "lucide-react";

export default function Ledger() {
  const { data: entries, isLoading } = useLedger();

  const totalValue = (entries || []).reduce((sum: number, e: any) => sum + parseFloat(e.projectValue || e.amount || 0), 0);
  const totalCommission = (entries || []).reduce((sum: number, e: any) => {
    const val = parseFloat(e.paymentAmount || e.amount || 0);
    const rate = parseFloat(e.commissionRate || 10) / 100;
    return sum + val * rate;
  }, 0);

  return (
    <div className="page-container">
      <h1 className="page-title">
        <DollarSign size={24} color="var(--accent-green)" style={{ verticalAlign: "middle", marginRight: 8 }} />
        Finance Ledger
      </h1>

      <div className="grid-2 mb-4">
        <div className="card" style={{ textAlign: "center" }}>
          <div className="text-xs text-muted">Total Project Value</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "var(--accent-green)", marginTop: 4 }}>
            {formatCurrency(totalValue)}
          </div>
        </div>
        <div className="card" style={{ textAlign: "center" }}>
          <div className="text-xs text-muted">Total Commission</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "var(--accent-orange)", marginTop: 4 }}>
            {formatCurrency(totalCommission)}
          </div>
        </div>
      </div>

      {isLoading && <div className="loading-spinner" />}

      <div className="flex-col gap-2">
        {(entries || []).map((e: any, i: number) => {
          const val = parseFloat(e.paymentAmount || e.amount || 0);
          const rate = parseFloat(e.commissionRate || 10) / 100;
          const comm = val * rate;
          return (
            <div key={e.id || i} className="card" style={{ padding: "12px 16px" }}>
              <div className="flex-between">
                <div>
                  <div className="font-bold">{e.clientName || e.description || "Payment"}</div>
                  <div className="text-sm text-secondary mt-1">
                    {e.paymentType === "deposit" ? "Deposit" : e.paymentType === "final" ? "Final Payment" : e.entryType || "Payment"}
                  </div>
                  <div className="text-xs text-muted mt-1">{formatDate(e.paymentDate)}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div className="font-bold" style={{ color: "var(--accent-green)" }}>
                    {formatCurrency(val)}
                  </div>
                  <div className="text-xs text-muted">
                    Commission: {formatCurrency(comm)} ({(rate * 100).toFixed(0)}%)
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {!isLoading && (entries || []).length === 0 && (
        <div className="empty-state">
          <DollarSign size={48} />
          <p>No financial entries yet</p>
        </div>
      )}
    </div>
  );
}
