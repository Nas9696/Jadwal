export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const TENANT_ID = process.env.NEXT_PUBLIC_DEMO_TENANT_ID ?? "00000000-0000-4000-8000-000000000001";

export type School = { id: string; name_ar: string; name_en?: string; code: string };
export type Item = Record<string, string | number | boolean | null> & { id: string };
export type SetupSnapshot = { school: School } & Record<string, Item[]>;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Tenant-ID": TENANT_ID, ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const code = body?.detail?.code;
    const messages: Record<string, string> = {
      day_block_overlap: "يتداخل هذا الوقت مع عنصر موجود في اليوم الدراسي.",
      resource_has_dependencies: "لا يمكن الحذف قبل حذف العناصر المرتبطة.",
      duplicate_or_dependent_data: "هذه البيانات مكررة أو مرتبطة بسجل غير صالح.",
      week_indexes_must_be_contiguous: "أضف أنماط الأسابيع بالترتيب دون فجوات.",
      calendar_reference_not_in_school: "الفترة أو نمط الأسبوع لا يتبع المدرسة الحالية.",
      validation_error: "راجع الحقول المطلوبة والقيم المدخلة.",
    };
    throw new Error(messages[code] ?? "تعذر حفظ البيانات. حاول مرة أخرى.");
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const setupApi = {
  schools: () => request<School[]>("/schools"),
  snapshot: (schoolId: string) => request<SetupSnapshot>(`/schools/${schoolId}/setup`),
  create: (schoolId: string, resource: string, payload: object) => request<Item>(`/schools/${schoolId}/setup/${resource}`, { method: "POST", body: JSON.stringify(payload) }),
  update: (schoolId: string, resource: string, id: string, payload: object) => request<Item>(`/schools/${schoolId}/setup/${resource}/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  remove: (schoolId: string, resource: string, id: string) => request<void>(`/schools/${schoolId}/setup/${resource}/${id}`, { method: "DELETE" }),
};
