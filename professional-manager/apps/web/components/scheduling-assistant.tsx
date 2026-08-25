"use client";

import { FormEvent, useState } from "react";
import { projectApi, type AssistantPreview } from "@/lib/project-api";

type Props = { projectId:string; onConfirmed:()=>Promise<void> };
const examples = [
  "لا تضع للأستاذ أحمد الحصة الأولى يوم الأحد",
  "يفضل أن تكون الرياضيات في أول ثلاث حصص",
  "لا تجعل للأستاذ علي أكثر من 4 حصص في اليوم",
];

export function SchedulingAssistant({projectId,onConfirmed}:Props){
  const [text,setText]=useState("");
  const [preview,setPreview]=useState<AssistantPreview|null>(null);
  const [selected,setSelected]=useState<string[]>([]);
  const [resolutions,setResolutions]=useState<Record<string,string>>({});
  const [busy,setBusy]=useState(false); const [error,setError]=useState(""); const [success,setSuccess]=useState("");
  async function parse(event?:FormEvent){
    event?.preventDefault(); if(!text.trim())return; setBusy(true);setError("");setSuccess("");
    try{const value=await projectApi.assistantParse(projectId,{text,resolutions});setPreview(value);setSelected(value.proposals.map(x=>x.id));}
    catch(reason){setError(reason instanceof Error?reason.message:"تعذر تحليل الطلب.");}finally{setBusy(false)}
  }
  async function confirm(){
    if(!preview||!selected.length)return;setBusy(true);setError("");
    try{const result=await projectApi.assistantConfirm(projectId,{preview_token:preview.preview_token,proposal_ids:selected});await onConfirmed();setSuccess(`تم اعتماد ${result.created_rules.length} قاعدة وإضافتها إلى المشروع.`);setPreview(null);setSelected([]);}
    catch(reason){setError(reason instanceof Error?reason.message:"تعذر اعتماد القواعد.");}finally{setBusy(false)}
  }
  return <section className="assistant-panel" aria-labelledby="assistant-title">
    <div className="section-heading"><div><p className="eyebrow">مساعد حتمي بدون إنترنت</p><h2 id="assistant-title">اكتب قاعدتك بالعربية</h2><p>سنعرض معاينة مفهومة؛ لن تُحفظ أي قاعدة قبل اعتمادك.</p></div></div>
    <form onSubmit={parse}><label htmlFor="assistant-request">طلب قاعدة الجدولة</label><textarea id="assistant-request" value={text} onChange={e=>{setText(e.target.value);setPreview(null);setResolutions({})}} rows={3} placeholder="مثال: لا تضع للأستاذ أحمد الحصة الأولى يوم الأحد" required/><div className="assistant-examples">{examples.map(x=><button type="button" key={x} onClick={()=>{setText(x);setPreview(null)}}>{x}</button>)}</div><button className="primary" disabled={busy||!text.trim()}>{busy?"جارٍ التحليل…":"معاينة القاعدة"}</button></form>
    {error&&<p className="error-banner" role="alert">{error}</p>}{success&&<p className="success-banner" role="status">{success}</p>}
    {preview?.clarifications.map(item=><fieldset className="clarification" key={item.key}><legend>{item.question}</legend>{item.choices.map(choice=><label key={choice.id}><input type="radio" name={item.key} checked={resolutions[item.key]===choice.id} onChange={()=>setResolutions(x=>({...x,[item.key]:choice.id}))}/><span>{choice.label}{choice.context&&<small>{choice.context}</small>}</span></label>)}<button type="button" disabled={!resolutions[item.key]||busy} onClick={()=>void parse()}>متابعة بعد التوضيح</button></fieldset>)}
    {preview?.warnings.map((warning,index)=><p className="assistant-warning" role="status" key={`${warning.code}-${index}`}>{warning.message??`لم يمكن فهم الطلب بأمان (${warning.code}).`}</p>)}
    {preview?.proposals.length?<div className="assistant-preview"><h3>معاينة قبل الحفظ</h3>{preview.proposals.map(proposal=><label className="proposal-card" key={proposal.id}><input type="checkbox" checked={selected.includes(proposal.id)} onChange={e=>setSelected(x=>e.target.checked?[...x,proposal.id]:x.filter(id=>id!==proposal.id))}/><span><strong>{proposal.arabic_summary}</strong><small>{proposal.severity==="hard"?"قاعدة إلزامية":`تفضيل · وزن ${proposal.weight}`}</small></span></label>)}<p>سيعيد الخادم التحقق من القواعد والنطاق عند الاعتماد.</p><button className="primary" disabled={busy||!selected.length} onClick={()=>void confirm()}>اعتماد القواعد المحددة</button></div>:null}
  </section>
}
