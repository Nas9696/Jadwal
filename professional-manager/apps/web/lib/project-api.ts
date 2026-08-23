import { API_URL, TENANT_ID } from "./setup-api";

export type ProjectSchool = { school_id: string; term_id: string; cycle_phase_offset: number };
export type Project = { id: string; name_ar: string; description?: string; status: string; scope_type: string; schools: ProjectSchool[] };
export type Rule = { id: string; label: string; description?: string; rule_type: string; severity: "hard" | "soft"; weight: number | null; selector: Record<string, unknown>; parameters: Record<string, unknown>; enabled: boolean };
export type Diagnostic = { code: string; message?: string; message_key?: string };
export type Preflight = { readiness: string; errors: number; warnings: number; diagnostics: Diagnostic[] };
export type Penalty = { rule_id: string; rule_type: string; violation_count: number; weight: number; weighted_penalty: number; category?:string };
export type CandidateSummary = { id: string; rank: number; solver_status: string; total_penalty: number; penalty_breakdown: Penalty[]; solve_time_ms: number; diversity_count: number };
export type SolveRun = { id: string; project_id: string; status: "queued" | "running" | "completed" | "infeasible" | "unknown" | "failed"; input_fingerprint: string; solver_status: string | null; diagnostics: Diagnostic[]; candidates: CandidateSummary[] };
type Label = { id: string; name_ar: string };
export type TimetableEntry = { id: string; occurrence_id: string; slot_id: string; project_cycle_week_index: number; weekday_index: number; starts_at_minute: number; ends_at_minute: number; school: Label; subject: Label; teachers: Label[]; sections: Label[]; resources: Label[] };
export type CandidateDetail = CandidateSummary & { entries: TimetableEntry[] };
export type EditorLock = { id: string; lock_type: string; occurrence_id?: string; label: string };
export type WorkingTimetable = {
  id: string; project_id: string; source_candidate_id: string; name: string;
  version_number: number; revision: number; history_cursor: number; status: string;
  change_summary?: string; can_undo: boolean; can_redo: boolean;
  entries: TimetableEntry[]; locks: EditorLock[];
};
export type MoveAnalysis = {
  revision: number; occurrence_id: string; source_slot_id: string; valid: boolean;
  target_slot: { id: string; project_cycle_week_index: number; weekday_index: number; starts_at_minute: number; ends_at_minute: number };
  violations: Array<{ code: string; occurrence_id?: string }>;
  teacher_conflicts: Array<{ occurrence_id: string }>;
  section_conflicts: Array<{ occurrence_id: string }>;
  resource_conflicts: Array<{ occurrence_id: string }>;
  hard_rule_violations: Array<{ code: string; label?: string }>;
  lock_violations: EditorLock[]; affected_entries: Array<{ occurrence_id: string }>;
  soft_penalty_delta: number; swap_candidates: Array<{ occurrence_id: string; slot_id: string }>;
  alternative_slots: Array<{ id: string; project_cycle_week_index: number; weekday_index: number; starts_at_minute: number; ends_at_minute: number }>;
};
export type RepairPreview = { revision: number; occurrence_id: string; target_slot_id: string; fingerprint: string; total_moved_occurrences: number; penalty_before: number; penalty_after: number; changes: Array<{ occurrence_id: string; from: { slot_id: string }; to: { slot_id: string }; reason: string }> };
export type TimetableSnapshot = { id: string; name: string; source_revision: number; changed_occurrences: number; created_at: string };
export type AuditEvent = { id: string; revision: number; operation_type: string; summary: string; created_at: string };
export type SnapshotComparison = { snapshot_id: string; source_revision: number; current_revision: number; changed_occurrences: number; changes: Array<{ occurrence_id: string; snapshot: { slot_id: string }; current: { slot_id: string } | null }> };
export type ProjectSlot = { id: string; school_id: string; project_cycle_week_index: number; weekday_index: number; starts_at_minute: number; ends_at_minute: number; attendance_mode: string };
export type QualityReport = { hard_violations: Array<Record<string, unknown>>; total_weighted_penalty: number; penalty_breakdown: Penalty[]; teacher_gaps: Record<string, number>; teacher_gap_total: number; first_period_distribution: Record<string, number>; last_period_distribution: Record<string, number>; consecutive_streaks: Array<{teacher_id:string;maximum_streak:number}>; distribution_violations: Array<Record<string, unknown>>; source: Record<string, unknown> };
export type PlacementExplanation = { occurrence_id:string; chosen_slot:ProjectSlot; mandatory_rule_facts:Array<Record<string,unknown>>; preference_rule_facts:Array<Record<string,unknown>>; entity_facts:Record<string,string[]>; alternatives:Array<{slot:ProjectSlot;status:"blocked"|"valid"|"valid_but_worse";blocking_facts:Array<Record<string,unknown>>;penalty_delta:number}> };

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...options, headers: { "Content-Type": "application/json", "X-Tenant-ID": TENANT_ID, ...options?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const messages: Record<string, string> = { preflight_blocked: "أكمل أخطاء فحص الجاهزية قبل توليد الجدول.", solve_run_already_active: "يوجد توليد جارٍ لهذا المشروع بالفعل.", invalid_cycle_phase_offset: "محاذاة دورة المدرسة خارج النطاق المتاح.", timetable_version_conflict: "تغير الجدول منذ فتحه. أعد التحميل والتحليل.", move_conflict: "النقل غير آمن؛ راجع لوحة التعارضات.", swap_conflict: "لا يمكن تنفيذ التبديل دون تعارض.", repair_infeasible: "تعذر إيجاد إصلاح يحترم القيود والأقفال." };
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
  solve: (id: string, payload: object = { candidate_count: 3, time_limit_seconds: 10, seed: 0, optimization_profile: "balanced" }) => req<SolveRun>(`/timetable-projects/${id}/solve`, { method: "POST", body: JSON.stringify(payload) }),
  solveRun: (projectId: string, runId: string) => req<SolveRun>(`/timetable-projects/${projectId}/solve-runs/${runId}`),
  candidate: (projectId: string, candidateId: string) => req<CandidateDetail>(`/timetable-projects/${projectId}/candidates/${candidateId}`),
  candidateQuality: (projectId:string,candidateId:string)=>req<QualityReport>(`/timetable-projects/${projectId}/candidates/${candidateId}/quality`),
  candidateExplanation: (projectId:string,candidateId:string,occurrenceId:string)=>req<PlacementExplanation>(`/timetable-projects/${projectId}/candidates/${candidateId}/explanations?occurrence_id=${encodeURIComponent(occurrenceId)}`),
  problem: (projectId: string) => req<{ slots: ProjectSlot[] }>(`/timetable-projects/${projectId}/problem`),
  deriveWorking: (projectId: string, candidateId: string) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable/from-candidate/${candidateId}`, { method: "POST" }),
  working: (projectId: string) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable`),
  workingQuality: (projectId:string)=>req<QualityReport>(`/timetable-projects/${projectId}/working-timetable/quality`),
  workingExplanation: (projectId:string,occurrenceId:string)=>req<PlacementExplanation>(`/timetable-projects/${projectId}/working-timetable/explanations?occurrence_id=${encodeURIComponent(occurrenceId)}`),
  compareQuality: (projectId:string,candidateId:string)=>req<Record<string,unknown>>(`/timetable-projects/${projectId}/working-timetable/quality/compare/${candidateId}`),
  analyzeMove: (projectId: string, payload: object) => req<MoveAnalysis>(`/timetable-projects/${projectId}/working-timetable/moves/analyze`, { method: "POST", body: JSON.stringify(payload) }),
  applyMove: (projectId: string, payload: object) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable/moves/apply`, { method: "POST", body: JSON.stringify(payload) }),
  applySwap: (projectId: string, payload: object) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable/swaps/apply`, { method: "POST", body: JSON.stringify(payload) }),
  undo: (projectId: string, revision: number) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable/undo`, { method: "POST", body: JSON.stringify({ revision }) }),
  redo: (projectId: string, revision: number) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable/redo`, { method: "POST", body: JSON.stringify({ revision }) }),
  lockOccurrence: (projectId: string, occurrenceId: string, revision: number) => req<{ lock: EditorLock; revision: number }>(`/timetable-projects/${projectId}/working-timetable/locks`, { method: "POST", body: JSON.stringify({ revision, lock_type: "occurrence", occurrence_id: occurrenceId, label: "قفل الحصة" }) }),
  unlock: (projectId: string, lockId: string, revision: number) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable/locks/${lockId}?revision=${revision}`, { method: "DELETE" }),
  repairPreview: (projectId: string, payload: object) => req<RepairPreview>(`/timetable-projects/${projectId}/working-timetable/repair/preview`, { method: "POST", body: JSON.stringify(payload) }),
  repairApply: (projectId: string, payload: object) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable/repair/apply`, { method: "POST", body: JSON.stringify(payload) }),
  snapshots: (projectId: string) => req<TimetableSnapshot[]>(`/timetable-projects/${projectId}/working-timetable/snapshots`),
  audit: (projectId: string) => req<AuditEvent[]>(`/timetable-projects/${projectId}/working-timetable/audit`),
  compareSnapshot: (projectId: string, snapshotId: string) => req<SnapshotComparison>(`/timetable-projects/${projectId}/working-timetable/snapshots/${snapshotId}/compare`),
  createSnapshot: (projectId: string, name: string, revision: number) => req<TimetableSnapshot>(`/timetable-projects/${projectId}/working-timetable/snapshots`, { method: "POST", body: JSON.stringify({ name, revision }) }),
  restoreSnapshot: (projectId: string, snapshotId: string, revision: number) => req<WorkingTimetable>(`/timetable-projects/${projectId}/working-timetable/snapshots/${snapshotId}/restore`, { method: "POST", body: JSON.stringify({ revision }) }),
};
