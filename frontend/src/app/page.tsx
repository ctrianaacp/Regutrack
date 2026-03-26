"use client";

import { useEffect, useState } from "react";
import { api, Stats, Document, Entity } from "@/lib/api";
import {
  Building2, FileText, TrendingUp, AlertCircle,
  CheckCircle, Clock, ExternalLink, RefreshCw
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

function fmtAgo(dt: string | null) {
  if (!dt) return "Nunca";
  return formatDistanceToNow(new Date(dt), { addSuffix: true, locale: es });
}

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <span className="badge badge-never">Sin datos</span>;
  if (status === "success") return <span className="badge badge-success">✓ Exitoso</span>;
  if (status === "failed") return <span className="badge badge-failed">✗ Fallido</span>;
  return <span className="badge badge-running">↻ Corriendo</span>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [newDocs, setNewDocs] = useState<Document[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [entityFilter, setEntityFilter] = useState<string>("all");

  const refresh = async () => {
    setLoading(true);
    try {
      const [s, docs, ents] = await Promise.all([
        api.stats(),
        api.documents.getNew(1),
        api.entities.list(),
      ]);
      setStats(s);
      setNewDocs(docs);          // keep all docs — filter derives correct entity list
      setEntities(ents);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  // Unique entity names present in today's new docs
  const entityOptions = Array.from(
    new Set(newDocs.map((d) => d.entity_name).filter((n): n is string => n !== null))
  ).sort();

  // Filtered docs for the Normas Nuevas table
  const filteredDocs = entityFilter === "all"
    ? newDocs
    : newDocs.filter((d) => d.entity_name === entityFilter);

  const STAT_CARDS = stats
    ? [
        {
          label: "Total Entidades",
          value: stats.total_entities,
          sub: `${stats.active_entities} activas`,
          color: "blue",
          icon: Building2,
        },
        {
          label: "Total Normas",
          value: stats.total_documents.toLocaleString(),
          sub: `${stats.new_documents_week} esta semana`,
          color: "purple",
          icon: FileText,
        },
        {
          label: "Nuevas Hoy",
          value: stats.new_documents_today,
          sub: "documentos detectados",
          color: "green",
          icon: TrendingUp,
        },
        {
          label: "Tasa de Éxito",
          value: `${Math.round(stats.success_rate_today * 100)}%`,
          sub: `${stats.failed_runs_today} fallidos hoy`,
          color: stats.success_rate_today >= 0.8 ? "green" : stats.success_rate_today >= 0.5 ? "amber" : "red",
          icon: stats.success_rate_today >= 0.8 ? CheckCircle : AlertCircle,
        },
      ]
    : [];

  return (
    <>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2>Dashboard</h2>
            <p>
              Monitoreo normativo en tiempo real · Colombia
              {stats?.last_run_at && (
                <> · Último scraping: {fmtAgo(stats.last_run_at)}</>
              )}
            </p>
          </div>
          <button className="btn btn-ghost" onClick={refresh} disabled={loading}>
            <RefreshCw size={14} className={loading ? "spinning" : ""} />
            Actualizar
          </button>
        </div>
      </div>

      <div className="page-body">
        {loading && !stats ? (
          <div className="loading"><div className="spinner" /><p>Cargando datos...</p></div>
        ) : (
          <>
            {/* Stat cards */}
            <div className="stat-grid">
              {STAT_CARDS.map((c) => (
                <div key={c.label} className={`stat-card ${c.color}`}>
                  <div className="stat-card-icon">
                    <c.icon size={20} />
                  </div>
                  <div className="stat-value">{c.value}</div>
                  <div className="stat-label">{c.label}</div>
                  <div className="stat-sub">{c.sub}</div>
                  {c.label === "Tasa de Éxito" && stats && (
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${stats.success_rate_today * 100}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="two-col">
              {/* Recent new documents */}
              <div>
                <div className="section-header">
                  <span className="section-title">Normas Nuevas (hoy)</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {entityOptions.length > 0 && (
                      <select
                        value={entityFilter}
                        onChange={(e) => setEntityFilter(e.target.value)}
                        style={{
                          fontSize: 12,
                          padding: "3px 8px",
                          borderRadius: 6,
                          border: "1px solid rgba(255,255,255,0.18)",
                          background: "#1e293b",
                          color: "#e2e8f0",
                          cursor: "pointer",
                          outline: "none",
                        }}
                      >
                        <option value="all">Todas las entidades</option>
                        {entityOptions.map((name) => (
                          <option key={name} value={name}>{name}</option>
                        ))}
                      </select>
                    )}
                    <span className="chip">{filteredDocs.length} docs</span>
                  </div>
                </div>
                <div className="card" style={{ padding: "4px 20px" }}>
                  {filteredDocs.length === 0 ? (
                    <div className="empty-state">
                      <FileText size={32} />
                      <p>{entityFilter === "all" ? "Sin nuevas normas hoy" : `Sin normas de ${entityFilter} hoy`}</p>
                    </div>
                  ) : (
                    filteredDocs.slice(0, 20).map((d) => (
                      <div key={d.id} className="activity-item">
                        <div className="activity-dot new" />
                        <div className="activity-body">
                          <div className="activity-title">
                            {d.url ? (
                              <a href={d.url} target="_blank" rel="noopener" style={{ color: "#a78bfa" }}>
                                {d.title.slice(0, 80)}
                              </a>
                            ) : d.title.slice(0, 80)}
                          </div>
                          <div className="activity-meta">
                            {d.entity_name} · {d.doc_type || "Norma"}
                            {d.number && ` · #${d.number}`}
                          </div>
                        </div>
                        <div className="activity-time">{fmtAgo(d.first_seen_at)}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Entity health grid */}
              <div>
                <div className="section-header">
                  <span className="section-title">Estado Entidades</span>
                  <span className="chip">{entities.length} total</span>
                </div>
                <div className="entity-grid">
                  {entities.map((e) => (
                    <div
                      key={e.id}
                      className={`entity-tile ${
                        e.last_run_status === "success"
                          ? "ok"
                          : e.last_run_status === "failed"
                          ? "fail"
                          : "never"
                      }`}
                    >
                      <div className="entity-tile-name">{e.name}</div>
                      <StatusBadge status={e.last_run_status} />
                      <div className="entity-tile-meta" style={{ marginTop: 6 }}>
                        {e.total_documents} normas
                        {e.new_documents_today > 0 && (
                          <span className="badge badge-new" style={{ marginLeft: 6 }}>
                            +{e.new_documents_today} hoy
                          </span>
                        )}
                      </div>
                      <div className="entity-tile-meta">{fmtAgo(e.last_run_at)}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
