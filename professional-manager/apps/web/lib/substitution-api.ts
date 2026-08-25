import { API_URL, TENANT_ID } from "./setup-api";

export type WaitingPolicy = {
  id: string | null; project_id: string; combined_workload_limit: number | null;
  daily_waiting_limit: number | null; weekly_waiting_limit: number | null;
  fairness_weight: number; specialty_preference_enabled: boolean;
  specialty_preference_weight: number; same_school_preference_weight: number;
  exclude_exempt_teachers: boolean; enabled: boolean;
};
export type Workload = {
  teacher_id: string; teacher_name: string; base_target: number; teaching_load: number;
  assigned_today: number; assigned_this_week: number; combined_limit: number;
  daily_limit: number | null; weekly_limit: number | null; remaining_capacity: number;
  exempt: boolean; custom_combined_limit: number | null; custom_daily_limit: number | null;
  custom_weekly_limit: number | null; notes: string | null;
};
export type SubstituteAssignment = {
  id: string; teacher_id: string; teacher_name: string; score: number; rank: number;
  manual_override: boolean; score_breakdown: Record<string, number>;
  eligibility_facts: Record<string, unknown>;
};
export type SubstitutionNeed = {
  id: string; absence_id: string; version: number; occurrence_id: string;
  school_id: string; school_name: string; subject_id: string; subject_name: string;
  section_names: string[]; project_cycle_week_index: number; weekday_index: number;
  starts_at_minute: number; ends_at_minute: number; status: string;
  source_working_revision: number; stale: boolean; assignment: SubstituteAssignment | null;
};
export type Absence = {
  id: string; project_id: string; school_id: string; school_name: string;
  teacher_id: string; teacher_name: string; absence_date: string;
  project_cycle_week_index: number; weekday_index: number; full_day: boolean;
  starts_at_minute: number | null; ends_at_minute: number | null; reason_code: string | null;
  reason_text: string | null; status: string; working_timetable_revision: number;
  stale: boolean; needs: SubstitutionNeed[];
};
export type DailySummary = {
  date: string; absent_teachers: number; needs: number; covered: number; uncovered: number;
  teachers_carrying_substitutions: number; absences: Absence[];
};
export type Candidate = {
  teacher_id: string; teacher_name: string; canonical_code: string; eligible: boolean;
  blocking_reasons: string[]; free_at_time: boolean; teaching_load: number;
  assigned_today: number; assigned_this_week: number; combined_after_assignment: number;
  combined_limit: number; daily_limit: number | null; weekly_limit: number | null;
  exempt: boolean; specialty_considered: boolean; specialty_match: boolean | null;
  same_school_membership: boolean; score_breakdown: Record<string, number>;
  total_score: number; rank: number;
};
export type CandidateList = {
  need_id: string; need_version: number; working_timetable_revision: number;
  candidates: Candidate[]; excluded: Candidate[];
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Tenant-ID": TENANT_ID, ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const code = body?.detail?.code;
    const messages: Record<string, string> = {
      working_timetable_not_found: "لا توجد نسخة عمل حالية لهذا المشروع. اعتمد مرشحًا أولًا.",
      timetable_version_conflict: "تغير جدول العمل. حدّث الغياب قبل المتابعة.",
      stale_substitution_need: "هذه الحاجة مبنية على نسخة جدول قديمة. استخدم تحديث الغياب.",
      substitution_need_version_conflict: "تغيرت حالة الحاجة. أعد تحميل اليوم.",
      substitution_need_already_assigned: "تم إسناد بديل لهذه الحصة بالفعل.",
      hard_ineligible_substitute: "المعلم غير مؤهل بسبب تعارض أو حد نصاب أو استثناء.",
      inactive_or_out_of_scope_absent_teacher: "المعلم غير نشط في المدرسة أو خارج نطاق المشروع.",
      school_outside_project_scope: "المدرسة خارج نطاق مشروع الجدول.",
    };
    throw new Error(messages[code] ?? "تعذر تنفيذ عملية الغياب والبدلاء.");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

const root = (projectId: string) => `/timetable-projects/${projectId}/substitutions`;
export const substitutionApi = {
  policy: (projectId: string) => request<WaitingPolicy>(`${root(projectId)}/policy`),
  savePolicy: (projectId: string, payload: object) => request<WaitingPolicy>(`${root(projectId)}/policy`, { method: "PUT", body: JSON.stringify(payload) }),
  saveProfile: (projectId: string, teacherId: string, payload: object) => request<object>(`${root(projectId)}/profiles/${teacherId}`, { method: "PUT", body: JSON.stringify(payload) }),
  workloads: (projectId: string, date: string) => request<Workload[]>(`${root(projectId)}/workloads?date=${date}`),
  summary: (projectId: string, date: string) => request<DailySummary>(`${root(projectId)}/daily-summary?date=${date}`),
  createAbsence: (projectId: string, payload: object) => request<Absence>(`${root(projectId)}/absences`, { method: "POST", body: JSON.stringify(payload) }),
  refreshAbsence: (projectId: string, absenceId: string, revision: number) => request<Absence>(`${root(projectId)}/absences/${absenceId}/refresh`, { method: "POST", body: JSON.stringify({ working_timetable_revision: revision }) }),
  cancelAbsence: (projectId: string, absenceId: string) => request<Absence>(`${root(projectId)}/absences/${absenceId}/cancel`, { method: "POST" }),
  candidates: (projectId: string, needId: string) => request<CandidateList>(`${root(projectId)}/needs/${needId}/candidates`),
  assign: (projectId: string, needId: string, payload: object) => request<SubstitutionNeed>(`${root(projectId)}/needs/${needId}/assign`, { method: "POST", body: JSON.stringify(payload) }),
  unassign: (projectId: string, needId: string, payload: object) => request<SubstitutionNeed>(`${root(projectId)}/needs/${needId}/unassign`, { method: "POST", body: JSON.stringify(payload) }),
};
