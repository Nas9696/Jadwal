import { API_URL, TENANT_ID } from "./setup-api";

export type ReportType = "general_timetable" | "section_timetable" | "teacher_timetable" | "subject_timetable" | "resource_timetable" | "daily_substitutions" | "waiting_workload";
export type ReportOption = { id:string; label:string; school_id:string|null; school_ids:string[] };
export type ReportOptions = { schools:ReportOption[]; teachers:ReportOption[]; sections:ReportOption[]; subjects:ReportOption[]; resources:ReportOption[] };
export type ReportRow = Record<string, unknown> & { row_id:string; teacher_names:string[]; section_names:string[]; resource_names:string[] };
export type ReportDataset = { report_type:ReportType; title:string; subtitle:string|null; source:{kind:"working"|"candidate"; revision:number|null; version_number:number|null; project_name:string}; columns:string[]; rows:ReportRow[]; row_count:number; stale:boolean; warnings:string[] };
export type ReportRequest = {
  report_type:ReportType;
  source:{kind:"working"|"candidate"; candidate_id?:string; expected_revision?:number};
  filters:Record<string,string|number|undefined>;
  print_options:{paper:"A4"|"A3";orientation:"portrait"|"landscape";density:"compact"|"comfortable";theme:"color"|"monochrome";show_heading:boolean;show_period_time:boolean;show_resource:boolean};
  branding:{title_override?:string;subtitle?:string;logo_data_url?:string;qr_payload?:string;footer_text?:string;signature_labels:string[]};
};

async function json<T>(path:string, init?:RequestInit):Promise<T>{
  const response=await fetch(`${API_URL}${path}`,{...init,headers:{"Content-Type":"application/json","X-Tenant-ID":TENANT_ID,...init?.headers}});
  if(!response.ok){const body=await response.json().catch(()=>({})); const code=body?.detail?.code; const messages:Record<string,string>={report_source_revision_conflict:"تغيرت نسخة الجدول. حدّث المعاينة قبل التصدير.",stale_report_source:"بيانات البدلاء مبنية على نسخة أقدم ولا يمكن تصديرها.",unsafe_logo_type:"الشعار يجب أن يكون PNG أو JPEG آمنًا.",unsafe_logo_content:"تعذر التحقق من ملف الشعار.",expected_revision_required_for_export:"حدّث المعاينة قبل التصدير."}; throw new Error(messages[code]??"تعذر إعداد التقرير.");}
  return response.json();
}

export const reportApi={
  options:(projectId:string)=>json<ReportOptions>(`/timetable-projects/${projectId}/reports/options`),
  preview:(projectId:string,payload:ReportRequest)=>json<ReportDataset>(`/timetable-projects/${projectId}/reports/preview`,{method:"POST",body:JSON.stringify(payload)}),
  export:async(projectId:string,payload:ReportRequest,format:"pdf"|"xlsx"|"png")=>{
    const response=await fetch(`${API_URL}/timetable-projects/${projectId}/reports/export`,{method:"POST",headers:{"Content-Type":"application/json","X-Tenant-ID":TENANT_ID},body:JSON.stringify({...payload,format})});
    if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(body?.detail?.code==="report_source_revision_conflict"?"تغيرت نسخة الجدول. حدّث المعاينة قبل التصدير.":"تعذر تصدير التقرير.");}
    const disposition=response.headers.get("Content-Disposition")??""; const filename=/filename="([^"]+)"/.exec(disposition)?.[1]??`report.${format}`;
    return {blob:await response.blob(),filename,pages:Number(response.headers.get("X-Report-Pages")??1),multiPage:response.headers.get("X-Report-Multi-Page")==="true"};
  },
};
