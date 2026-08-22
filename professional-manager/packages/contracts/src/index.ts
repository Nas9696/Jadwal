export interface HealthResponse {
  status: "ok" | "degraded";
  service: string;
  version: string;
}

export interface School {
  id: string;
  tenant_id: string;
  name_ar: string;
  name_en: string | null;
  code: string;
  school_type: string;
  created_at: string;
}

