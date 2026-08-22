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
  schools: Array<{ school_id: string; term_id: string }>;
  complex_id: string | null;
}

export interface SchedulerTimeSlot {
  id: string;
  school_id: string;
  week_pattern_id: string;
  local_cycle_week_index: number;
  project_cycle_week_index: number;
  weekday_index: number;
  day_code: string | null;
  starts_at_minute: number;
  ends_at_minute: number;
  period: number;
  attendance_mode: "onsite" | "remote" | "hybrid";
}
