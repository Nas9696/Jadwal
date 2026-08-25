import { API_URL, TENANT_ID } from "./setup-api";

export type ImportDiagnostic = {sheet:string;row:number;field:string|null;severity:"error"|"warning"|"info";code:string;message_ar:string;resolution_ar:string|null};
export type ImportRow = {id:string;sheet_name:string;source_row_number:number;entity_type:string;source_values:Record<string,unknown>;normalized_values:Record<string,unknown>;proposed_action:string;diagnostics:ImportDiagnostic[];before_values:Record<string,unknown>;after_values:Record<string,unknown>;excluded:boolean;group_key:string|null};
export type DetectedSheet = {name:string;headers:string[];entity_type:string;confidence:number;suggested_mapping:Record<string,string>;row_count:number};
export type ImportJob = {id:string;school_id:string;term_id:string|null;source_filename:string;file_size:number;file_sha256:string;status:string;detected_sheets:DetectedSheet[];mapping:Record<string,unknown>;validation_summary:Record<string,unknown>;result_summary:Record<string,unknown>;duplicate_file_warning:boolean;rows:ImportRow[]};

async function request<T>(path:string,options?:RequestInit):Promise<T>{
  const headers:Record<string,string>={"X-Tenant-ID":TENANT_ID};if(!(options?.body instanceof FormData))headers["Content-Type"]="application/json";
  const response=await fetch(`${API_URL}${path}`,{...options,headers:{...headers,...options?.headers}});
  if(!response.ok){const body=await response.json().catch(()=>({}));const code=body?.detail?.code;const messages:Record<string,string>={unsupported_file_type:"نوع الملف غير مدعوم. استخدم CSV أو XLSX أو XML من Timetables.",file_size_limit:"حجم الملف يتجاوز الحد المسموح.",row_limit_exceeded:"عدد الصفوف يتجاوز الحد المسموح.",formula_not_allowed:"توجد صيغة غير مسموحة.",mapping_required:"أكد مطابقة الأعمدة أولًا.",import_not_ready:"عالج الأخطاء قبل الاستيراد.",warnings_acknowledgement_required:"يجب الإقرار بالتحذيرات قبل المتابعة.",import_already_committed:"تم استيراد هذه المهمة مسبقًا ولا يمكن تكرارها.",atomic_import_failed:"أُلغي الاستيراد كاملًا ولم تُحفظ بيانات جزئية.",xml_unsafe_declaration:"ملف XML يحتوي تعريفات غير آمنة ولا يمكن فتحه.",xml_encoding_not_supported:"ترميز ملف XML غير مدعوم.",xml_structure_invalid:"تعذر قراءة بنية ملف XML.",xml_not_asctt:"الملف ليس تصديرًا صالحًا من aSc Timetables.",school_shift_required:"أنشئ اليوم الدراسي أولًا قبل استيراد ملف Timetables."};throw new Error(messages[code]??"تعذر تنفيذ عملية الاستيراد.")}
  return response.status===204?undefined as T:response.json();
}

export const importApi={
  upload:(school:string,file:File,term?:string)=>{const body=new FormData();body.append("file",file);if(term)body.append("term_id",term);return request<ImportJob>(`/schools/${school}/imports/upload`,{method:"POST",body})},
  get:(school:string,id:string)=>request<ImportJob>(`/schools/${school}/imports/${id}`),
  mapping:(school:string,id:string,payload:object)=>request<ImportJob>(`/schools/${school}/imports/${id}/mapping`,{method:"PUT",body:JSON.stringify(payload)}),
  validate:(school:string,id:string)=>request<ImportJob>(`/schools/${school}/imports/${id}/validate`,{method:"POST"}),
  exclude:(school:string,id:string,rowIds:string[])=>request<ImportJob>(`/schools/${school}/imports/${id}/exclude`,{method:"PUT",body:JSON.stringify({row_ids:rowIds})}),
  commit:(school:string,id:string,acknowledge:boolean)=>request<ImportJob>(`/schools/${school}/imports/${id}/commit`,{method:"POST",body:JSON.stringify({acknowledge_warnings:acknowledge})}),
  downloadTemplate:async(school:string,kind:string)=>{
    const response=await fetch(`${API_URL}/schools/${school}/imports/templates/${kind}.csv`,{headers:{"X-Tenant-ID":TENANT_ID}});
    if(!response.ok)throw new Error("تعذر تنزيل القالب.");
    const url=URL.createObjectURL(await response.blob());const anchor=document.createElement("a");anchor.href=url;anchor.download=`${kind}.csv`;anchor.click();URL.revokeObjectURL(url);
  },
};
