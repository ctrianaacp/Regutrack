"use client";

import { useEffect, useState } from "react";
import { api, Entity } from "@/lib/api";
import { RefreshCw, Play, ExternalLink, Search } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

const GROUPS: Record<string, string> = {
  group1_centralizadores: "Centralizadores",
  group2_ministerios: "Ministerios",
  group3_control: "Organismos de Control",
  group4_legislativa: "Legislativa / Judicial",
  group5_agencias: "Agencias Nacionales",
  group6_descentralizadas: "Entidades Descentralizadas",
};


function fmtAgo(dt: string | null) {
  if (!dt) return "Nunca";
  return formatDistanceToNow(new Date(dt), { addSuffix: true, locale: es });
}

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <span className="badge badge-never">Sin ejecutar</span>;
  if (status === "success") return <span className="badge badge-success">✓ Exitoso</span>;
  if (status === "failed") return <span className="badge badge-failed">✗ Fallido</span>;
  if (status === "running") return <span className="badge badge-running">↻ Corriendo</span>;
  return <span className="badge badge-never">{status}</span>;
}

export default function EntitiesPage() {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("all");
  const [triggering, setTriggering] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setEntities(await api.entities.list());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const filtered = entities.filter((e) => {
    const matchGroup = group === "all" || e.group === group;
    const matchSearch = !search || e.name.toLowerCase().includes(search.toLowerCase());
    return matchGroup && matchSearch;
  });

  const handleTrigger = async (entity: Entity) => {
    setTriggering(entity.id);
    try {
      const res = await api.entities.triggerRun(entity.key);
      alert(`✓ ${res.message}`);
      setTimeout(load, 2000);
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setTriggering(null);
    }
  };

  return (
    <>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2>Entidades Monitoreadas</h2>
            <p>Estado de scraping y acceso directo a las fuentes normativas</p>
          </div>
          <button className="btn btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw size={14} />
            Actualizar
          </button>
        </div>
      </div>

      <div className="page-body">
        <div className="filter-bar">
          <div className="search-wrapper">
            <Search size={14} className="search-icon" />
            <input
              className="search-input"
              placeholder="Buscar entidad..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="filter-select"
            value={group}
            onChange={(e) => setGroup(e.target.value)}
          >
            <option value="all">Todos los grupos</option>
            {Object.entries(GROUPS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <span className="chip">{filtered.length} entidades</span>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner" /><p>Cargando entidades...</p></div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Entidad</th>
                  <th>Grupo</th>
                  <th>Última Ejecución</th>
                  <th>Estado</th>
                  <th style={{ textAlign: "right" }}>Normas</th>
                  <th style={{ textAlign: "right" }}>Nuevas Hoy</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{e.name}</div>
                    </td>
                    <td>
                      <span className="chip">{GROUPS[e.group] ?? e.group}</span>
                    </td>
                    <td className="td-muted">{fmtAgo(e.last_run_at)}</td>
                    <td><StatusBadge status={e.last_run_status} /></td>
                    <td style={{ textAlign: "right", fontWeight: 600 }}>
                      {e.total_documents.toLocaleString()}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {e.new_documents_today > 0 ? (
                        <span className="badge badge-new">+{e.new_documents_today}</span>
                      ) : (
                        <span className="td-muted">0</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          className="btn btn-primary"
                          style={{ fontSize: 11, padding: "5px 10px" }}
                          onClick={() => handleTrigger(e)}
                          disabled={triggering === e.id}
                          title="Ejecutar scraping ahora"
                        >
                          <Play size={11} />
                          {triggering === e.id ? "Iniciando..." : "Scrapear"}
                        </button>
                        <a
                          href={e.url}
                          target="_blank"
                          rel="noopener"
                          className="btn btn-ghost"
                          style={{ fontSize: 11, padding: "5px 10px" }}
                          title="Ver fuente oficial"
                        >
                          <ExternalLink size={11} />
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
