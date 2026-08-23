import { API_URL, TENANT_ID } from "./setup-api";

export type ProjectSchool = { school_id: string; term_id: string; cycle_phase_offset: number };
export type Project = { id: string; name_ar: string; description?: string; status: string; scope_type: string; schools: ProjectSchool[] };
export type Rule = { id: string; label: string; description?: string; rule_type: string; severity: "hard" | "soft"; weight: number | null; selector: Record<string, unknown>; parameters: Record<string, unknown>; enabled: boolean };
export type Diagnostic = { code: string; message?: string; message_key?: string };
export type Preflight = { readiness: string; errors: number; warnings: number; diagnostics: Diagnostic[] };
export type Penalty = { rule_id: string; rule_type: string; violation_count: number; weight: number; weighted_penalty: number };
export type CandidateSummary = { id: string; rank: number; solver_status: string; total_penalty: number; penalty_breakdown: Penalty[]; solve_time_ms: number; diversity_count: number };
export type SolveRun = { id: string; project_id: string; status: "queued" | "running" | "completed" | "infeasible" | "unknown" | "failed"; input_fingerprint: string; solver_status: string | null; diagnostics: Diagnostic[]; candidates: CandidateSummary[] };
type Label = { id: string; name_ar: string };
export type TimetableEntry = { id: string; occurrence_id: string; slot_id: string; project_cycle_week_index: number; weekday_index: number; starts_at_minute: number; ends_at_minute: number; school: Label; subject: Label; teachers: Label[]; sections: Label[]; resources: Label[] };
export type CandidateDetail = CandidateSummary & { entries: TimetableEntry[] };

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...options, headers: { "Content-Type": "application/json", "X-Tenant-ID": TENANT_ID, ...options?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const messages: Record<string, string> = { preflight_blocked: "أكمل أخطاء فحص الجاهزية قبل توليد الجدول.", solve_run_already_active: "يوجد توليد جارٍ لهذا المشروع بالفعل.", invalid_cycle_phase_offset: "محاذاة دورة المدرسة خارج النطاق المتاح." };
    throw new Error(messages[body?.detail?.code] ?? "تعذر تنفيذ العملية. راجع نطاق المشروع والقاعدة.");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const projectApi = {
  list: () => req<Project[]>("/timetable-projects"),
  create: (payload: object) => req<Project>("/timetable-projects", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: string, payload: object) => req<Project>(`/timetable-projects/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  remove: (id: string) => req<void>(`/timetable-projects/${id}`, { method: "DELETE" }),
  rules: (id: string) => req<Rule[]>(`/timetable-projects/${id}/rules`),
  saveRule: (id: string, payload: object) => req<Rule>(`/timetable-projects/${id}/rules`, { method: "POST", body: JSON.stringify(payload) }),
  updateRule: (id: string, ruleId: string, payload: object) => req<Rule>(`/timetable-projects/${id}/rules/${ruleId}`, { method: "PUT", body: JSON.stringify(payload) }),
  duplicateRule: (id: string, ruleId: string) => req<Rule>(`/timetable-projects/${id}/rules/${ruleId}/duplicate`, { method: "POST" }),
  removeRule: (id: string, ruleId: string) => req<void>(`/timetable-projects/${id}/rules/${ruleId}`, { method: "DELETE" }),
  preflight: (id: string) => req<Preflight>(`/timetable-projects/${id}/preflight`, { method: "POST" }),
  solve: (id: string, payload = { candidate_count: 3, time_limit_seconds: 10, seed: 0 }) => req<SolveRun>(`/timetable-projects/${id}/solve`, { method: "POST", body: JSON.stringify(payload) }),
  solveRun: (projectId: string, runId: string) => req<SolveRun>(`/timetable-projects/${projectId}/solve-runs/${runId}`),
  candidate: (projectId: string, candidateId: string) => req<CandidateDetail>(`/timetable-projects/${projectId}/candidates/${candidateId}`),
};
