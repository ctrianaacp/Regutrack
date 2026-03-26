"use client";

import { useEffect, useState } from "react";
import { api, ScrapeRun } from "@/lib/api";
import { RefreshCw, CheckCircle, XCircle, Loader, Clock } from "lucide-react";
import { format, formatDistanceToNow, differenceInSeconds } from "date-fns";
import { es } from "date-fns/locale";

function fmtDuration(start: string, end: string | null) {
  if (!end) return "en curso";
  const secs = differenceInSeconds(new Date(end), new Date(start));
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function RunStatusIcon({ status }: { status: string }) {
  if (status === "success") return <CheckCircle size={15} style={{ color: "var(--accent-green)" }} />;
  if (status === "failed") return <XCircle size={15} style={{ color: "var(--accent-red)" }} />;
  if (status === "running") return <Loader size={15} style={{ color: "var(--accent-blue)", animation: "spin 1s linear infinite" }} />;
  return <Clock size={15} style={{ color: "var(--text-muted)" }} />;
}

const STATUS_OPTS = ["", "success", "failed", "running", "partial"];

export default function RunsPage() {
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [limit, setLimit] = useState(100);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.runs.list({
        status: status || undefined,
        limit,
      });
      setRuns(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [status, limit]);

  // Stats from runs
  const totalNew = runs.reduce((s, r) => s + r.new_documents, 0);
  const successCount = runs.filter((r) => r.status === "success").length;
  const failedCount = runs.filter((r) => r.status === "failed").length;

  return (
    <>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2>Historial de Ejecuciones</h2>
            <p>Registro detallado de cada scraping ejecutado</p>
          </div>
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} />
            Actualizar
          </button>
        </div>
      </div>

      <div className="page-body">
        {/* Mini summary */}
        <div className="stat-grid" style={{ marginBottom: 20 }}>
          <div className="stat-card green">
            <div className="stat-card-icon"><CheckCircle size={18} /></div>
            <div className="stat-value">{successCount}</div>
            <div className="stat-label">Exitosos</div>
          </div>
          <div className="stat-card red">
            <div className="stat-card-icon"><XCircle size={18} /></div>
            <div className="stat-value">{failedCount}</div>
            <div className="stat-label">Fallidos</div>
          </div>
          <div className="stat-card purple">
            <div className="stat-card-icon"><Clock size={18} /></div>
            <div className="stat-value">{totalNew.toLocaleString()}</div>
            <div className="stat-label">Normas nuevas</div>
            <div className="stat-sub">en este período</div>
          </div>
        </div>

        <div className="filter-bar">
          <select
            className="filter-select"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {STATUS_OPTS.map((s) => (
              <option key={s} value={s}>{s || "Todos los estados"}</option>
            ))}
          </select>
          <select
            className="filter-select"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          >
            <option value={50}>Últimas 50</option>
            <option value={100}>Últimas 100</option>
            <option value={250}>Últimas 250</option>
            <option value={500}>Últimas 500</option>
          </select>
          <span className="chip">{runs.length} registros</span>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner" /><p>Cargando historial...</p></div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Entidad</th>
                  <th>Inicio</th>
                  <th>Duración</th>
                  <th>Estado</th>
                  <th style={{ textAlign: "right" }}>Nuevas</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {runs.length === 0 ? (
                  <tr>
                    <td colSpan={7}>
                      <div className="empty-state">
                        <Clock size={32} />
                        <p>No hay registros de ejecución aún</p>
                        <p style={{ fontSize: 12, marginTop: 4 }}>Ejecuta un scraping desde la página de Entidades</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  runs.map((r) => (
                    <tr key={r.id}>
                      <td><RunStatusIcon status={r.status} /></td>
                      <td style={{ fontWeight: 500, fontSize: 13 }}>
                        {r.entity_name || `Entity #${r.entity_id}`}
                      </td>
                      <td className="td-muted" style={{ whiteSpace: "nowrap", fontSize: 12 }}>
                        <div>{format(new Date(r.started_at), "dd MMM yyyy", { locale: es })}</div>
                        <div>{format(new Date(r.started_at), "HH:mm:ss")}</div>
                      </td>
                      <td className="td-muted" style={{ whiteSpace: "nowrap" }}>
                        {fmtDuration(r.started_at, r.finished_at)}
                      </td>
                      <td>
                        {r.status === "success" && <span className="badge badge-success">Exitoso</span>}
                        {r.status === "failed" && <span className="badge badge-failed">Fallido</span>}
                        {r.status === "running" && <span className="badge badge-running">Corriendo</span>}
                        {r.status === "partial" && <span className="badge badge-never">Parcial</span>}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        {r.new_documents > 0 ? (
                          <span className="badge badge-new">+{r.new_documents}</span>
                        ) : (
                          <span className="td-muted">0</span>
                        )}
                      </td>
                      <td>
                        {r.error_message && (
                          <span
                            className="td-muted"
                            title={r.error_message}
                            style={{ fontSize: 11, cursor: "help", maxWidth: 200, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                          >
                            {r.error_message.slice(0, 60)}...
                          </span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
