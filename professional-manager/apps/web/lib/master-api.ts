import { API_URL, TENANT_ID, type Item, type School } from "./setup-api";

export type LinkedTeacherSchool = {
  school_id: string;
  name_ar: string;
  code: string;
  is_home_school: boolean;
  is_active: boolean;
  local_employee_code: string | null;
  is_current_school: boolean;
};
export type TeacherCard = { teacher: Item; membership: Item; schools: LinkedTeacherSchool[]; is_shared: boolean; assigned_workload: number };
export type TeacherSnapshot = { school: School; teachers: TeacherCard[]; available_teachers: Item[] };
export type CatalogSnapshot = { school: School; subjects: Item[]; resources: Item[]; requirements: Item[]; grades: Item[]; stages: Item[] };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...options, headers: { "Content-Type": "application/json", "X-Tenant-ID": TENANT_ID, ...options?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({})); const code = body?.detail?.code;
    const messages: Record<string,string> = {
      duplicate_or_dependent_data: "يوجد سجل بالرمز نفسه أو ارتباط مكرر.", teacher_not_in_tenant: "المعلم المحدد لا يتبع هذا الحساب.",
      teacher_membership_has_assignments: "لا يمكن فك ارتباط المعلم لوجود إسنادات مرتبطة.", subject_has_dependencies: "احذف الأنصبة المرتبطة بالمادة أولًا.",
      resource_has_dependencies: "المورد مستخدم في بيانات أخرى ولا يمكن حذفه.", grade_not_in_school: "الصف لا يتبع المدرسة الحالية.",
      subject_not_in_school: "المادة لا تتبع المدرسة الحالية.", validation_error: "راجع الحقول والقيم المدخلة.",
      membership_already_exists_use_reactivation: "للمعلم ارتباط سابق بهذه المدرسة؛ استخدم إعادة التفعيل بدل إنشاء ارتباط جديد.",
      archived_teacher_cannot_have_active_membership: "هوية المعلم مؤرشفة. أعد تفعيل المعلم أولًا ثم فعّل ارتباطه بالمدرسة.",
      teacher_has_active_memberships: "عطّل ارتباط المعلم في جميع مدارسه قبل أرشفة هويته.",
    };
    throw new Error(messages[code] ?? "تعذر تنفيذ العملية. حاول مرة أخرى.");
  }
  return response.status === 204 ? undefined as T : response.json();
}

export const masterApi = {
  teachers: (school: string) => request<TeacherSnapshot>(`/schools/${school}/teachers`),
  createTeacher: (school: string, payload: object) => request<Item>(`/schools/${school}/teachers`, { method:"POST", body:JSON.stringify(payload) }),
  linkTeacher: (school: string, payload: object) => request<Item>(`/schools/${school}/teacher-memberships`, { method:"POST", body:JSON.stringify(payload) }),
  updateTeacher: (school: string, id: string, payload: object) => request<Item>(`/schools/${school}/teachers/${id}`, { method:"PUT", body:JSON.stringify(payload) }),
  updateMembership: (school: string, id: string, payload: object) => request<Item>(`/schools/${school}/teacher-memberships/${id}`, { method:"PUT", body:JSON.stringify(payload) }),
  unlink: (school: string, id: string) => request<void>(`/schools/${school}/teacher-memberships/${id}`, { method:"DELETE" }),
  catalog: (school: string) => request<CatalogSnapshot>(`/schools/${school}/catalog`),
  createCatalog: (school:string, kind:string, payload:object) => request<Item>(`/schools/${school}/catalog/${kind}`, {method:"POST",body:JSON.stringify(payload)}),
  updateCatalog: (school:string, kind:string, id:string, payload:object) => request<Item>(`/schools/${school}/catalog/${kind}/${id}`, {method:"PUT",body:JSON.stringify(payload)}),
  deleteCatalog: (school:string, kind:string, id:string) => request<void>(`/schools/${school}/catalog/${kind}/${id}`, {method:"DELETE"}),
};
