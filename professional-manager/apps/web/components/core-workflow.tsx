"use client";

import Link from "next/link";
import { FormEvent, type ReactNode, useCallback, useEffect, useState } from "react";
import { coreApi, type AvailabilityCell, type BulkTeacherResult, type CoreAssignment, type CoreSnapshot } from "@/lib/core-api";
import { ArabicNumberInput } from "@/components/arabic-number-input";
import { CoreTimetableGrid } from "@/components/core-timetable-grid";

const steps = [
  ["/setup", "المدرسة واليوم الدراسي"], ["/academic-structure", "الصفوف والفصول"],
  ["/teachers", "المعلمون"], ["/assignments", "المواد والإسناد"],
  ["/constraints", "التوفر والقيود"], ["/timetables", "إنشاء الجدول"],
] as const;
const weekdays = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس"];
const gradeSets = {
  primary: ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس"],
  intermediate: ["الأول المتوسط", "الثاني المتوسط", "الثالث المتوسط"],
  secondary: ["الأول الثانوي", "الثاني الثانوي", "الثالث الثانوي"],
} as const;

function value(form: FormData, key: string) { return String(form.get(key) ?? ""); }
function statusClass(value: boolean) { return value ? "ready" : "missing"; }
function moved(ids: string[], id: string, direction: -1 | 1) { const index=ids.indexOf(id), target=index+direction;if(index<0||target<0||target>=ids.length)return ids;const next=[...ids];[next[index],next[target]]=[next[target],next[index]];return next; }
function teacherNameKey(name: string) {
  return name.normalize("NFKD").replace(/[\u064B-\u065F\u0670\u0640]/g, "").replace(/[أإآٱ]/g, "ا").replace(/ى/g, "ي").replace(/ة/g, "ه").replace(/ؤ/g, "و").replace(/ئ/g, "ي").replace(/[^\p{L}]/gu, "").toLocaleLowerCase("ar");
}
function editDistance(left: string, right: string) {
  let previous=Array.from({length:right.length+1},(_,index)=>index);
  for(let i=1;i<=left.length;i++){const current=[i];for(let j=1;j<=right.length;j++)current[j]=Math.min(current[j-1]+1,previous[j]+1,previous[j-1]+(left[i-1]===right[j-1]?0:1));previous=current;} return previous[right.length];
}
function similarNames(name: string, existing: string[]) { const key=teacherNameKey(name); return existing.filter(item=>{const other=teacherNameKey(item);return key===other||editDistance(key,other)<=(Math.max(key.length,other.length)<8?1:2)}); }
type Confirmation = { title: string; message: string; confirmLabel: string; danger?: boolean; action: () => void };
function ConfirmDialog({title,message,confirmLabel,danger=false,onCancel,onConfirm}:{title:string;message:string;confirmLabel:string;danger?:boolean;onCancel:()=>void;onConfirm:()=>void}) {
  return <div className="dialog-backdrop"><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="core-confirm-title"><h2 id="core-confirm-title">{title}</h2><p>{message}</p><div className="dialog-actions"><button type="button" className="secondary" onClick={onCancel}>إلغاء</button><button type="button" className={danger?"danger-button":"primary"} onClick={onConfirm}>{confirmLabel}</button></div></section></div>;
}
function initialCurriculum(data: CoreSnapshot) {
  const result: Record<string,number> = Object.fromEntries((data.curriculum??[]).map(item=>[`${item.grade_id}:${item.subject_id}`,item.weekly_occurrences]));
  for (const assignment of data.assignments) for (const sectionId of assignment.section_ids) {
    const section=data.sections.find(item=>item.id===sectionId); if(!section) continue;
    const key=`${section.grade_id}:${assignment.subject_id}`;
    if(!(key in result)) result[key]=Math.max(result[key]??0,assignment.weekly_occurrences);
  }
  return result;
}

export function CoreWorkflow({ step }: { step: number }) {
  const [schoolId, setSchoolId] = useState("");
  const [data, setData] = useState<CoreSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [generationRunId, setGenerationRunId] = useState("");
  const load = useCallback(async (id?: string, silent = false) => {
    const selected = id ?? localStorage.getItem("pm-school") ?? "";
    if (!selected) { setLoading(false); return; }
    setSchoolId(selected);
    if (!silent) setLoading(true);
    try { setData(await coreApi.snapshot(selected)); setError(""); }
    catch (reason) { setError((reason as Error).message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    const handler = (event: Event) => void load((event as CustomEvent<string>).detail);
    window.addEventListener("pm-school-change", handler);
    return () => { window.clearTimeout(timer); window.removeEventListener("pm-school-change", handler); };
  }, [load]);
  async function act(action: () => Promise<unknown>, message: string) {
    setBusy(true); setError("");
    try { await action(); setNotice(message); await load(schoolId, true); window.setTimeout(() => setNotice(""), 2800); }
    catch (reason) { setError((reason as Error).message); }
    finally { setBusy(false); }
  }
  async function addTeachers(action: () => Promise<BulkTeacherResult>) {
    setBusy(true); setError("");
    try { const result = await action(); setNotice(`تمت إضافة ${result.created} معلم${result.skipped ? `، وتجاهل ${result.skipped} مكرر` : ""}`); await load(schoolId, true); }
    catch (reason) { setError((reason as Error).message); }
    finally { setBusy(false); }
  }
  if (loading) return <section className="content"><div className="skeleton" aria-label="جار تحميل المسار الأساسي" /></section>;
  if (!schoolId || !data) return <section className="content"><div className="empty-state"><h2>تعذر فتح المدرسة</h2><p>{error || "اختر مدرسة للبدء."}</p></div></section>;
  return <section className="content core-workflow">
    <div className="core-heading"><div><span className="eyebrow">المسار الأساسي</span><h1>{steps[step - 1][1]}</h1><p>أدخل ما تعرفه فقط، ويتولى النظام التفاصيل الداخلية تلقائيًا.</p></div><span className="step-counter">الخطوة {step} من 6</span></div>
    <nav className="core-steps" aria-label="خطوات إنشاء الجدول">{steps.map(([href, label], index) => <Link key={href} href={href} className={index + 1 === step ? "active" : ""}><b>{index + 1}</b><span>{label}</span></Link>)}</nav>
    {notice && <div className="success-banner" role="status">{notice}</div>}{error && <div className="error-banner" role="alert">{error}</div>}
    {step === 1 && <SchoolDayStep data={data} busy={busy} onSave={(payload) => act(async () => { await coreApi.saveDay(schoolId, payload); window.dispatchEvent(new Event("pm-schools-refresh")); }, "تم حفظ اسم المدرسة وإنشاء اليوم الدراسي")} onEdit={(blockId,payload)=>act(()=>coreApi.editPeriod(schoolId,blockId,payload),"تم تعديل الفترة وإعادة احتساب ما يليها")} />}
    {step === 2 && <StructureStep data={data} busy={busy} onSave={(payload) => act(() => coreApi.saveStructure(schoolId, payload), "تم إنشاء الصفوف والفصول تلقائيًا")} onUpdate={(id,name_ar)=>act(()=>coreApi.updateSection(schoolId,id,{name_ar}),"تم تعديل اسم الفصل")} onDelete={(id)=>act(()=>coreApi.deleteSection(schoolId,id),"تم حذف الفصل")} onOrder={(ids)=>act(()=>coreApi.orderSections(schoolId,ids),"تم حفظ ترتيب الفصول")} />}
    {step === 3 && <><BulkTeacherEntry data={data} busy={busy} onPaste={(names, limit, allowSimilar) => addTeachers(() => coreApi.createTeachers(schoolId, names, limit, allowSimilar))} onFile={(file, limit) => addTeachers(() => coreApi.uploadTeachers(schoolId,file,limit))} /><ManagedTeachersStep data={data} busy={busy} onCreate={(payload) => act(() => coreApi.createTeacher(schoolId, payload), "تمت إضافة المعلم")} onUpdate={(id,payload)=>act(()=>coreApi.updateTeacher(schoolId,id,payload),"تم تعديل بيانات المعلم")} onDelete={(id,cascade)=>act(()=>coreApi.deleteTeacher(schoolId,id,cascade),"تم حذف المعلم وإسناداته، وأصبحت حصصه شاغرة")} onMerge={(source,target)=>act(()=>coreApi.mergeTeachers(schoolId,source,target),"تم دمج الاسمين وتصحيح الإسنادات والنصاب")} onOrder={(ids)=>act(()=>coreApi.orderTeachers(schoolId,ids),"تم حفظ ترتيب المعلمين")} onAvailability={(teacherId, cells) => act(() => coreApi.saveAvailability(schoolId, teacherId, { cells }), "تم حفظ توفر المعلم")} onCopy={(source, targets) => act(() => coreApi.copyAvailability(schoolId, { source_teacher_id: source, target_teacher_ids: targets }), "تم نسخ التوفر والقيود")} /></>}
    {step === 4 && <MaterialsAndAssignmentsTabs plan={<CurriculumPlan data={data} busy={busy} onSubject={(name_ar)=>act(()=>coreApi.createSubject(schoolId,{name_ar}),"تمت إضافة المادة")} onSubjectUpdate={(id,name_ar)=>act(()=>coreApi.updateSubject(schoolId,id,{name_ar}),"تم تعديل المادة")} onSubjectDelete={(id)=>act(()=>coreApi.deleteSubject(schoolId,id),"تم حذف المادة")} onSubjectOrder={(ids)=>act(()=>coreApi.orderSubjects(schoolId,ids),"تم حفظ ترتيب المواد")} onSave={(cells)=>act(()=>coreApi.saveCurriculum(schoolId,cells),"تم حفظ الخطة الدراسية وحساب احتياج المدرسة")} />} assignments={<AssignmentsStep data={data} busy={busy} onSubject={(name_ar) => act(() => coreApi.createSubject(schoolId, { name_ar }), "تمت إضافة المادة")} onAssign={(payload) => act(() => coreApi.createAssignment(schoolId, payload), "تم حفظ الإسناد وتحديث النصاب")} onUpdate={(id,payload)=>act(()=>coreApi.updateAssignment(schoolId,id,payload),"تم تعديل الإسناد وتحديث النصاب")} onDelete={(id)=>act(()=>coreApi.deleteAssignment(schoolId,id),"تم حذف الإسناد وتحديث النصاب")} onDeduplicate={(teacherId)=>act(()=>coreApi.deduplicateAssignments(schoolId,teacherId),"تم حذف الإسنادات المكررة وتصحيح النصاب")} onTransfer={(payload)=>act(()=>coreApi.transferAssignments(schoolId,payload),"تم نقل الإسنادات إلى المعلم الجديد")} />} />}
    {step === 5 && <ConstraintsStep data={data} busy={busy} onRule={(payload) => act(() => coreApi.createRule(schoolId, payload), "تم تطبيق القاعدة")} />}
    {step === 6 && <GenerateStep data={data} busy={busy} runId={generationRunId} onGenerate={async (profile) => { setBusy(true); setError(""); try { const result = await coreApi.generate(schoolId, profile); if (!result.started) { setError(result.preflight.diagnostics.map(item => item.message).join("، ") || "أكمل بيانات الجاهزية أولًا."); } else { setGenerationRunId(result.run_id??""); setNotice(result.partial?"بدأ إنشاء جدول جزئي؛ ستظهر الحصص غير الموزعة بوضوح مع أسبابها.":"بدأ إنشاء ثلاثة بدائل للجدول"); } } catch (reason) { setError((reason as Error).message); } finally { setBusy(false); } }} />}
  </section>;
}

function BulkTeacherEntry({ data, busy, onPaste, onFile }: { data: CoreSnapshot; busy: boolean; onPaste: (names: string[], limit: number, allowSimilar: boolean) => void; onFile: (file: File, limit: number) => void }) {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [limit, setLimit] = useState(24);
  const [similarReview, setSimilarReview] = useState<string[]>([]);
  const names = text.split(/\r?\n|[,،;]+/).map((line) => line.split("\t")[0].trim()).filter(Boolean);
  return <article className="core-card bulk-teachers">
    <div className="card-title"><div><h2>إضافة المعلمين دفعة واحدة</h2><p>الصق الأسماء من Notepad أو من عمود في Excel، اسم واحد في كل سطر.</p></div><span className="bulk-count">{names.length} اسم</span></div>
    <div className="bulk-teacher-grid">
      <label className="bulk-paste">لصق الأسماء<textarea aria-label="أسماء المعلمين" value={text} onChange={(event) => setText(event.target.value)} placeholder={"أحمد محمد\nسارة علي\nخالد حسن"} rows={7} /></label>
      <div className="bulk-file"><label>النصاب الافتراضي<ArabicNumberInput aria-label="النصاب الافتراضي للقائمة" min="1" max="60" value={limit} onChange={(event) => setLimit(Number(event.target.value))} /></label><label className="file-choice">ملف Excel أو CSV<input aria-label="ملف أسماء المعلمين" type="file" accept=".xlsx,.csv,.txt" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><strong>{file?.name ?? "اختر ملفًا"}</strong></label><button type="button" disabled={busy || !file} onClick={() => file && onFile(file, limit)}>استيراد الملف</button></div>
    </div>
    <button type="button" className="primary core-primary" disabled={busy || !names.length} onClick={() => {const duplicates=names.flatMap(name=>similarNames(name,data.teachers.map(item=>item.name_ar)).map(match=>`${name} ↔ ${match}`));if(duplicates.length){setSimilarReview(duplicates);return}onPaste(names,limit,false)}}>إضافة جميع الأسماء</button>
    {similarReview.length>0&&<ConfirmDialog title="راجع الأسماء المتشابهة" message={`وجدنا: ${similarReview.join("، ")}. هل تريد الاحتفاظ بها كمعلمين مستقلين؟`} confirmLabel="الاحتفاظ وإضافة الأسماء" onCancel={()=>setSimilarReview([])} onConfirm={()=>{onPaste(names,limit,true);setSimilarReview([])}} />}
  </article>;
}

function SchoolDayStep({ data, busy, onSave, onEdit }: { data: CoreSnapshot; busy: boolean; onSave: (payload: object) => void; onEdit: (blockId:string,payload:object)=>void }) {
  const [secondBreak, setSecondBreak] = useState(false);
  const [customDuration, setCustomDuration] = useState(false);
  const [prayerMode, setPrayerMode] = useState<"none"|"after"|"fixed">("none");
  const [editingId, setEditingId] = useState("");
  const editing = data.blocks.find(block=>block.id===editingId);
  useEffect(() => {
    document.querySelectorAll<HTMLInputElement>('.day-builder input[name="stages"]').forEach((input) => {
      input.checked = data.selected_stages.includes(input.value as "primary" | "intermediate" | "secondary");
    });
  }, [data.selected_stages]);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const breaks = [{ after_period: Number(value(form, "break_after")), duration_minutes: Number(value(form, "break_minutes")) }];
    if (secondBreak) breaks.push({ after_period: Number(value(form, "break2_after")), duration_minutes: Number(value(form, "break2_minutes")) });
    const prayer = prayerMode === "after" ? { after_period: Number(value(form,"prayer_after")), duration_minutes: Number(value(form,"prayer_minutes")) } : prayerMode === "fixed" ? { fixed_time: value(form,"prayer_time"), duration_minutes: Number(value(form,"prayer_minutes")) } : null;
    onSave({ school_name: value(form, "school_name"), stages: form.getAll("stages"), weekdays: form.getAll("weekdays").map(Number), period_count: Number(value(form, "period_count")), assembly_start: value(form, "assembly_start"), assembly_minutes: Number(value(form, "assembly_minutes")), period_minutes: Number(value(form, customDuration ? "custom_period_minutes" : "period_minutes")), breaks, prayer });
  }
  return <div className="core-grid"><form className="core-card day-builder" onSubmit={submit}><div className="card-title"><div><h2>بيانات المدرسة واليوم</h2><p>الإعداد الافتراضي مدرسة صباحية، من الأحد إلى الخميس.</p></div></div><label>اسم المدرسة<input name="school_name" defaultValue={data.school.name_ar} required /></label><fieldset><legend>المرحلة</legend><div className="choice-row">{[["primary","ابتدائي"],["intermediate","متوسط"],["secondary","ثانوي"]].map(([key,label]) => <label className="choice" key={key}><input type="checkbox" name="stages" value={key} defaultChecked={key === "primary"}/>{label}</label>)}</div></fieldset><fieldset><legend>أيام الدراسة</legend><div className="choice-row">{weekdays.map((day,index)=><label className="choice" key={day}><input type="checkbox" name="weekdays" value={index} defaultChecked/>{day}</label>)}</div></fieldset><div className="form-row three"><label>عدد الحصص<input name="period_count" type="number" min="1" max="20" defaultValue="7" required /></label><label>بداية الطابور<input name="assembly_start" type="time" defaultValue="06:45" required /></label><label>مدة الطابور<input name="assembly_minutes" type="number" min="0" defaultValue="15" required /></label></div><fieldset><legend>مدة الحصة</legend><div className="choice-row">{[40,45,50].map(minutes=><label className="choice" key={minutes}><input type="radio" name="period_minutes" value={minutes} defaultChecked={minutes===45} onChange={()=>setCustomDuration(false)}/>{minutes} دقيقة</label>)}<label className="choice"><input type="radio" name="duration_mode" onChange={()=>setCustomDuration(true)}/>مخصص</label></div>{customDuration && <input aria-label="مدة حصة مخصصة" name="custom_period_minutes" type="number" min="20" max="120" defaultValue="45" />}</fieldset><div className="form-row"><label>الفسحة بعد الحصة<input name="break_after" type="number" min="1" defaultValue="2" required /></label><label>مدة الفسحة<input name="break_minutes" type="number" min="5" defaultValue="20" required /></label></div>{secondBreak && <div className="form-row"><label>الفسحة الثانية بعد<input name="break2_after" type="number" min="1" defaultValue="5" required /></label><label>مدتها<input name="break2_minutes" type="number" min="5" defaultValue="10" required /></label></div>}<button type="button" className="inline-action" onClick={()=>setSecondBreak(!secondBreak)}>{secondBreak ? "إلغاء الفسحة الثانية" : "+ إضافة فسحة ثانية"}</button><div className="form-row three"><label>الصلاة<select aria-label="طريقة إضافة الصلاة" value={prayerMode} onChange={event=>setPrayerMode(event.target.value as typeof prayerMode)}><option value="none">بدون صلاة</option><option value="after">بعد حصة</option><option value="fixed">وقت ثابت</option></select></label>{prayerMode==="after"&&<label>بعد الحصة<select name="prayer_after" defaultValue="4">{Array.from({length:7},(_,index)=><option value={index+1} key={index}>{index+1}</option>)}</select></label>}{prayerMode==="fixed"&&<label>وقت الصلاة<input type="time" name="prayer_time" defaultValue="10:20"/></label>}{prayerMode!=="none"&&<label>مدة الصلاة<input name="prayer_minutes" type="number" min="5" defaultValue="15" /></label>}</div><button className="primary core-primary" disabled={busy}>إنشاء التوقيت تلقائيًا</button></form><article className="core-card day-preview"><div className="card-title"><div><h2>معاينة اليوم</h2><p>يمكن تعديل أي فترة بعد الإنشاء، مع إعادة احتساب ما يليها.</p></div><span className="live-badge">متتابع</span></div>{data.blocks.length ? <div className="period-list">{data.blocks.map(block=><div className={`period-row ${block.block_type}`} key={block.id}><time>{block.starts_at.slice(0,5)}<i>←</i>{block.ends_at.slice(0,5)}</time><strong>{block.label_ar}</strong><button type="button" className="period-edit" onClick={()=>setEditingId(block.id)}>تعديل</button></div>)}</div> : <div className="soft-empty">اضغط «إنشاء التوقيت تلقائيًا» لمشاهدة اليوم كاملًا.</div>}{editing&&<form className="period-editor" onSubmit={event=>{event.preventDefault();const form=new FormData(event.currentTarget);onEdit(editing.id,{block_order:editing.block_order,label_ar:value(form,"label"),block_type:editing.block_type,period_number:editing.period_number,starts_at:value(form,"starts"),ends_at:value(form,"ends"),recalculate_following:form.get("recalculate")==="on"});setEditingId("");}}><h3>تعديل {editing.label_ar}</h3><input aria-label="مسمى الفترة" name="label" defaultValue={editing.label_ar}/><div className="form-row"><label>من<input name="starts" type="time" defaultValue={editing.starts_at.slice(0,5)}/></label><label>إلى<input name="ends" type="time" defaultValue={editing.ends_at.slice(0,5)}/></label></div><label className="recalc-option"><input name="recalculate" type="checkbox" defaultChecked/> إعادة احتساب الفترات التالية تلقائيًا</label><div><button type="button" onClick={()=>setEditingId("")}>إلغاء</button><button disabled={busy}>حفظ التعديل</button></div></form>}</article></div>;
}

function StructureStep({ data, busy, onSave, onUpdate, onDelete, onOrder }: { data: CoreSnapshot; busy: boolean; onSave: (payload: object) => void; onUpdate:(id:string,name:string)=>void; onDelete:(id:string)=>void; onOrder:(ids:string[])=>void }) {
  const [view,setView]=useState<"create"|"manage">("create");
  const [stage, setStage] = useState<keyof typeof gradeSets>(data.selected_stages[0] ?? "primary");
  const [namingPattern,setNamingPattern]=useState<"grade_letter"|"number_slash_number"|"number_dash_number"|"number_slash_letter">("grade_letter");
  const [counts, setCounts] = useState<Record<string, number>>(()=>Object.fromEntries(data.grades.map(grade=>[grade.name_ar,data.sections.filter(section=>section.grade_id===grade.id).length])));
  const [selectedSectionId, setSelectedSectionId] = useState(data.sections[0]?.id??"");
  const [sectionName, setSectionName] = useState(data.sections[0]?.name_ar??"");
  const [deletingSectionId, setDeletingSectionId] = useState("");
  const grades = gradeSets[stage];
  const visibleGrades = data.grades.filter(grade=>(grades as readonly string[]).includes(grade.name_ar));
  const visibleSections = visibleGrades.flatMap(grade=>data.sections.filter(section=>section.grade_id===grade.id).map(section=>({section,grade})));
  const selectedItem = visibleSections.find(item=>item.section.id===selectedSectionId)??visibleSections[0];
  const activeSectionId = selectedItem?.section.id??"";
  const deletingSection = data.sections.find(section=>section.id===deletingSectionId);
  function selectSection(id:string,name:string){setSelectedSectionId(id);setSectionName(name)}
  function selectStage(nextStage:keyof typeof gradeSets){
    setStage(nextStage);
    const nextNames=gradeSets[nextStage] as readonly string[];
    const firstGrade=data.grades.find(grade=>nextNames.includes(grade.name_ar));
    const firstSection=data.sections.find(section=>section.grade_id===firstGrade?.id);
    setSelectedSectionId(firstSection?.id??"");setSectionName(firstSection?.name_ar??"");
  }
  function exampleName(gradeIndex:number){const letter="أ";if(namingPattern==="number_slash_number")return `${gradeIndex+1} / 1`;if(namingPattern==="number_dash_number")return `${gradeIndex+1} ـ 1`;if(namingPattern==="number_slash_letter")return `${gradeIndex+1} / ${letter}`;return `${grades[gradeIndex]} ${letter}`}
  function moveSelected(direction:-1|1){
    if(!selectedItem)return;
    const sectionIds=data.sections.filter(section=>section.grade_id===selectedItem.grade.id).map(section=>section.id);
    const nextGradeOrder = moved(sectionIds, selectedItem.section.id, direction);
    let index = 0;
    onOrder(data.sections.map(section => sectionIds.includes(section.id) ? nextGradeOrder[index++] : section.id));
  }
  return <div className="core-card structure-workspace">
    <div className="structure-toolbar"><div><h2>الصفوف والفصول</h2><p>{view==="create"?"معالج سريع لإنشاء الصفوف وتسميتها دفعة واحدة.":"حدّد فصلًا من القائمة، ثم عدّل بياناته."}</p></div><label className="stage-filter">المرحلة<select className="compact-select" value={stage} onChange={event=>selectStage(event.target.value as keyof typeof gradeSets)}><option value="primary">ابتدائي</option><option value="intermediate">متوسط</option><option value="secondary">ثانوي</option></select></label></div>
    <div className="structure-tabs" role="tablist" aria-label="أوضاع الصفوف والفصول"><button type="button" role="tab" aria-selected={view==="create"} className={view==="create"?"active":""} onClick={()=>setView("create")}>إنشاء الصفوف والفصول</button><button type="button" role="tab" aria-selected={view==="manage"} className={view==="manage"?"active":""} onClick={()=>setView("manage")}>إدارة الموجود</button></div>
    {view==="create"?<section className="structure-builder" aria-label="معالج إنشاء الصفوف والفصول">
      <div className="builder-step"><span>١</span><div><h3>حدد عدد الشعب لكل صف</h3><p>ضع صفرًا للصف الذي لا تريد إنشاءه.</p></div></div>
      <div className="builder-grade-grid">{grades.map((grade,index)=><label key={grade}><span><strong>{grade}</strong><small>مثال: {exampleName(index)}</small></span><ArabicNumberInput aria-label={`عدد فصول ${grade}`} min="0" max="30" value={counts[grade]??0} onChange={event=>setCounts({...counts,[grade]:Number(event.target.value)})}/></label>)}</div>
      <div className="builder-step"><span>٢</span><div><h3>اختر طريقة تسمية الفصول</h3><p>يمكن تعديل أي اسم لاحقًا من تبويب «إدارة الموجود».</p></div></div>
      <div className="naming-options">{[["grade_letter","الأول أ"],["number_slash_number","1 / 1"],["number_dash_number","1 ـ 1"],["number_slash_letter","1 / أ"]].map(([key,label])=><label key={key} className={namingPattern===key?"selected":""}><input type="radio" name="section_naming" checked={namingPattern===key} onChange={()=>setNamingPattern(key as typeof namingPattern)}/><span>{label}</span></label>)}</div>
      <div className="builder-submit"><div><strong>{Object.values(counts).reduce((sum,count)=>sum+count,0)} فصلًا</strong><span>سيتم إنشاؤها أو تحديثها مباشرة</span></div><button className="primary" disabled={busy} onClick={()=>{onSave({stage,naming_pattern:namingPattern,reset_names:true,grades:grades.map(grade=>({grade_name:grade,section_count:counts[grade]??0}))});setView("manage")}}>{busy?"جارٍ الإنشاء…":"إنشاء الصفوف والفصول"}</button></div>
    </section>:<div className="structure-editor-layout">
      <section className="structure-directory" aria-label="قائمة الفصول">
        <header><span>الصف</span><strong>الفصل / الشعبة</strong></header>
        <div className="structure-list">{visibleSections.map(({section,grade})=><button type="button" key={section.id} className={section.id===activeSectionId?"selected":""} onClick={()=>selectSection(section.id,section.name_ar)}><span>{grade.name_ar}</span><strong>{section.name_ar}</strong></button>)}{!visibleSections.length&&<p className="structure-empty">لا توجد فصول في هذه المرحلة. انتقل إلى تبويب الإنشاء.</p>}</div>
        <footer><button type="button" aria-label="رفع الفصل المحدد" title="رفع" disabled={busy||!selectedItem||data.sections.filter(section=>section.grade_id===selectedItem.grade.id)[0]?.id===activeSectionId} onClick={()=>moveSelected(-1)}>↑</button><button type="button" aria-label="خفض الفصل المحدد" title="خفض" disabled={busy||!selectedItem||data.sections.filter(section=>section.grade_id===selectedItem.grade.id).at(-1)?.id===activeSectionId} onClick={()=>moveSelected(1)}>↓</button><span>حدّد فصلًا ثم استخدم السهمين لترتيبه</span></footer>
      </section>
      <section className="structure-detail" aria-label="بيانات الفصل المحدد">{selectedItem?<><div><span>الفصل المحدد</span><h3>{selectedItem.section.name_ar}</h3><p>{selectedItem.grade.name_ar}</p></div><form onSubmit={event=>{event.preventDefault();const name=sectionName.trim();if(name.length>=1)onUpdate(selectedItem.section.id,name)}}><label>اسم الفصل أو الشعبة<input aria-label="اسم الفصل أو الشعبة" minLength={1} maxLength={100} value={sectionName} onChange={event=>setSectionName(event.target.value)} placeholder="مثال: ١/أ أو الموهوبون" required/></label><small>اكتب الاسم المستخدم في مدرستك دون نمط مفروض.</small><button className="primary" disabled={busy||sectionName.trim().length<1||sectionName.trim()===selectedItem.section.name_ar}>حفظ الاسم</button></form><button type="button" className="danger-action structure-delete" onClick={()=>setDeletingSectionId(selectedItem.section.id)}>حذف الفصل المحدد</button></>:<div className="soft-empty">اختر فصلًا من القائمة لعرض بياناته.</div>}</section>
    </div>}
    {deletingSection&&<div className="dialog-backdrop"><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-section-title"><h2 id="delete-section-title">حذف «{deletingSection.name_ar}» وإسناداته؟</h2><p>سيُزال الفصل من المدرسة وتُحذف إسناداته الحالية. سيبقى المعلمون والمواد موجودين ويمكنك إنشاء فصل جديد وإسنادهم إليه.</p><div className="dialog-actions"><button type="button" className="secondary" onClick={()=>setDeletingSectionId("")}>إلغاء</button><button type="button" className="danger-button" disabled={busy} onClick={()=>{onDelete(deletingSection.id);setDeletingSectionId("")}}>حذف الفصل وإسناداته</button></div></section></div>}
  </div>;
}

function ManagedTeachersStep({ data, busy, onCreate, onUpdate, onDelete, onMerge, onOrder, onAvailability, onCopy }: { data: CoreSnapshot; busy: boolean; onCreate:(payload:object)=>void; onUpdate:(id:string,payload:object)=>void; onDelete:(id:string,cascade:boolean)=>void; onMerge:(source:string,target:string)=>void; onOrder:(ids:string[])=>void; onAvailability:(id:string,cells:AvailabilityCell[])=>void; onCopy:(source:string,targets:string[])=>void }) {
  const [selected,setSelected]=useState(()=>{const saved=window.localStorage.getItem("pm-selected-teacher");return data.teachers.some(item=>item.id===saved)?saved??"":data.teachers[0]?.id??""});
  const [tab,setTab]=useState<"assignments"|"availability"|"constraints">("assignments");
  const [editing,setEditing]=useState(false);
  const [ignoredPairs,setIgnoredPairs]=useState<string[]>([]);
  const [cells,setCells]=useState<AvailabilityCell[]>(()=>data.teachers.find(item=>item.id===selected)?.availability??[]);
  const [copyTargets,setCopyTargets]=useState<string[]>([]);
  const [confirmation,setConfirmation]=useState<Confirmation|null>(null);
  const teacher=data.teachers.find(item=>item.id===selected);
  const periods=Math.max(1,...data.blocks.filter(item=>item.period_number).map(item=>item.period_number??0));
  const teacherAssignments=data.assignments.filter(item=>item.teacher_ids.includes(selected));
  const duplicatePairs=data.teachers.flatMap((item,index)=>data.teachers.slice(index+1).filter(other=>similarNames(item.name_ar,[other.name_ar]).length).map(other=>({first:item,second:other,key:`${item.id}:${other.id}`}))).filter(pair=>!ignoredPairs.includes(pair.key));
  function currentState(day:number,period:number){return cells.find(item=>item.weekday_index===day&&item.period_number===period)?.state??"available";}
  function cycle(day:number,period:number){const current=currentState(day,period);const state=current==="available"?"unavailable":current==="unavailable"?"avoid":"available";setCells([...cells.filter(item=>item.weekday_index!==day||item.period_number!==period),{weekday_index:day,period_number:period,state}]);}
  function reviewName(name:string,exclude:string|undefined,action:(allowSimilar:boolean)=>void){const matches=similarNames(name,data.teachers.filter(item=>item.id!==exclude).map(item=>item.name_ar));if(!matches.length){action(false);return}setConfirmation({title:"راجع اسم المعلم",message:`الاسم قريب من: ${matches.join("، ")}. هل هما شخصان مختلفان؟`,confirmLabel:"نعم، حفظ كمعلم مستقل",action:()=>action(true)});}
  return <div className="core-grid teacher-layout">
    <article className="core-card teacher-directory">
      <div className="card-title"><div><h2>المعلمون</h2><p>{data.teachers.length} معلمًا، ويمكن الإضافة والتعديل والحذف من هنا.</p></div></div>
      {duplicatePairs.length>0&&<details className="duplicate-review" open><summary>تنبيه: {duplicatePairs.length} أسماء متشابهة تحتاج مراجعتك</summary>{duplicatePairs.map(pair=><div key={pair.key}><p><strong>{pair.first.name_ar}</strong><span>يشبه</span><strong>{pair.second.name_ar}</strong></p><div><button type="button" onClick={()=>{setSelected(pair.second.id);setEditing(true)}}>تعديل الثاني</button><button type="button" className="danger-action" onClick={()=>setConfirmation({title:"دمج الاسمين؟",message:`ستُنقل كل إسنادات ${pair.second.name_ar} إلى ${pair.first.name_ar} ثم يُحذف الاسم الثاني.`,confirmLabel:"دمج وحذف الثاني",danger:true,action:()=>onMerge(pair.second.id,pair.first.id)})}>دمج وحذف الثاني</button><button type="button" onClick={()=>setIgnoredPairs([...ignoredPairs,pair.key])}>الاحتفاظ بهما</button></div></div>)}</details>}
      <form className="quick-add" onSubmit={event=>{event.preventDefault();const element=event.currentTarget;const form=new FormData(element);const name=value(form,"name");reviewName(name,undefined,allowSimilar=>{onCreate({name_ar:name,workload_limit:Number(value(form,"limit")),allow_similar:allowSimilar});element.reset()})}}>
        <input name="name" placeholder="اسم المعلم" required/><ArabicNumberInput aria-label="النصاب" name="limit" defaultValue="24" min="1"/><button disabled={busy}>إضافة</button>
      </form>
      <div className="teacher-list"><div className="list-head"><span>الاسم</span><span>النصاب</span><span>المسند</span><span>المتبقي</span></div>{data.teachers.map(item=><button type="button" className={`teacher-select ${item.id===selected?"selected":""}`} key={item.id} onClick={()=>{setSelected(item.id);window.localStorage.setItem("pm-selected-teacher",item.id);setCells(item.availability);setEditing(false)}}><strong>{item.name_ar}{item.shared&&<small>مشترك</small>}</strong><span>{item.workload_limit}</span><span>{item.assigned}</span><span className={item.remaining<0?"negative":""}>{item.remaining}</span></button>)}<div className="teacher-list-order"><button type="button" aria-label="رفع المعلم المحدد" title="رفع المعلم المحدد" disabled={busy||!teacher||data.teachers[0]?.id===selected} onClick={()=>onOrder(moved(data.teachers.map(item=>item.id),selected,-1))}>↑</button><button type="button" aria-label="خفض المعلم المحدد" title="خفض المعلم المحدد" disabled={busy||!teacher||data.teachers.at(-1)?.id===selected} onClick={()=>onOrder(moved(data.teachers.map(item=>item.id),selected,1))}>↓</button><span>حدّد معلمًا ثم استخدم السهمين لتحريكه</span></div></div>
    </article>
    <article className="core-card teacher-profile">
      {!teacher?<div className="soft-empty">أضف معلمًا لعرض ملفه.</div>:<>
        <header className="teacher-profile-head"><div><span>ملف المعلم</span><h2>{teacher.name_ar}</h2><p>{teacher.assigned} حصة مسندة من نصاب {teacher.workload_limit}، والمتبقي {teacher.remaining}.</p></div><div><button type="button" onClick={()=>setEditing(!editing)}>تعديل</button><button type="button" className="danger-action" disabled={busy} onClick={()=>setConfirmation({title:`حذف ${teacher.name_ar}؟`,message:`سيُحذف المعلم و${teacher.assigned} حصة مسندة له. ستبقى المواد والفصول، وتصبح حصصها شاغرة لإسنادها من جديد.`,confirmLabel:"حذف المعلم وإسناداته",danger:true,action:()=>onDelete(teacher.id,true)})}>حذف المعلم</button></div></header>
        {editing&&<form className="teacher-edit" onSubmit={event=>{event.preventDefault();const form=new FormData(event.currentTarget);const name=value(form,"edit_name");reviewName(name,teacher.id,allowSimilar=>{onUpdate(teacher.id,{name_ar:name,workload_limit:Number(value(form,"edit_limit")),allow_similar:allowSimilar});setEditing(false)})}}><label>اسم المعلم<input name="edit_name" defaultValue={teacher.name_ar} required/></label><label>نصاب الحصص<ArabicNumberInput name="edit_limit" min="1" max="60" defaultValue={teacher.workload_limit}/></label><button disabled={busy}>حفظ التعديل</button></form>}
        <div className="teacher-tabs" role="tablist"><button className={tab==="assignments"?"active":""} onClick={()=>setTab("assignments")}>المواد والفصول</button><button className={tab==="availability"?"active":""} onClick={()=>setTab("availability")}>التوفر</button><button className={tab==="constraints"?"active":""} onClick={()=>setTab("constraints")}>القيود</button></div>
        {tab==="assignments"&&<div className="teacher-detail-list">{teacherAssignments.map(item=><div key={item.id}><strong>{item.subject_name}</strong><span>{item.section_names.join("، ")} · {item.weekly_occurrences} حصص أسبوعيًا</span></div>)}{!teacherAssignments.length&&<div className="soft-empty">لم تُسند مواد لهذا المعلم بعد.</div>}<Link className="profile-link" href="/assignments" onClick={()=>window.localStorage.setItem("pm-selected-teacher",teacher.id)}>فتح شاشة الإسناد لهذا المعلم</Link></div>}
        {tab==="constraints"&&<div className="teacher-constraints"><p>أيام العمل، عدم أخذ الأولى، أول أربع حصص والحدود اليومية.</p><Link href="/constraints">فتح قواعد {teacher.name_ar}</Link></div>}
        {tab==="availability"&&<><div className="availability-legend"><span className="available">متاح</span><span className="unavailable">غير متاح</span><span className="avoid">يفضل تجنبه</span></div><div className="availability-grid" style={{gridTemplateColumns:`110px repeat(${periods},1fr)`}}><b>اليوم</b>{Array.from({length:periods},(_,index)=><b key={index}>{index+1}</b>)}{weekdays.map((day,dayIndex)=><div style={{display:"contents"}} key={day}><strong>{day}</strong>{Array.from({length:periods},(_,index)=>{const state=currentState(dayIndex,index+1);return <button aria-label={`${day} الحصة ${index+1} ${state}`} type="button" className={state} key={index} onClick={()=>cycle(dayIndex,index+1)}>{state==="available"?"✓":state==="unavailable"?"×":"~"}</button>})}</div>)}</div><button className="primary core-primary" disabled={busy} onClick={()=>onAvailability(teacher.id,cells)}>حفظ التوفر</button><details className="copy-panel"><summary>نسخ التوفر لمعلم أو مجموعة</summary><div>{data.teachers.filter(item=>item.id!==teacher.id).map(item=><label key={item.id}><input type="checkbox" checked={copyTargets.includes(item.id)} onChange={event=>setCopyTargets(event.target.checked?[...copyTargets,item.id]:copyTargets.filter(id=>id!==item.id))}/>{item.name_ar}</label>)}</div><button disabled={!copyTargets.length||busy} onClick={()=>onCopy(teacher.id,copyTargets)}>نسخ للمحددين</button></details></>}
      </>}
      {confirmation&&<ConfirmDialog title={confirmation.title} message={confirmation.message} confirmLabel={confirmation.confirmLabel} danger={confirmation.danger} onCancel={()=>setConfirmation(null)} onConfirm={()=>{confirmation.action();setConfirmation(null)}}/>}
    </article>
  </div>;
}

// Retained temporarily for compatibility with older snapshots during the workflow migration.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function TeachersStep({ data, busy, onCreate, onAvailability, onCopy }: { data: CoreSnapshot; busy: boolean; onCreate:(payload:object)=>void; onAvailability:(id:string,cells:AvailabilityCell[])=>void; onCopy:(source:string,targets:string[])=>void }) {
  const [selected, setSelected] = useState(data.teachers[0]?.id ?? ""); const teacher = data.teachers.find(item=>item.id===selected); const [cells,setCells]=useState<AvailabilityCell[]>(teacher?.availability??[]); const [copyTargets,setCopyTargets]=useState<string[]>([]); const [teacherTab,setTeacherTab]=useState<"assignments"|"availability"|"constraints">("availability");
  function cellState(day:number,period:number){return cells.find(item=>item.weekday_index===day&&item.period_number===period)?.state??"available";}
  function cycle(day:number,period:number){const current=cellState(day,period);const next=current==="available"?"unavailable":current==="unavailable"?"avoid":"available";setCells([...cells.filter(item=>item.weekday_index!==day||item.period_number!==period),{weekday_index:day,period_number:period,state:next}]);}
  const periods = Math.max(1,...data.blocks.filter(item=>item.period_number).map(item=>item.period_number??0));
  return <div className="core-grid teacher-layout"><article className="core-card"><div className="card-title"><div><h2>قائمة المعلمين</h2><p>النصاب والمسند والمتبقي في نظرة واحدة.</p></div></div><form className="quick-add" onSubmit={event=>{event.preventDefault();const form=new FormData(event.currentTarget);onCreate({name_ar:value(form,"name"),workload_limit:Number(value(form,"limit"))});event.currentTarget.reset();}}><input name="name" placeholder="اسم المعلم" required/><input aria-label="النصاب" name="limit" type="number" defaultValue="24" min="1"/><button disabled={busy}>إضافة</button></form><div className="teacher-list"><div className="list-head"><span>الاسم</span><span>النصاب</span><span>المسند</span><span>المتبقي</span></div>{data.teachers.map(item=><button type="button" className={item.id===selected?"selected":""} key={item.id} onClick={()=>{setSelected(item.id);setCells(item.availability);}}><strong>{item.name_ar}{item.shared&&<small>مشترك</small>}</strong><span>{item.workload_limit}</span><span>{item.assigned}</span><span className={item.remaining<0?"negative":""}>{item.remaining}</span></button>)}</div></article><article className="core-card availability-card"><div className="card-title"><div><h2>{teacher?.name_ar??"اختر معلمًا"}</h2><p>الإسنادات والتوفر والقيود الخاصة بالمعلم في مكان واحد.</p></div></div>{teacher&&<><div className="teacher-tabs" role="tablist"><button className={teacherTab==="assignments"?"active":""} onClick={()=>setTeacherTab("assignments")}>الإسنادات</button><button className={teacherTab==="availability"?"active":""} onClick={()=>setTeacherTab("availability")}>التوفر/التفريغ</button><button className={teacherTab==="constraints"?"active":""} onClick={()=>setTeacherTab("constraints")}>القيود</button></div>{teacherTab==="assignments"&&<div className="teacher-detail-list">{data.assignments.filter(item=>item.teacher_names.includes(teacher.name_ar)).map(item=><div key={item.id}><strong>{item.subject_name}</strong><span>{item.section_names.join("، ")} · {item.weekly_occurrences} حصص</span></div>)}{!data.assignments.some(item=>item.teacher_names.includes(teacher.name_ar))&&<div className="soft-empty">لا توجد إسنادات لهذا المعلم.</div>}</div>}{teacherTab==="constraints"&&<div className="teacher-constraints"><p>أنماط الواقع المدرسي جاهزة: أيام محددة، بدون الأولى، أول أربع حصص، وحدود يومية ومتتالية.</p><Link href="/constraints">فتح قواعد {teacher.name_ar}</Link></div>}{teacherTab==="availability"&&<><div className="availability-legend"><span className="available">متاح</span><span className="unavailable">غير متاح</span><span className="avoid">يفضل تجنبه</span></div><div className="availability-grid" style={{gridTemplateColumns:`110px repeat(${periods},1fr)`}}><b>اليوم</b>{Array.from({length:periods},(_,index)=><b key={index}>{index+1}</b>)}{weekdays.map((day,dayIndex)=><div className="availability-row" style={{display:"contents"}} key={day}><strong>{day}</strong>{Array.from({length:periods},(_,index)=>{const state=cellState(dayIndex,index+1);return <button aria-label={`${day} الحصة ${index+1} ${state}`} type="button" className={state} key={index} onClick={()=>cycle(dayIndex,index+1)}>{state==="available"?"✓":state==="unavailable"?"×":"~"}</button>})}</div>)}</div><button className="primary core-primary" disabled={busy} onClick={()=>onAvailability(teacher.id,cells)}>حفظ التوفر</button><details className="copy-panel"><summary>نسخ التوفر والقيود لمعلم أو مجموعة</summary><div>{data.teachers.filter(item=>item.id!==teacher.id).map(item=><label key={item.id}><input type="checkbox" checked={copyTargets.includes(item.id)} onChange={event=>setCopyTargets(event.target.checked?[...copyTargets,item.id]:copyTargets.filter(id=>id!==item.id))}/>{item.name_ar}</label>)}</div><button disabled={!copyTargets.length||busy} onClick={()=>onCopy(teacher.id,copyTargets)}>نسخ للمحددين</button></details></>}</>}</article></div>;
}

function MaterialsAndAssignmentsTabs({plan,assignments}:{plan:ReactNode;assignments:ReactNode}){
  const [tab,setTab]=useState<"plan"|"assignments">("assignments");
  return <div className="materials-workspace"><div className="materials-tabs" role="tablist" aria-label="المواد والإسناد"><button type="button" role="tab" aria-selected={tab==="assignments"} className={tab==="assignments"?"active":""} onClick={()=>setTab("assignments")}>إسناد المعلمين</button><button type="button" role="tab" aria-selected={tab==="plan"} className={tab==="plan"?"active":""} onClick={()=>setTab("plan")}>الخطة الدراسية والاحتياج</button></div>{tab==="plan"?plan:assignments}</div>;
}

function CurriculumPlan({data,busy,onSubject,onSubjectUpdate,onSubjectDelete,onSubjectOrder,onSave}:{data:CoreSnapshot;busy:boolean;onSubject:(name:string)=>void;onSubjectUpdate:(id:string,name:string)=>void;onSubjectDelete:(id:string)=>void;onSubjectOrder:(ids:string[])=>void;onSave:(cells:Array<{grade_id:string;subject_id:string;weekly_occurrences:number}>)=>void}){
  const [planningLoad,setPlanningLoad]=useState(24);
  const [cells,setCells]=useState<Record<string,number>>(()=>initialCurriculum(data));
  const [editingSubject,setEditingSubject]=useState<{id:string;name:string}|null>(null);
  const [deletingSubject,setDeletingSubject]=useState<{id:string;name:string}|null>(null);
  const sectionCount=(gradeId:string)=>data.sections.filter(section=>section.grade_id===gradeId).length;
  const valueFor=(gradeId:string,subjectId:string)=>cells[`${gradeId}:${subjectId}`]??0;
  const subjectTotal=(subjectId:string)=>data.grades.reduce((total,grade)=>total+valueFor(grade.id,subjectId)*sectionCount(grade.id),0);
  const assignedTotal=(subjectId:string)=>data.assignments.filter(item=>item.subject_id===subjectId).reduce((total,item)=>total+item.weekly_occurrences,0);
  const schoolCapacity=data.weekdays.length*Math.max(0,...data.blocks.map(item=>item.period_number??0))*data.sections.length;
  const requiredTotal=data.subjects.reduce((sum,subject)=>sum+subjectTotal(subject.id),0);
  const assignedPlanTotal=data.subjects.reduce((sum,subject)=>sum+Math.min(subjectTotal(subject.id),assignedTotal(subject.id)),0);
  const unassignedTotal=Math.max(0,requiredTotal-assignedPlanTotal);
  return <article className="core-card curriculum-plan">
    <div className="card-title"><div><span className="eyebrow">قبل الإسناد</span><h2>الخطة الدراسية واحتياج المدرسة</h2><p>أدخل حصص المادة لكل صف مرة واحدة؛ يحسب النظام إجمالي الحصص وعدد المعلمين المطلوب تلقائيًا.</p></div><label className="planning-load">نصاب التخطيط<select value={planningLoad} onChange={event=>setPlanningLoad(Number(event.target.value))}><option value="24">24 حصة</option><option value="22">22 حصة</option><option value="18">18 حصة</option></select></label></div>
    <div className="curriculum-capacity"><div><span>الفصول والشُعب</span><strong>{data.sections.length}</strong></div><div><span>الحصص المتاحة أسبوعيًا</span><strong>{schoolCapacity}</strong></div><div><span>الخطة المطلوبة</span><strong>{requiredTotal}</strong></div><div className={unassignedTotal?"needs-assignment":""}><span>حصص غير مسندة</span><strong>{unassignedTotal}</strong></div></div>
    {unassignedTotal>0&&<div className="assignment-gap" role="status">تنبيه: توجد {unassignedTotal} حصة في الخطة بلا معلم، ويمكن إسنادها من تبويب «إسناد المعلمين».</div>}
    {!data.subjects.length?<div className="soft-empty">أضف المواد أولًا لبدء الخطة الدراسية.</div>:<div className="curriculum-wrap"><table><thead><tr><th>المادة</th>{data.grades.map(grade=><th key={grade.id}>{grade.name_ar}<small>{sectionCount(grade.id)} فصول</small></th>)}<th>إجمالي المدرسة</th><th>المسند</th><th>الاحتياج</th><th>الإجراءات</th></tr></thead><tbody>{data.subjects.map(subject=>{const total=subjectTotal(subject.id),assigned=assignedTotal(subject.id);return <tr key={subject.id}><th><strong>{subject.name_ar}</strong></th>{data.grades.map(grade=><td key={grade.id}><ArabicNumberInput aria-label={`${subject.name_ar} ${grade.name_ar}`} min="0" max="60" value={valueFor(grade.id,subject.id)} onChange={event=>setCells({...cells,[`${grade.id}:${subject.id}`]:Number(event.target.value)})}/></td>)}<td><strong>{total}</strong> حصة</td><td className={assigned<total?"plan-warning":"plan-complete"}>{assigned}</td><td><strong>{total?Math.ceil(total/planningLoad):0}</strong> معلم</td><td className="subject-actions"><button type="button" aria-label={`رفع ${subject.name_ar}`} title="رفع" onClick={()=>onSubjectOrder(moved(data.subjects.map(item=>item.id),subject.id,-1))}>↑</button><button type="button" aria-label={`خفض ${subject.name_ar}`} title="خفض" onClick={()=>onSubjectOrder(moved(data.subjects.map(item=>item.id),subject.id,1))}>↓</button><button type="button" onClick={()=>setEditingSubject({id:subject.id,name:subject.name_ar})}>تعديل</button><button type="button" className="danger-action" onClick={()=>setDeletingSubject({id:subject.id,name:subject.name_ar})}>حذف</button></td></tr>})}</tbody></table></div>}
    <div className="curriculum-actions"><form onSubmit={event=>{event.preventDefault();const form=new FormData(event.currentTarget);onSubject(value(form,"plan_subject"));event.currentTarget.reset()}}><input name="plan_subject" placeholder="اسم مادة جديدة" required/><button type="submit" aria-label="إضافة مادة" title="إضافة مادة" disabled={busy}>+</button></form><button className="primary" disabled={busy||!data.subjects.length} onClick={()=>onSave(data.subjects.flatMap(subject=>data.grades.map(grade=>({grade_id:grade.id,subject_id:subject.id,weekly_occurrences:valueFor(grade.id,subject.id)}))))}>حفظ الخطة الدراسية</button></div>
    {editingSubject&&<div className="dialog-backdrop"><form className="confirm-dialog" role="dialog" aria-modal="true" onSubmit={event=>{event.preventDefault();if(editingSubject.name.trim())onSubjectUpdate(editingSubject.id,editingSubject.name.trim());setEditingSubject(null)}}><h2>تعديل اسم المادة</h2><label>اسم المادة<input aria-label="اسم المادة" autoFocus value={editingSubject.name} onChange={event=>setEditingSubject({...editingSubject,name:event.target.value})}/></label><div className="dialog-actions"><button type="button" onClick={()=>setEditingSubject(null)}>إلغاء</button><button className="primary" disabled={!editingSubject.name.trim()}>حفظ التعديل</button></div></form></div>}
    {deletingSubject&&<ConfirmDialog title={`حذف ${deletingSubject.name}؟`} message="لن تُحذف المادة إذا كانت مرتبطة بإسناد؛ انقل الإسناد أو احذفه أولًا." confirmLabel="حذف المادة" danger onCancel={()=>setDeletingSubject(null)} onConfirm={()=>{onSubjectDelete(deletingSubject.id);setDeletingSubject(null)}}/>}
  </article>;
}

function AssignmentsStep({ data, busy, onSubject, onAssign, onUpdate, onDelete, onDeduplicate, onTransfer }: {
  data: CoreSnapshot;
  busy: boolean;
  onSubject: (name: string) => void;
  onAssign: (payload: object) => void;
  onUpdate: (id: string, payload: object) => void;
  onDelete: (id: string) => void;
  onDeduplicate: (teacherId: string) => void;
  onTransfer: (payload: { source_teacher_id: string; target_teacher_id: string; assignment_ids: string[]; mode: "move"; allow_overload: boolean }) => void;
}) {
  const [teacherId, setTeacherId] = useState(()=>{const saved=window.localStorage.getItem("pm-selected-teacher");return data.teachers.some(item=>item.id===saved)?saved??"":data.teachers[0]?.id??""});
  const [search, setSearch] = useState("");
  const [editor, setEditor] = useState<CoreAssignment | "new" | null>(null);
  const [subjectId, setSubjectId] = useState(data.subjects[0]?.id ?? "");
  const [sectionIds, setSectionIds] = useState<string[]>([]);
  const [weekly, setWeekly] = useState(5);
  const [selectedAssignments, setSelectedAssignments] = useState<string[]>([]);
  const [transferOpen, setTransferOpen] = useState(false);
  const [targetTeacherId, setTargetTeacherId] = useState("");
  const [confirmation,setConfirmation]=useState<Confirmation|null>(null);
  const teacher = data.teachers.find((item) => item.id === teacherId) ?? data.teachers[0];
  const teacherAssignments = data.assignments.filter((item) => item.teacher_ids.includes(teacher?.id ?? ""));
  const assignmentKeys=teacherAssignments.map(item=>`${item.subject_id}:${[...item.section_ids].sort().join(",")}`);
  const duplicateAssignmentCount=assignmentKeys.length-new Set(assignmentKeys).size;
  const visibleTeachers = data.teachers.filter((item) => item.name_ar.includes(search.trim()));
  const gradesById = new Map(data.grades.map((item) => [item.id, item]));
  const sectionLabel = (sectionId: string, savedName?: string) => {
    const section = data.sections.find((item) => item.id === sectionId);
    const grade = section ? gradesById.get(section.grade_id) : undefined;
    if (!section) return savedName || "فصل محفوظ غير نشط";
    return grade && !section.name_ar.includes(grade.name_ar)
      ? `${grade.name_ar} ${section.name_ar}`
      : section.name_ar;
  };
  const gradeGroups = data.grades.map((grade) => ({
    grade,
    sections: data.sections.filter((section) => section.grade_id === grade.id),
  })).filter((group) => group.sections.length);
  const progress = teacher ? Math.min(100, Math.round((teacher.assigned / Math.max(1, teacher.workload_limit)) * 100)) : 0;

  function openNew() {
    setEditor("new");
    setSubjectId(data.subjects[0]?.id ?? "");
    setSectionIds([]);
    setWeekly(5);
  }
  function openEdit(assignment: CoreAssignment) {
    setEditor(assignment);
    setSubjectId(assignment.subject_id);
    setSectionIds(assignment.section_ids.slice(0, 1));
    setWeekly(assignment.weekly_occurrences);
  }
  function toggleSection(id: string) {
    if (editor !== "new") {
      setSectionIds([id]);
      return;
    }
    setSectionIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }
  function submitAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!teacher || !subjectId || !sectionIds.length) return;
    const projected = teacher.assigned + (
      editor === "new" ? sectionIds.length * weekly : weekly - (editor?.weekly_occurrences ?? 0)
    );
    const allowOverload = projected > teacher.workload_limit;
    const payload = { term_id: data.term_id, section_ids: sectionIds, subject_id: subjectId, teacher_id: teacher.id, weekly_occurrences: weekly, allow_overload: allowOverload };
    const save=()=>{if(editor === "new") onAssign(payload);else if(editor) onUpdate(editor.id,payload);setEditor(null)};
    if(allowOverload){setConfirmation({title:"تجاوز النصاب المحدد",message:`سيصبح نصاب ${teacher.name_ar} ${projected} حصة بدلًا من ${teacher.workload_limit}. اعتمد الزيادة فقط إذا كانت مقصودة.`,confirmLabel:"اعتماد الزيادة وحفظ الإسناد",action:save});return}
    save();
  }

  return <div className="assignment-workbench">
    <aside className="core-card assignment-teachers">
      <div className="assignment-side-heading"><div><span>فريق المدرسة</span><h2>المعلمون</h2></div><b>{data.teachers.length}</b></div>
      <label className="teacher-search"><span>بحث</span><input value={search} onChange={(event)=>setSearch(event.target.value)} placeholder="اكتب اسم المعلم" /></label>
      <div className="assignment-teacher-list">{visibleTeachers.map((item)=>{
        const percent=Math.min(100,Math.round((item.assigned/Math.max(1,item.workload_limit))*100));
        return <button type="button" className={item.id===teacher?.id?"active":""} key={item.id} onClick={()=>{setTeacherId(item.id);window.localStorage.setItem("pm-selected-teacher",item.id);setEditor(null);setSelectedAssignments([]);setTransferOpen(false)}}>
          <span className="teacher-avatar">{item.name_ar.trim().charAt(0)}</span><span className="teacher-row-main"><strong>{item.name_ar}</strong><i><u style={{width:`${percent}%`}} /></i></span><span className="teacher-load"><b>{item.assigned}</b><small>من {item.workload_limit}</small></span>
        </button>})}{!visibleTeachers.length&&<div className="soft-empty">لا يوجد معلم بهذا الاسم.</div>}</div>
    </aside>

    <main className="core-card assignment-detail">
      {!teacher?<div className="soft-empty">أضف المعلمين أولًا لبدء الإسناد.</div>:<>
        <header className="teacher-assignment-header">
          <div className="selected-teacher"><span className="teacher-avatar large">{teacher.name_ar.trim().charAt(0)}</span><div><span>إسنادات المعلم</span><h2>{teacher.name_ar}</h2></div></div>
          <div className={`workload-meter ${teacher.remaining<0?"over":""}`}><div><span>النصاب الحالي</span><strong>{teacher.assigned} <small>من {teacher.workload_limit} حصة</small></strong></div><div className="meter-track"><i style={{width:`${progress}%`}} /></div><b>{teacher.remaining>=0?`${teacher.remaining} متبقية`:`تجاوز ${Math.abs(teacher.remaining)}`}</b></div>
        </header>
        {duplicateAssignmentCount>0&&<div className="assignment-duplicate-warning" role="alert"><div><strong>وجدنا {duplicateAssignmentCount} إسنادًا مكررًا لهذا المعلم</strong><span>سيُحتفظ بنسخة واحدة لكل مادة وفصل، ويُصحح النصاب تلقائيًا.</span></div><button type="button" disabled={busy} onClick={()=>onDeduplicate(teacher.id)}>إصلاح التكرار</button></div>}
        <div className="assignment-toolbar"><button type="button" className="primary add-assignment" disabled={busy||!data.subjects.length||!data.sections.length} onClick={openNew}>+ إضافة إسناد</button><button type="button" disabled={!selectedAssignments.length} onClick={()=>setTransferOpen(!transferOpen)}>نقل المحدد <b>{selectedAssignments.length||""}</b></button><form className="inline-subject" onSubmit={event=>{event.preventDefault();const form=new FormData(event.currentTarget);onSubject(value(form,"subject_name"));event.currentTarget.reset()}}><input name="subject_name" placeholder="إضافة مادة غير موجودة" required/><button disabled={busy}>إضافة المادة</button></form></div>

        {transferOpen&&<section className="transfer-panel"><div><strong>نقل الإسنادات</strong><span>{selectedAssignments.length} إسناد محدد من {teacher.name_ar}</span></div><label>إلى المعلم<select value={targetTeacherId} onChange={(event)=>setTargetTeacherId(event.target.value)}><option value="">اختر المعلم</option>{data.teachers.filter((item)=>item.id!==teacher.id).map((item)=><option value={item.id} key={item.id}>{item.name_ar} · {item.assigned} من {item.workload_limit}</option>)}</select></label><button type="button" className="primary" disabled={busy||!targetTeacherId} onClick={()=>{const target=data.teachers.find(item=>item.id===targetTeacherId);const added=teacherAssignments.filter(item=>selectedAssignments.includes(item.id)&&!item.teacher_ids.includes(targetTeacherId)).reduce((sum,item)=>sum+item.weekly_occurrences,0);const projected=(target?.assigned??0)+added;const allowOverload=Boolean(target&&projected>target.workload_limit);const transfer=()=>{onTransfer({source_teacher_id:teacher.id,target_teacher_id:targetTeacherId,assignment_ids:selectedAssignments,mode:"move",allow_overload:allowOverload});setTransferOpen(false);setSelectedAssignments([])};if(allowOverload){setConfirmation({title:"تجاوز نصاب المعلم المنقول إليه",message:`سيصبح نصاب ${target?.name_ar} ${projected} حصة بدلًا من ${target?.workload_limit}.`,confirmLabel:"اعتماد الزيادة وتنفيذ النقل",action:transfer});return}transfer()}}>تنفيذ النقل</button></section>}

        {editor&&<form className="assignment-editor-simple" onSubmit={submitAssignment}>
          <div className="editor-heading"><div><span>{editor==="new"?"إسناد جديد":"تعديل الإسناد"}</span><h3>اختر المادة ثم الفصول</h3></div><button type="button" aria-label="إغلاق" onClick={()=>setEditor(null)}>×</button></div>
          <div className="assignment-editor-grid"><label>المادة<select value={subjectId} onChange={(event)=>setSubjectId(event.target.value)} required>{data.subjects.map((item)=><option value={item.id} key={item.id}>{item.name_ar}</option>)}</select></label><label>عدد الحصص الأسبوعية<ArabicNumberInput min="1" max="60" value={weekly} onChange={(event)=>setWeekly(Number(event.target.value))} required/></label></div>
          <fieldset><legend>الصفوف والفصول <small>{editor==="new"?"يمكن اختيار أكثر من فصل":"اختر فصلًا واحدًا عند التعديل"}</small></legend><div className="section-groups">{gradeGroups.map(({grade,sections})=>{const allSelected=sections.every((item)=>sectionIds.includes(item.id));return <section key={grade.id}><header><strong>{grade.name_ar}</strong>{editor==="new"&&<button type="button" onClick={()=>setSectionIds((current)=>allSelected?current.filter((id)=>!sections.some((item)=>item.id===id)):[...new Set([...current,...sections.map((item)=>item.id)])])}>{allSelected?"إلغاء الصف":"اختيار الصف كاملًا"}</button>}</header><div>{sections.map((section)=><label className={sectionIds.includes(section.id)?"selected":""} key={section.id}><input type={editor==="new"?"checkbox":"radio"} checked={sectionIds.includes(section.id)} onChange={()=>toggleSection(section.id)}/><span>{sectionLabel(section.id)}</span></label>)}</div></section>})}</div></fieldset>
          <div className="editor-footer"><span>سيصبح النصاب المتوقع <strong>{teacher.assigned+(editor==="new"?sectionIds.length*weekly:weekly-editor.weekly_occurrences)}</strong> من {teacher.workload_limit}</span><div><button type="button" onClick={()=>setEditor(null)}>إلغاء</button><button className="primary" disabled={busy||!sectionIds.length}>{editor==="new"?`حفظ ${sectionIds.length||""} إسناد`:"حفظ التعديل"}</button></div></div>
        </form>}

        <section className="teacher-assignment-list"><header><div><h3>المواد والفصول المسندة</h3><span>{teacherAssignments.length} إسناد · {teacher.assigned} حصة أسبوعية</span></div>{teacherAssignments.length>0&&<label><input type="checkbox" checked={selectedAssignments.length===teacherAssignments.length} onChange={(event)=>setSelectedAssignments(event.target.checked?teacherAssignments.map((item)=>item.id):[])} /> تحديد الكل</label>}</header>{teacherAssignments.length?teacherAssignments.map((item)=><article key={item.id}><label className="assignment-select"><input type="checkbox" checked={selectedAssignments.includes(item.id)} onChange={(event)=>setSelectedAssignments(event.target.checked?[...selectedAssignments,item.id]:selectedAssignments.filter((id)=>id!==item.id))}/></label><span className="subject-mark">{item.subject_name.trim().charAt(0)}</span><div className="assignment-name"><strong>{item.subject_name}</strong><span>{item.section_ids.map((id,index)=>sectionLabel(id,item.section_names[index])).join("، ")}</span></div><div className="assignment-hours"><b>{item.weekly_occurrences}</b><span>حصص</span></div><div className="assignment-actions"><button type="button" onClick={()=>openEdit(item)}>تعديل</button><button type="button" className="danger-link" onClick={()=>setConfirmation({title:"حذف الإسناد؟",message:`سيُحذف إسناد ${item.subject_name} من ${item.section_names.join("، ")} ويُحدّث نصاب المعلم مباشرة.`,confirmLabel:"حذف الإسناد",danger:true,action:()=>onDelete(item.id)})}>حذف</button></div></article>):<div className="assignment-empty"><span>+</span><h3>لا توجد إسنادات لهذا المعلم</h3><p>ابدأ باختيار المادة والفصول، وسيظهر النصاب هنا مباشرة.</p><button type="button" onClick={openNew}>إضافة أول إسناد</button></div>}</section>
        <details className="advanced-box"><summary>خيارات الإسناد المتقدمة</summary><p>التدريس المشترك، دمج الفصول، تقسيم المجموعات والموارد تبقى منفصلة عن العمل اليومي.</p><div><Link href="/advanced/assignments">فتح الإسناد المتقدم</Link><Link href="/imports">استيراد البيانات</Link></div></details>
      </>}
      {confirmation&&<ConfirmDialog title={confirmation.title} message={confirmation.message} confirmLabel={confirmation.confirmLabel} danger={confirmation.danger} onCancel={()=>setConfirmation(null)} onConfirm={()=>{confirmation.action();setConfirmation(null)}}/>}
    </main>
  </div>;
}

function ConstraintsStep({data,busy,onRule}:{data:CoreSnapshot;busy:boolean;onRule:(payload:object)=>void}){
  const [teacherId,setTeacherId]=useState(data.teachers[0]?.id??"");const [assignmentId,setAssignmentId]=useState(data.assignments[0]?.id??"");const [secondAssignmentId,setSecondAssignmentId]=useState(data.assignments[1]?.id??"");
  const presets=[
    ["no_first_period","لا تعطه الحصة الأولى","teacher"],["no_thursday","لا يعمل يوم الخميس","teacher"],["selected_days_only","يعمل الأحد والثلاثاء فقط","teacher"],["first_four_only","يعمل أول 4 حصص فقط","teacher"],["max_daily","لا يزيد عن 4 حصص يوميًا","teacher"],["max_consecutive","لا أكثر من 3 حصص متتالية","teacher"],["prefer_free_day","يفضل يوم الخميس فارغًا","teacher"],["spread_assignment","وزع المادة على 4 أيام","assignment"],["consecutive_assignment","اجعل حصتي العلوم متتاليتين","assignment"],["assignment_before","مادة قبل مادة","relation"],
  ] as const;
  return <div className="core-card"><div className="card-title"><div><h2>قواعد جاهزة بلغة المدرسة</h2><p>اختر المعلم أو الإسناد ثم طبّق القاعدة بضغطة واحدة.</p></div></div><div className="constraint-targets"><label>المعلم<select value={teacherId} onChange={event=>setTeacherId(event.target.value)}>{data.teachers.map(item=><option value={item.id} key={item.id}>{item.name_ar}</option>)}</select></label><label>المادة والفصل<select value={assignmentId} onChange={event=>setAssignmentId(event.target.value)}>{data.assignments.map(item=><option value={item.id} key={item.id}>{item.subject_name} · {item.section_names.join("، ")}</option>)}</select></label><label>المادة التالية في قاعدة «قبل»<select value={secondAssignmentId} onChange={event=>setSecondAssignmentId(event.target.value)}>{data.assignments.filter(item=>item.id!==assignmentId).map(item=><option value={item.id} key={item.id}>{item.subject_name} · {item.section_names.join("، ")}</option>)}</select></label></div><div className="preset-rules">{presets.map(([preset,label,target])=><button type="button" disabled={busy||(target==="teacher"?!teacherId:target==="relation"?!assignmentId||!secondAssignmentId:!assignmentId)} key={preset} onClick={()=>onRule({preset,teacher_id:target==="teacher"?teacherId:null,assignment_id:target!=="teacher"?assignmentId:null,second_assignment_id:target==="relation"?secondAssignmentId:null,weekdays:preset==="selected_days_only"?[0,2]:preset==="prefer_free_day"?[4]:[],value:preset==="max_daily"||preset==="spread_assignment"?4:preset==="max_consecutive"?3:preset==="consecutive_assignment"?2:null})}><span>+</span>{label}</button>)}</div><details className="advanced-box"><summary>خيارات متقدمة</summary><p>باني القواعد الكامل والعلاقات بين مادتين متاحان عند الحاجة، بأسماء واضحة دون إدخال معرفات.</p><Link href="/advanced/timetables">فتح باني القواعد المتقدم</Link></details></div>;
}

function GenerateStep({data,busy,runId,onGenerate}:{data:CoreSnapshot;busy:boolean;runId:string;onGenerate:(profile:string)=>void}){
  const [profile,setProfile]=useState("balanced");const checks=[["البيانات الأساسية",data.readiness.basic_data],["الإسنادات",data.readiness.assignments],["القيود",data.readiness.constraints],["الفحص المسبق",data.readiness.preflight]] as const;
  return <div className="generation-workspace"><div className="generate-layout"><article className="core-card readiness-card"><div className="card-title"><div><h2>جاهزية الجدول</h2><p>نعرض المطلوب بلغة واضحة قبل البدء.</p></div></div>{checks.map(([label,ready])=><div className={`readiness-row ${statusClass(ready)}`} key={label}><span>{ready?"✓":"!"}</span><strong>{label}</strong><b>{ready?"مكتملة":"تحتاج إكمال"}</b></div>)}</article><article className="core-card generate-card"><h2>اختر أسلوب التوزيع</h2><div className="profile-options">{[["balanced","متوازن","توزيع عملي بين احتياجات المدرسة"],["teacher_comfort","راحة المعلمين","تقليل الفجوات والتتابع المرهق"],["student_rhythm","أفضل للطلاب","إيقاع يومي وتوزيع مواد أفضل"],["custom","مخصص","استخدام تفضيلاتك المحفوظة"]].map(([key,label,description])=><label className={profile===key?"selected":""} key={key}><input type="radio" name="profile" value={key} checked={profile===key} onChange={()=>setProfile(key)}/><strong>{label}</strong><span>{description}</span></label>)}</div><button className="generate-button" disabled={busy} onClick={()=>onGenerate(profile)}>{busy?"جارٍ الفحص...":"إنشاء الجدول"}<small>سيتم إنشاء 3 بدائل للمقارنة</small></button><details className="advanced-box"><summary>الإدارة والنتائج المتقدمة</summary><div><Link href="/advanced/timetables">المشاريع والقواعد</Link><Link href="/substitutions">الغياب والبدلاء</Link><Link href="/reports">التقارير والطباعة</Link></div></details></article></div><CoreTimetableGrid data={data} runId={runId}/></div>;
}
