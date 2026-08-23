import { API_URL, TENANT_ID, type Item, type School } from "./setup-api";

export type Assignment = {
  id: string; term_id: string; subject_id: string; weekly_occurrences: number;
  teacher_ids: string[]; section_offering_ids: string[]; resource_ids: string[]; notes: string | null;
};
export type Offering = Item & { section_id: string; shift_id: string; term_id: string; is_active: boolean };
export type AssignmentCell = { offering_id: string; subject_id: string; required: number | null; assigned: number; status: "missing"|"partial"|"complete"|"over"|"no_requirement"; assignment_ids: string[] };
export type AssignmentSnapshot = {
  school: School; selected_term: Item; years: Item[]; terms: Item[]; shifts: Item[];
  sections: Array<{id:string;name_ar:string;grade_id:string;grade_name:string;stage_id:string;stage_name:string}>;
  offerings: Offering[]; subjects: Item[]; resources: Item[];
  teachers: Array<{id:string;name_ar:string;base_workload:number;teaching_workload_limit:number;assigned_workload:number;other_school_overlapping_workload?:number}>;
  assignments: Assignment[]; cells: AssignmentCell[];
};

async function request<T>(path:string, options?:RequestInit):Promise<T>{
  const response=await fetch(`${API_URL}${path}`,{...options,headers:{"Content-Type":"application/json","X-Tenant-ID":TENANT_ID,...options?.headers}});
  if(!response.ok){const body=await response.json().catch(()=>({}));const code=body?.detail?.code;const messages:Record<string,string>={
    term_not_in_school:"الفصل الدراسي لا يتبع المدرسة الحالية.",section_offering_not_in_term:"الشعبة غير مفعلة في هذا الفصل الدراسي.",
    teacher_not_active_in_school:"المعلم غير نشط أو غير مرتبط بهذه المدرسة.",subject_not_in_school:"المادة لا تتبع المدرسة الحالية.",
    subject_inactive:"المادة غير نشطة ولا يمكن إنشاء إسناد جديد لها.",resource_not_in_school:"المورد لا يتبع المدرسة الحالية.",
    resource_inactive:"المورد غير نشط.",section_offering_has_assignments:"احذف إسنادات الشعبة قبل تعطيلها.",
    curriculum_requirement_missing:"لا يوجد نصاب منهجي لهذه الخلية.",duplicate_relation:"يوجد ارتباط مكرر داخل الإسناد.",validation_error:"راجع بيانات الإسناد المطلوبة.",
  };throw new Error(messages[code]??"تعذر تنفيذ عملية الإسناد.")}
  return response.status===204?undefined as T:response.json();
}

export const assignmentApi={
  snapshot:(school:string,term:string)=>request<AssignmentSnapshot>(`/schools/${school}/assignments?term_id=${term}`),
  offerings:(school:string,payload:object)=>request<Offering[]>(`/schools/${school}/assignments/section-offerings`,{method:"PUT",body:JSON.stringify(payload)}),
  create:(school:string,payload:object)=>request<{assignment_id:string;warnings:Array<{code:string;value:number}>}>(`/schools/${school}/assignments`,{method:"POST",body:JSON.stringify(payload)}),
  update:(school:string,id:string,payload:object)=>request<{assignment_id:string;warnings:Array<{code:string;value:number}>}>(`/schools/${school}/assignments/${id}`,{method:"PUT",body:JSON.stringify(payload)}),
  remove:(school:string,id:string)=>request<void>(`/schools/${school}/assignments/${id}`,{method:"DELETE"}),
  bulk:(school:string,payload:object)=>request<Array<{assignment_id:string;warnings:Array<{code:string;value:number}>}>>(`/schools/${school}/assignments/bulk/apply`,{method:"POST",body:JSON.stringify(payload)}),
  bulkTeachers:(school:string,payload:object)=>request<Array<{assignment_id:string;warnings:Array<{code:string;value:number}>}>>(`/schools/${school}/assignments/bulk/teachers`,{method:"POST",body:JSON.stringify(payload)}),
  bulkDelete:(school:string,payload:object)=>request<{deleted:number}>(`/schools/${school}/assignments/bulk/delete`,{method:"POST",body:JSON.stringify(payload)}),
};
