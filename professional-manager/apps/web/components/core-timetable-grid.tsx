"use client";

import Link from "next/link";
import { type CSSProperties, useCallback, useEffect, useMemo, useState } from "react";
import { type CoreSnapshot } from "@/lib/core-api";
import { projectApi, type CandidateDetail, type PlacementExplanation, type QualityReport, type SolveRun, type TimetableEntry } from "@/lib/project-api";
import { TimetableEditor } from "@/components/timetable-editor";

const dayNames = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
type GridView = "section" | "teacher" | "subject" | "resource";
type Row = { id: string; label: string };

function minute(value: string) {
  const [hours, minutes] = value.split(":").map(Number);
  return hours * 60 + minutes;
}
function clock(value: number) { return `${String(Math.floor(value / 60)).padStart(2,"0")}:${String(value % 60).padStart(2,"0")}`; }
function hue(id: string) { return Array.from(id).reduce((sum,character)=>sum+character.charCodeAt(0),0)%360; }

export function CoreTimetableGrid({data,runId}:{data:CoreSnapshot;runId:string}) {
  const [run,setRun]=useState<SolveRun|null>(null);
  const [candidate,setCandidate]=useState<CandidateDetail|null>(null);
  const [view,setView]=useState<GridView>("section");
  const [week,setWeek]=useState(0);
  const [selected,setSelected]=useState<TimetableEntry|null>(null);
  const [quality,setQuality]=useState<QualityReport|null>(null);
  const [explanation,setExplanation]=useState<PlacementExplanation|null>(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);

  const openCandidate=useCallback(async (candidateId:string) => {
    setLoading(true); setError(""); setSelected(null); setExplanation(null); setQuality(null);
    try { setCandidate(await projectApi.candidate(data.project_id,candidateId)); }
    catch(reason){ setError((reason as Error).message); }
    finally { setLoading(false); }
  },[data.project_id]);

  useEffect(()=>{
    let cancelled=false; let timer:number|undefined;
    async function refresh(){
      try {
        const next=runId?await projectApi.solveRun(data.project_id,runId):await projectApi.latestSolve(data.project_id);
        if(cancelled)return;
        setRun(next);
        if(next?.status==="completed"&&next.candidates.length){
          const currentStillExists=next.candidates.some(item=>item.id===candidate?.id);
          if(!currentStillExists) await openCandidate(next.candidates[0].id);
        } else if(next?.status==="queued"||next?.status==="running") {
          timer=window.setTimeout(()=>void refresh(),1500);
        }
      } catch(reason){ if(!cancelled)setError((reason as Error).message); }
    }
    void refresh();
    return ()=>{cancelled=true;if(timer)window.clearTimeout(timer)};
  },[candidate?.id,data.project_id,openCandidate,runId]);

  const lessons=useMemo(()=>data.blocks.filter(item=>item.block_type==="lesson"&&item.period_number!==null).sort((a,b)=>(a.period_number??0)-(b.period_number??0)),[data.blocks]);
  const weeks=useMemo(()=>candidate?[...new Set(candidate.entries.map(item=>item.project_cycle_week_index))].sort((a,b)=>a-b):[0],[candidate]);
  const rows=useMemo<Row[]>(()=>{
    if(view==="section") return data.sections.map(section=>({id:section.id,label:section.name_ar}));
    if(view==="teacher") return data.teachers.map(teacher=>({id:teacher.id,label:teacher.name_ar}));
    if(view==="subject") return data.subjects.map(subject=>({id:subject.id,label:subject.name_ar}));
    const resources=candidate?.entries.flatMap(item=>item.resources)??[];
    return [...new Map(resources.map(item=>[item.id,{id:item.id,label:item.name_ar}])).values()];
  },[candidate?.entries,data.sections,data.subjects,data.teachers,view]);
  function entriesFor(row:Row,weekday:number,startsAt:number){
    return (candidate?.entries??[]).filter(entry=>entry.project_cycle_week_index===week&&entry.weekday_index===weekday&&entry.starts_at_minute===startsAt&&(view==="section"?entry.sections.some(item=>item.id===row.id):view==="teacher"?entry.teachers.some(item=>item.id===row.id):view==="subject"?entry.subject.id===row.id:entry.resources.some(item=>item.id===row.id)));
  }
  function secondary(entry:TimetableEntry){
    if(view==="teacher")return entry.sections.map(item=>item.name_ar).join(" + ");
    if(view==="section")return entry.teachers.map(item=>item.name_ar).join(" + ");
    if(view==="subject")return entry.sections.map(item=>item.name_ar).join(" + ");
    return `${entry.subject.name_ar} · ${entry.sections.map(item=>item.name_ar).join(" + ")}`;
  }
  function unavailable(row:Row,weekday:number,period:number){return view==="teacher"&&data.teachers.find(item=>item.id===row.id)?.availability.some(item=>item.weekday_index===weekday&&item.period_number===period&&item.state==="unavailable");}
  function rememberTeacher(entry:TimetableEntry){const teacher=entry.teachers[0];if(teacher)window.localStorage.setItem("pm-selected-teacher",teacher.id);}

  if(!run)return <section className="core-card timetable-result-empty"><div><span>شبكة الجدول</span><h2>أنشئ الجدول لتظهر النتيجة هنا مباشرة</h2><p>بعد التوليد يمكنك التبديل بين الفصول والمعلمين والمواد والموارد دون مغادرة الشاشة.</p></div></section>;
  const active=run.status==="queued"||run.status==="running";
  return <section className="core-card timetable-workbench" aria-label="شبكة الجدول الأسبوعية">
    <header className="timetable-workbench-head"><div><span className="eyebrow">نتيجة التوليد</span><h2>{active?"يجري بناء البدائل…":"الجدول الأسبوعي"}</h2><p>{active?"ستظهر الشبكة تلقائيًا فور اكتمال التوزيع.":`${candidate?.entries.length??0} حصة موزعة في البديل الحالي.`}</p></div><div className="timetable-head-actions"><Link href="/reports">طباعة وتصدير</Link>{candidate&&<button type="button" onClick={()=>void projectApi.candidateQuality(data.project_id,candidate.id).then(setQuality).catch(reason=>setError((reason as Error).message))}>جودة الجدول</button>}</div></header>
    {active&&<div className="generation-progress" role="status"><i/><strong>جاري إنشاء البدائل الثلاثة باستخدام قواعد المدرسة…</strong></div>}
    {error&&<div className="error-banner" role="alert">{error}</div>}
    {!active&&run.diagnostics.length>0&&<details className="generation-diagnostics"><summary>ملاحظات التوزيع ({run.diagnostics.length})</summary>{run.diagnostics.map((item,index)=><article key={`${item.code}-${index}`}><strong>{item.message??"تعذر توزيع بعض الحصص"}</strong>{item.unscheduled_assignments?.map(assignment=><p key={assignment.assignment_id}>{assignment.subject} · {assignment.sections.join("، ")} · {assignment.teachers.join(" + ")} — بقي {assignment.unscheduled_count}</p>)}{item.suggested_remediation&&<span>{item.suggested_remediation}</span>}</article>)}</details>}
    {run.candidates.length>0&&<div className="candidate-switcher" aria-label="بدائل الجدول">{run.candidates.map(item=><button type="button" className={candidate?.id===item.id?"active":""} key={item.id} onClick={()=>void openCandidate(item.id)}><strong>البديل {item.rank}</strong><span>{item.total_penalty===0?"بلا جزاءات تفضيلية":`${item.total_penalty} جزاء تفضيلي`}</span></button>)}</div>}
    {candidate&&<>
      <div className="grid-toolbar"><div className="segmented" aria-label="طريقة عرض الجدول">{([["section","الفصول"],["teacher","المعلمون"],["subject","المواد"],["resource","الموارد"]] as [GridView,string][]).map(([key,label])=><button type="button" key={key} className={view===key?"selected":""} onClick={()=>{setView(key);setSelected(null)}}>{label}</button>)}</div>{weeks.length>1&&<div className="week-switcher">{weeks.map(item=><button type="button" className={week===item?"active":""} key={item} onClick={()=>setWeek(item)}>الأسبوع {item+1}</button>)}</div>}<span className="grid-legend"><i className="unavailable"/> غير متاح</span></div>
      {loading?<div className="skeleton grid-skeleton" aria-label="جار تحميل البديل"/>:rows.length?<div className="weekly-grid-scroll"><table className="weekly-grid"><thead><tr><th rowSpan={2}>الاسم</th>{data.weekdays.map(day=><th colSpan={lessons.length} key={day}>{dayNames[day]}</th>)}</tr><tr>{data.weekdays.flatMap(day=>lessons.map(block=><th key={`${day}-${block.id}`}><b>{block.period_number}</b><small>{block.starts_at.slice(0,5)}</small></th>))}</tr></thead><tbody>{rows.map(row=><tr key={row.id}><th>{row.label}</th>{data.weekdays.flatMap(day=>lessons.map(block=>{const matches=entriesFor(row,day,minute(block.starts_at));const entry=matches[0];const isUnavailable=unavailable(row,day,block.period_number??0);return <td key={`${row.id}-${day}-${block.id}`} className={`${isUnavailable?"is-unavailable":""} ${entry?"has-lesson":""}`}>{entry?<button type="button" className={selected?.occurrence_id===entry.occurrence_id?"selected":""} style={{"--subject-hue":hue(entry.subject.id)} as CSSProperties} onClick={()=>setSelected(entry)}><strong>{entry.subject.name_ar}</strong><span>{secondary(entry)}</span>{matches.length>1&&<small>+ {matches.length-1}</small>}</button>:<span className="empty-cell">{isUnavailable?"غير متاح":""}</span>}</td>}))}</tr>)}</tbody></table></div>:<div className="soft-empty">لا توجد {view==="resource"?"موارد مستخدمة في هذا البديل":"بيانات لهذا العرض"}.</div>}
      {selected&&<aside className="lesson-inspector"><div><span>{dayNames[selected.weekday_index]} · {clock(selected.starts_at_minute)}–{clock(selected.ends_at_minute)}</span><h3>{selected.subject.name_ar}</h3><p>{selected.sections.map(item=>item.name_ar).join(" + ")} · {selected.teachers.map(item=>item.name_ar).join(" + ")}</p>{selected.resources.length>0&&<p>المورد: {selected.resources.map(item=>item.name_ar).join(" + ")}</p>}</div><div><button type="button" onClick={()=>void projectApi.candidateExplanation(data.project_id,candidate.id,selected.occurrence_id).then(setExplanation).catch(reason=>setError((reason as Error).message))}>لماذا هنا؟</button>{selected.teachers.length>0&&<Link href="/teachers" onClick={()=>rememberTeacher(selected)}>تفريغ المعلم</Link>}{selected.teachers.length>0&&<Link href="/teachers" onClick={()=>rememberTeacher(selected)}>نسخ القيود</Link>}<Link href="/reports">طباعة</Link></div></aside>}
      {quality&&<aside className="quality-panel core-quality"><h3>جودة الجدول</h3><p>المخالفات الإلزامية: <strong>{quality.hard_violations.length}</strong></p><p>مجموع الجزاء الموزون: <strong>{quality.total_weighted_penalty}</strong></p><p>فجوات المعلمين: <strong>{quality.teacher_gap_total}</strong></p><button type="button" onClick={()=>setQuality(null)}>إغلاق</button></aside>}
      {explanation&&<aside className="explanation-panel core-explanation"><h3>لماذا وُضعت هنا؟</h3><p>الوقت المختار: {dayNames[explanation.chosen_slot.weekday_index]} {clock(explanation.chosen_slot.starts_at_minute)}</p><p>{explanation.mandatory_rule_facts.length} قواعد إلزامية و{explanation.preference_rule_facts.length} قواعد تفضيلية أثرت في الاختيار.</p>{explanation.alternatives.slice(0,4).map(item=><p key={item.slot.id}>{item.status==="blocked"?"بديل مرفوض":item.status==="valid_but_worse"?"بديل صالح لكنه أسوأ":"بديل صالح"} · {dayNames[item.slot.weekday_index]} {clock(item.slot.starts_at_minute)} · فرق الجزاء {item.penalty_delta}</p>)}<button type="button" onClick={()=>setExplanation(null)}>إغلاق</button></aside>}
      <TimetableEditor projectId={data.project_id} candidate={candidate}/>
    </>}
  </section>;
}
