"use client";

import { useEffect, useState, useCallback } from "react";
import { api, Document, PaginatedDocuments } from "@/lib/api";
import { Search, ExternalLink, RefreshCw, FileText } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const DOC_TYPES = [
  "Ley", "Decreto", "Resolución", "Circular", "Acuerdo",
  "Sentencia", "Directiva", "Reglamento", "Concepto",
];

export default function DocumentsPage() {
  const [data, setData] = useState<PaginatedDocuments | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [docType, setDocType] = useState("");
  const [days, setDays] = useState("");
  const [onlyNew, setOnlyNew] = useState(false);
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.documents.list({
        page,
        page_size: 25,
        search: search || undefined,
        doc_type: docType || undefined,
        is_new: onlyNew || undefined,
        days: days ? parseInt(days) : undefined,
      });
      setData(result);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, search, docType, onlyNew, days]);

  useEffect(() => { load(); }, [load]);

  const totalPages = data ? Math.ceil(data.total / 25) : 1;

  const handleFilter = () => { setPage(1); load(); };

  return (
    <>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2>Normas y Documentos</h2>
            <p>
              {data ? `${data.total.toLocaleString()} documentos encontrados` : "Cargando..."}
            </p>
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
              placeholder="Buscar por título o número..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleFilter()}
            />
          </div>
          <select
            className="filter-select"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
          >
            <option value="">Todos los tipos</option>
            {DOC_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select
            className="filter-select"
            value={days}
            onChange={(e) => setDays(e.target.value)}
          >
            <option value="">Cualquier fecha</option>
            <option value="1">Hoy</option>
            <option value="7">Últimos 7 días</option>
            <option value="30">Último mes</option>
            <option value="90">Últimos 90 días</option>
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 13, color: "var(--text-secondary)" }}>
            <input
              type="checkbox"
              checked={onlyNew}
              onChange={(e) => setOnlyNew(e.target.checked)}
            />
            Solo nuevos
          </label>
          <button className="btn btn-primary" onClick={handleFilter}>
            <Search size={13} />
            Buscar
          </button>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner" /><p>Buscando normas...</p></div>
        ) : (
          <>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Número</th>
                    <th>Título</th>
                    <th>Entidad</th>
                    <th>Fecha publi.</th>
                    <th>Detectado</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.length === 0 ? (
                    <tr>
                      <td colSpan={7}>
                        <div className="empty-state">
                          <FileText size={32} />
                          <p>No se encontraron documentos con los filtros actuales</p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    data?.items.map((doc) => (
                      <tr key={doc.id}>
                        <td>
                          <span className="chip">{doc.doc_type || "—"}</span>
                        </td>
                        <td className="td-muted" style={{ whiteSpace: "nowrap" }}>
                          {doc.number || "—"}
                        </td>
                        <td style={{ maxWidth: 360 }}>
                          <div style={{ fontWeight: 500, lineHeight: 1.4 }}>
                            {doc.title.slice(0, 100)}
                            {doc.title.length > 100 && "..."}
                          </div>
                          {doc.is_new && (
                            <span className="badge badge-new" style={{ marginTop: 4 }}>Nuevo</span>
                          )}
                        </td>
                        <td>
                          <span className="td-muted" style={{ fontSize: 12 }}>
                            {doc.entity_name || "—"}
                          </span>
                        </td>
                        <td className="td-muted" style={{ whiteSpace: "nowrap" }}>
                          {doc.publication_date
                            ? format(new Date(doc.publication_date), "dd MMM yyyy", { locale: es })
                            : "—"}
                        </td>
                        <td className="td-muted" style={{ whiteSpace: "nowrap", fontSize: 11 }}>
                          {format(new Date(doc.first_seen_at), "dd MMM yyyy HH:mm", { locale: es })}
                        </td>
                        <td>
                          {doc.url && (
                            <a href={doc.url} target="_blank" rel="noopener" className="btn btn-ghost" style={{ padding: "5px 8px" }}>
                              <ExternalLink size={12} />
                            </a>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "16px 0", justifyContent: "center" }}>
                <button
                  className="btn btn-ghost"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  ← Anterior
                </button>
                <span style={{ color: "var(--text-secondary)", fontSize: 13 }}>
                  Página {page} de {totalPages}
                </span>
                <button
                  className="btn btn-ghost"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Siguiente →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
