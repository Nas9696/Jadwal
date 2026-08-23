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

export interface LinkedTeacherSchool {
  school_id: string;
  name_ar: string;
  code: string;
  is_home_school: boolean;
  is_active: boolean;
  local_employee_code: string | null;
  is_current_school: boolean;
}

export interface CanonicalTeacher {
  id: string;
  tenant_id: string;
  canonical_code: string;
  name_ar: string;
  name_en: string | null;
  specialty_reference: string | null;
  base_workload: number;
  teaching_workload_limit: number;
  is_active: boolean;
}

export interface SchoolSubject {
  id: string;
  tenant_id: string;
  school_id: string;
  code: string;
  name_ar: string;
  name_en: string | null;
  is_active: boolean;
}

export interface CurriculumRequirement {
  id: string;
  tenant_id: string;
  school_id: string;
  grade_id: string;
  subject_id: string;
  weekly_occurrences: number;
  notes: string | null;
}

export type ResourceType =
  | "classroom"
  | "science_lab"
  | "computer_lab"
  | "gym"
  | "learning_resources"
  | "playground"
  | "other";

export interface SchoolResource {
  id: string;
  tenant_id: string;
  school_id: string;
  code: string;
  name_ar: string;
  resource_type: ResourceType;
  capacity: number | null;
  exclusive: boolean;
  is_active: boolean;
}

export interface SectionOffering {
  id: string;
  tenant_id: string;
  school_id: string;
  term_id: string;
  section_id: string;
  shift_id: string;
  is_active: boolean;
}

export interface TeachingAssignment {
  id: string;
  tenant_id: string;
  school_id: string;
  term_id: string;
  subject_id: string;
  weekly_occurrences: number;
  teacher_ids: string[];
  section_offering_ids: string[];
  resource_ids: string[];
  notes: string | null;
}

export type CurriculumCoverageStatus =
  | "missing"
  | "partial"
  | "complete"
  | "over"
  | "no_requirement";

export interface AssignmentCoverageCell {
  offering_id: string;
  subject_id: string;
  required: number | null;
  assigned: number;
  status: CurriculumCoverageStatus;
  assignment_ids: string[];
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

export interface SchoolShift {
  id: string;
  school_id: string;
  code: string;
  name_ar: string;
  name_en: string | null;
  order: number;
  is_active: boolean;
}

export interface SchoolDay {
  id: string;
  school_id: string;
  shift_id: string;
  week_pattern_id: string;
  weekday_index: number;
  enabled: boolean;
  label_ar: string | null;
}

export interface DayBlock {
  id: string;
  school_id: string;
  school_day_id: string;
  week_pattern_id: string;
  weekday_index: number;
  block_order: number;
  block_type: "lesson" | "break" | "prayer" | "assembly" | "activity" | "custom";
  label_ar: string | null;
  starts_at: string;
  ends_at: string;
  period_number: number | null;
  attendance_mode: "onsite" | "remote" | "hybrid";
  schedulable: boolean;
}
