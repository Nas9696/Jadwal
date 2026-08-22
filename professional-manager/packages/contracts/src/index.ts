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

export interface TeacherSchoolMembership {
  id: string;
  tenant_id: string;
  teacher_id: string;
  school_id: string;
  local_employee_code: string | null;
  is_home_school: boolean;
  is_active: boolean;
}

export interface TimetableProject {
  id: string;
  tenant_id: string;
  name_ar: string;
  scope_type: "school" | "complex" | "schools";
  school_ids: string[];
  complex_id: string | null;
}
