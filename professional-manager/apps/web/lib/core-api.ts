import { API_URL, TENANT_ID } from "./setup-api";

export type CoreItem = { id: string; name_ar: string };
export type CoreBlock = { id: string; label_ar: string; block_order: number; block_type: string; period_number: number | null; starts_at: string; ends_at: string };
export type AvailabilityCell = { weekday_index: number; period_number: number; state: "available" | "unavailable" | "avoid" };
export type CoreTeacher = CoreItem & { workload_limit: number; assigned: number; remaining: number; shared: boolean; availability: AvailabilityCell[] };
export type CoreAssignment = { id: string; subject_name: string; teacher_names: string[]; section_names: string[]; weekly_occurrences: number };
export type BulkTeacherResult = { created: number; skipped: number; names: string[] };
export type CoreSnapshot = {
  school: { name_ar: string };
  selected_stages: Array<"primary" | "intermediate" | "secondary">;
  term_id: string;
  project_id: string;
  weekdays: number[];
  blocks: CoreBlock[];
  stages: CoreItem[];
  grades: Array<CoreItem & { stage_id: string }>;
  sections: Array<CoreItem & { grade_id: string }>;
  teachers: CoreTeacher[];
  subjects: CoreItem[];
  assignments: CoreAssignment[];
  assignments_count: number;
  rules_count: number;
  readiness: { basic_data: boolean; assignments: boolean; constraints: boolean; preflight: boolean };
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Tenant-ID": TENANT_ID, ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const messages: Record<string, string> = {
      fixed_prayer_time_not_on_period_boundary: "وقت الصلاة الثابت يجب أن يوافق نهاية إحدى الحصص.",
      fixed_prayer_time_breaks_sequence: "وقت الصلاة المختار يقطع حصة قائمة. عدّل الوقت أو اختر الصلاة بعد حصة.",
      preflight_blocked: "أكمل أخطاء الجاهزية قبل إنشاء الجدول.",
      validation_error: "راجع القيم المدخلة ثم حاول مرة أخرى.",
    };
    throw new Error(messages[body?.detail?.code] ?? "تعذر حفظ التغييرات. راجع البيانات وحاول مرة أخرى.");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

const base = (schoolId: string) => `/schools/${schoolId}/core-workflow`;
export const coreApi = {
  snapshot: (schoolId: string) => request<CoreSnapshot>(base(schoolId)),
  saveDay: (schoolId: string, payload: object) => request(`${base(schoolId)}/school-day`, { method: "PUT", body: JSON.stringify(payload) }),
  editPeriod: (schoolId: string, blockId: string, payload: object) => request(`${base(schoolId)}/periods/${blockId}`, { method: "PUT", body: JSON.stringify(payload) }),
  saveStructure: (schoolId: string, payload: object) => request(`${base(schoolId)}/structure`, { method: "PUT", body: JSON.stringify(payload) }),
  createTeacher: (schoolId: string, payload: object) => request(`${base(schoolId)}/teachers`, { method: "POST", body: JSON.stringify(payload) }),
  createTeachers: (schoolId: string, names: string[], workload_limit: number) => request<BulkTeacherResult>(`${base(schoolId)}/teachers/bulk`, { method: "POST", body: JSON.stringify({ names, workload_limit }) }),
  uploadTeachers: async (schoolId: string, file: File, workloadLimit: number) => {
    const form = new FormData(); form.append("file", file); form.append("workload_limit", String(workloadLimit));
    const response = await fetch(`${API_URL}${base(schoolId)}/teachers/bulk-file`, { method: "POST", headers: { "X-Tenant-ID": TENANT_ID }, body: form });
    if (!response.ok) throw new Error("تعذر قراءة الملف. استخدم ملف XLSX أو CSV واجعل أسماء المعلمين في العمود الأول.");
    return response.json() as Promise<BulkTeacherResult>;
  },
  saveAvailability: (schoolId: string, teacherId: string, payload: object) => request(`${base(schoolId)}/teachers/${teacherId}/availability`, { method: "PUT", body: JSON.stringify(payload) }),
  copyAvailability: (schoolId: string, payload: object) => request(`${base(schoolId)}/teachers/availability/copy`, { method: "POST", body: JSON.stringify(payload) }),
  createSubject: (schoolId: string, payload: object) => request(`${base(schoolId)}/subjects`, { method: "POST", body: JSON.stringify(payload) }),
  createAssignment: (schoolId: string, payload: object) => request(`${base(schoolId)}/assignments`, { method: "POST", body: JSON.stringify(payload) }),
  createRule: (schoolId: string, payload: object) => request(`${base(schoolId)}/rules`, { method: "POST", body: JSON.stringify(payload) }),
  generate: (schoolId: string, optimization_profile: string) => request<{ started: boolean; project_id: string; run_id?: string; preflight: { errors: number; warnings: number; diagnostics: Array<{ message: string; suggested_remediation?: string }> } }>(`${base(schoolId)}/generate`, { method: "POST", body: JSON.stringify({ optimization_profile }) }),
};
