/**
 * API client — all calls go through Next.js rewrites to FastAPI.
 * In dev: /api/* → http://localhost:8000/api/*
 */

const BASE = typeof window !== "undefined" ? "" : (process.env.NEXT_PUBLIC_API_URL || "");

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────────

export interface Stats {
  total_entities: number;
  active_entities: number;
  total_documents: number;
  new_documents_today: number;
  new_documents_week: number;
  total_runs: number;
  successful_runs_today: number;
  failed_runs_today: number;
  success_rate_today: number;
  last_run_at: string | null;
}

export interface Entity {
  id: number;
  key: string;            // Exact key for POST /api/run/{key}
  name: string;
  group: string;
  url: string;
  scraper_class: string;
  is_active: boolean;
  created_at: string;
  last_run_at: string | null;
  last_run_status: string | null;
  total_documents: number;
  new_documents_today: number;
}

export interface Document {
  id: number;
  entity_id: number;
  entity_name: string | null;
  title: string;
  doc_type: string | null;
  number: string | null;
  publication_date: string | null;
  url: string | null;
  raw_summary: string | null;
  is_new: boolean;
  first_seen_at: string;
  last_seen_at: string;
}

export interface PaginatedDocuments {
  total: number;
  page: number;
  page_size: number;
  items: Document[];
}

export interface ScrapeRun {
  id: number;
  entity_id: number;
  entity_name: string | null;
  started_at: string;
  finished_at: string | null;
  status: string;
  new_documents: number;
  error_message: string | null;
}

export interface TriggerRunResponse {
  entity_key: string;
  entity_name: string;
  message: string;
}

// ── API calls ──────────────────────────────────────────────────────

export const api = {
  stats: () => apiFetch<Stats>("/api/stats"),

  entities: {
    list: () => apiFetch<Entity[]>("/api/entities"),
    get: (id: number) => apiFetch<Entity>(`/api/entities/${id}`),
    triggerRun: (key: string) =>
      apiFetch<TriggerRunResponse>(`/api/run/${key}`, { method: "POST" }),
  },

  documents: {
    list: (params: {
      page?: number;
      page_size?: number;
      entity_id?: number;
      doc_type?: string;
      is_new?: boolean;
      search?: string;
      days?: number;
    }) => {
      const q = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
      });
      return apiFetch<PaginatedDocuments>(`/api/documents?${q}`);
    },
    getNew: (days = 7) =>
      apiFetch<Document[]>(`/api/documents/new?days=${days}`),
  },

  runs: {
    list: (params?: { entity_id?: number; status?: string; limit?: number }) => {
      const q = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v !== undefined) q.set(k, String(v));
        });
      }
      return apiFetch<ScrapeRun[]>(`/api/runs?${q}`);
    },
    latest: () => apiFetch<ScrapeRun[]>("/api/runs/latest"),
  },
};
