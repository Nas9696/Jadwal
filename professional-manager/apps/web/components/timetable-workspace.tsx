"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { setupApi, type School, type SetupSnapshot } from "@/lib/setup-api";
import {
  projectApi,
  type CandidateDetail,
  type Preflight,
  type Project,
  type ProjectSchool,
  type QualityReport,
  type PlacementExplanation,
  type Rule,
  type SolveRun,
} from "@/lib/project-api";
import { TimetableEditor } from "@/components/timetable-editor";
import { SchedulingAssistant } from "@/components/scheduling-assistant";

const weekdays = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
const softTypes = new Set(["teacher_preferred_time", "teacher_avoided_time", "assignment_preferred_time", "assignment_avoided_time", "subject_preferred_time", "subject_avoided_time", "assignment_avoid_same_day_repeat", "assignment_preferred_resource"]);
const ruleLabels: Record<string, string> = {
  teacher_unavailable: "المعلم غير متاح",
  section_unavailable: "الشعبة غير متاحة",
  resource_unavailable: "المورد غير متاح",
  assignment_forbidden_time: "وقت ممنوع للإسناد",
  assignment_required_time: "وقت مطلوب للإسناد",
  teacher_preferred_time: "وقت مفضل للمعلم",
  teacher_avoided_time: "وقت غير مفضل للمعلم",
  assignment_preferred_time: "وقت مفضل للإسناد",
  assignment_avoided_time: "وقت غير مفضل للإسناد",
  subject_preferred_time: "وقت مفضل للمادة",
  subject_avoided_time: "وقت غير مفضل للمادة",
  assignment_max_per_day: "الحد اليومي للإسناد",
  assignment_min_days: "الحد الأدنى لأيام التوزيع",
  teacher_max_lessons_per_day: "الحد اليومي للمعلم",
  section_max_lessons_per_day: "الحد اليومي للشعبة",
  teacher_max_consecutive_lessons: "أقصى حصص متتالية للمعلم",
  section_max_consecutive_lessons: "أقصى حصص متتالية للشعبة",
  assignment_avoid_same_day_repeat: "تجنب تكرار الإسناد في اليوم",
  assignment_require_consecutive_block: "حصة مزدوجة / ثلاثية",
  assignment_forbid_consecutive: "منع التتالي",
  assignment_min_gap: "فاصل أدنى بين حصص الإسناد",
  assignments_same_time: "إسنادان في الوقت نفسه",
  assignments_not_same_time: "إسنادان ليسا في الوقت نفسه",
  assignments_same_day: "إسنادان في اليوم نفسه",
  assignments_different_day: "إسنادان في يومين مختلفين",
  assignment_before_assignment: "إسناد قبل إسناد",
  assignment_required_resource_type: "نوع مورد إلزامي",
  assignment_preferred_resource: "مورد مفضل",
};
const relationshipTypes = new Set(["assignments_same_time","assignments_not_same_time","assignments_same_day","assignments_different_day","assignment_before_assignment"]);
const limitTypes = new Set(["assignment_max_per_day","teacher_max_lessons_per_day","section_max_lessons_per_day","teacher_max_consecutive_lessons","section_max_consecutive_lessons"]);

const minutes = (value: number) => `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
const statusLabel: Record<string, string> = { queued: "قيد الانتظار", running: "قيد التوليد", completed: "اكتمل", infeasible: "تعذر إيجاد حل", unknown: "انتهى الوقت دون حل مثبت", failed: "فشل التوليد" };

export function TimetableWorkspace() {
  const [schools, setSchools] = useState<School[]>([]);
  const [setups, setSetups] = useState<Record<string, SetupSnapshot>>({});
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [scope, setScope] = useState<ProjectSchool[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [report, setReport] = useState<Preflight | null>(null);
  const [run, setRun] = useState<SolveRun | null>(null);
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [week, setWeek] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [profile,setProfile]=useState("balanced");
  const [customWeights,setCustomWeights]=useState({teacher_gaps:8,first_period_fairness:5,last_period_fairness:5,teaching_streaks:7});
  const [quality,setQuality]=useState<QualityReport|null>(null);
  const [explanation,setExplanation]=useState<PlacementExplanation|null>(null);
  const [name, setName] = useState("");
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [deleteRule, setDeleteRule] = useState<Rule | null>(null);
  const partialCodes=new Set(["section_capacity_shortage","teacher_capacity_shortage","resource_structural_shortage","occurrence_without_candidate_slot"]);
  const errorDiagnostics=report?.diagnostics.filter(item=>item.severity==="error")??[];
  const partialOnly=Boolean(report?.errors&&errorDiagnostics.length===report.errors&&errorDiagnostics.every(item=>partialCodes.has(item.code)));

  async function load() {
    const schoolList = await setupApi.schools();
    const snapshots = Object.fromEntries(await Promise.all(schoolList.map(async item => [item.id, await setupApi.snapshot(item.id)])));
    const projectList = await projectApi.list();
    setSchools(schoolList);
    setSetups(snapshots);
    setProjects(projectList);
  }

  useEffect(() => {
    const timer = window.setTimeout(() => { void load().catch(showError); }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!selected || !run || !["queued", "running"].includes(run.status)) return;
    const timer = window.setInterval(() => {
      projectApi.solveRun(selected.id, run.id).then(setRun).catch(showError);
    }, 750);
    return () => window.clearInterval(timer);
  }, [selected, run]);

  useEffect(() => {
    if (!selected || run?.status !== "completed" || !run.candidates.length) return;
    projectApi.candidate(selected.id, run.candidates[0].id).then(value => { setCandidate(value); setWeek(0); }).catch(showError);
  }, [selected, run]);

  function showError(reason: unknown) {
    setError(reason instanceof Error ? reason.message : "تعذر تنفيذ العملية");
  }

  async function open(project: Project) {
    setSelected(project);
    setScope(project.schools);
    setReport(null);
    setRun(null);
    setCandidate(null);
    setEditingRule(null);
    const [projectRules, latestRun] = await Promise.all([
      projectApi.rules(project.id),
      projectApi.latestSolve(project.id),
    ]);
    setRules(projectRules);
    setRun(latestRun);
    if (latestRun?.status === "completed" && latestRun.candidates.length) {
      setNotice("تم تحميل آخر جدول مولّد ومحفوظ لهذا المشروع.");
    }
  }

  function defaultScope(): ProjectSchool[] {
    const first = schools[0];
    const term = first ? setups[first.id]?.terms[0] : undefined;
    return first && term ? [{ school_id: first.id, term_id: String(term.id), cycle_phase_offset: 0 }] : [];
  }

  async function create() {
    const schoolsScope = scope.length ? scope : defaultScope();
    if (!name.trim() || !schoolsScope.length) return;
    setBusy(true);
    try {
      const created = await projectApi.create({ name_ar: name.trim(), scope_type: schoolsScope.length === 1 ? "school" : "schools", schools: schoolsScope });
      setName("");
      await load();
      await open(created);
      setNotice("تم إنشاء المشروع وحفظ نطاقه.");
    } catch (reason) { showError(reason); } finally { setBusy(false); }
  }

  function toggleSchool(schoolId: string, checked: boolean) {
    if (!checked) return setScope(current => current.filter(item => item.school_id !== schoolId));
    const term = setups[schoolId]?.terms[0];
    if (term) setScope(current => [...current, { school_id: schoolId, term_id: String(term.id), cycle_phase_offset: 0 }]);
  }

  function updateScope(schoolId: string, patch: Partial<ProjectSchool>) {
    setScope(current => current.map(item => item.school_id === schoolId ? { ...item, ...patch } : item));
  }

  async function saveScope() {
    if (!selected || !scope.length) return;
    setBusy(true);
    try {
      const updated = await projectApi.update(selected.id, { name_ar: selected.name_ar, description: selected.description ?? null, scope_type: scope.length === 1 ? "school" : "schools", schools: scope });
      setSelected(updated);
      setProjects(current => current.map(item => item.id === updated.id ? updated : item));
      setReport(null);
      setNotice("تم حفظ نطاق المدارس والفصول ومحاذاة الدورة.");
    } catch (reason) { showError(reason); } finally { setBusy(false); }
  }

  async function runPreflight() {
    if (!selected) return;
    try { setReport(await projectApi.preflight(selected.id)); } catch (reason) { showError(reason); }
  }

  async function generate() {
    if (!selected) return;
    setBusy(true); setError(""); setCandidate(null);
    try { setRun(await projectApi.solve(selected.id,{candidate_count:3,time_limit_seconds:10,seed:0,optimization_profile:profile,allow_partial:partialOnly,...(profile==="custom"?{optimization_weights:customWeights}:{})})); } catch (reason) { showError(reason); } finally { setBusy(false); }
  }

  async function saveRule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = new FormData(event.currentTarget);
    const type = String(form.get("rule_type"));
    const severity = String(form.get("severity") || (softTypes.has(type) ? "soft" : "hard")) as "soft"|"hard";
    const targetKey=String(form.get("target_key")); const targetId=String(form.get("target_id"));
    const selector:Record<string,unknown>=relationshipTypes.has(type)?{assignment_ids:[targetId,String(form.get("second_target_id"))]}:{[targetKey]:targetId};
    if(type==="assignment_preferred_resource") selector.resource_id=String(form.get("second_target_id"));
    let parameters:Record<string,unknown>={}; const numeric=Number(form.get("numeric_value")||1);
    if(limitTypes.has(type)) parameters={maximum:numeric}; else if(type==="assignment_min_days") parameters={minimum_days:numeric}; else if(type==="assignment_require_consecutive_block") parameters={block_size:numeric}; else if(type==="assignment_min_gap") parameters={minimum_gap_minutes:numeric}; else if(type==="assignment_required_resource_type") parameters={resource_type:String(form.get("resource_type")||"room")}; else if(!relationshipTypes.has(type)&&!["assignment_avoid_same_day_repeat","assignment_forbid_consecutive","assignment_preferred_resource"].includes(type)) parameters={weekday_index:Number(form.get("weekday_index"))};
    const payload = {
      label: String(form.get("label")), rule_type: type, severity,
      weight: severity === "soft" ? Number(form.get("weight") || 50) : null,
      selector, parameters, enabled: editingRule?.enabled ?? true,
    };
    try {
      if (editingRule) await projectApi.updateRule(selected.id, editingRule.id, payload);
      else await projectApi.saveRule(selected.id, payload);
      setRules(await projectApi.rules(selected.id)); setEditingRule(null); setReport(null);
      setNotice(editingRule ? "تم تحديث القاعدة." : "تمت إضافة القاعدة.");
      event.currentTarget.reset();
    } catch (reason) { showError(reason); }
  }

  async function refreshRules(action: () => Promise<unknown>) {
    if (!selected) return;
    try { await action(); setRules(await projectApi.rules(selected.id)); setReport(null); } catch (reason) { showError(reason); }
  }

  const weeks = useMemo(() => [...new Set(candidate?.entries.map(item => item.project_cycle_week_index) ?? [])], [candidate]);
  const visibleEntries = candidate?.entries.filter(item => item.project_cycle_week_index === week) ?? [];

  return <div className="content timetable-space">
    <div className="welcome"><div><p className="eyebrow">المرحلة الثانية</p><h1>مشاريع الجداول الذكية</h1><p>ابنِ نطاق المشروع، افحص الجاهزية، ثم ولّد بدائل فعلية بواسطة CP-SAT.</p></div><button className="primary generate-button" disabled={!selected || !report || (report.errors > 0&&!partialOnly) || busy || run?.status === "queued" || run?.status === "running"} onClick={() => void generate()}>{busy ? "جارٍ البدء…" : partialOnly?"توليد جدول جزئي":"توليد الجدول"}</button></div>
    {error && <p className="error-banner" role="alert">{error}<button aria-label="إغلاق الخطأ" onClick={() => setError("")}>×</button></p>}
    {notice && <p className="success-banner" role="status">{notice}</p>}

    <section className="project-create"><label>اسم المشروع<input aria-label="اسم المشروع" value={name} onChange={event => setName(event.target.value)} placeholder="مثال: جدول الفصل الأول" /></label><button className="primary" disabled={busy} onClick={() => void create()}>إنشاء مشروع</button></section>
    <div className="project-layout"><section className="project-list"><h2>المشاريع</h2>{projects.length ? projects.map(project => <button className={selected?.id === project.id ? "selected" : ""} key={project.id} onClick={() => void open(project)}><strong>{project.name_ar}</strong><span>{project.schools.length} مدرسة · {project.status}</span></button>) : <p className="empty-state">لا توجد مشاريع بعد.</p>}</section>
      {selected && <section className="project-detail"><div className="section-heading"><div><h2>{selected.name_ar}</h2><p>اختر كل مدرسة وفصلها ومحاذاة أسبوعها داخل دورة المشروع.</p></div><button onClick={() => void saveScope()} disabled={busy || !scope.length}>حفظ النطاق</button></div>
        <div className="scope-editor">{schools.map(school => { const scoped = scope.find(item => item.school_id === school.id); const setup = setups[school.id]; return <article key={school.id} className={scoped ? "scope-active" : ""}><label className="scope-check"><input type="checkbox" checked={Boolean(scoped)} onChange={event => toggleSchool(school.id, event.target.checked)} />{school.name_ar}</label>{scoped && <div className="scope-controls"><label>الفصل<select aria-label={`فصل ${school.name_ar}`} value={scoped.term_id} onChange={event => updateScope(school.id, { term_id: event.target.value })}>{setup?.terms.map(term => <option key={term.id} value={String(term.id)}>{String(term.name_ar)}</option>)}</select></label><label>محاذاة الدورة<select aria-label={`محاذاة ${school.name_ar}`} value={scoped.cycle_phase_offset} onChange={event => updateScope(school.id, { cycle_phase_offset: Number(event.target.value) })}>{(setup?.patterns.length ? setup.patterns : [{ id: "one" }]).map((_, index) => <option key={index} value={index}>الأسبوع {index + 1}</option>)}</select></label></div>}</article>; })}</div>
        <div className="preflight-actions"><label>ملف التحسين<select aria-label="ملف التحسين" value={profile} onChange={e=>setProfile(e.target.value)}><option value="balanced">متوازن</option><option value="teacher_comfort">راحة المعلمين</option><option value="student_rhythm">إيقاع تعلم الطلاب</option><option value="administration_priorities">أولويات الإدارة</option><option value="custom">مخصص</option></select></label>{profile==="custom"&&<div className="custom-profile"><label>فجوات المعلمين<input aria-label="وزن فجوات المعلمين" type="number" min="0" max="1000" value={customWeights.teacher_gaps} onChange={e=>setCustomWeights(x=>({...x,teacher_gaps:Number(e.target.value)}))}/></label><label>عدالة الحصة الأولى<input aria-label="وزن عدالة الحصة الأولى" type="number" min="0" max="1000" value={customWeights.first_period_fairness} onChange={e=>setCustomWeights(x=>({...x,first_period_fairness:Number(e.target.value)}))}/></label><label>عدالة الحصة الأخيرة<input aria-label="وزن عدالة الحصة الأخيرة" type="number" min="0" max="1000" value={customWeights.last_period_fairness} onChange={e=>setCustomWeights(x=>({...x,last_period_fairness:Number(e.target.value)}))}/></label><label>تتابع التدريس<input aria-label="وزن تتابع التدريس" type="number" min="0" max="1000" value={customWeights.teaching_streaks} onChange={e=>setCustomWeights(x=>({...x,teaching_streaks:Number(e.target.value)}))}/></label></div>}<button className="primary" onClick={() => void runPreflight()}>تشغيل فحص الجاهزية</button>{report && <div className={`readiness ${report.errors ? "blocked" : "ready"}`} role="status"><h3>{report.readiness}</h3><p>{report.errors} أخطاء · {report.warnings} تحذيرات</p>{partialOnly&&<strong>يمكن إنشاء جدول جزئي الآن، وستظهر الحصص غير الموزعة بالاسم.</strong>}<div className="diagnostic-list">{report.diagnostics.map((item,index)=><article key={`${item.code}-${index}`}><b>{item.message??item.message_key}</b>{item.suggested_remediation&&<span>{item.suggested_remediation}</span>}</article>)}</div></div>}</div>

        {run && <section className={`solve-status status-${run.status}`} aria-live="polite"><div><span>حالة التوليد</span><h3>{statusLabel[run.status]}</h3></div><code title="بصمة مدخلات الجدولة">{run.input_fingerprint.slice(0, 12)}</code>{run.diagnostics.map((item,index)=><div className={item.code==="partial_schedule"?"partial-diagnostic":""} key={`${item.code}-${index}`}><p>{item.message??item.message_key??item.code}</p>{item.unscheduled_assignments?.map(row=><p key={row.assignment_id}><strong>{row.subject}</strong> · {row.sections.join(" + ")} · {row.teachers.join(" + ")} — غير موزع: {row.unscheduled_count}</p>)}</div>)}</section>}
        {run?.status === "completed" && <section className="candidate-view"><h2>الجداول المولّدة</h2><p className="candidate-hint">هذه آخر نتيجة محفوظة للمشروع. اختر البديل لعرض حصصه.</p><div className="candidate-tabs" aria-label="بدائل الجدول">{run.candidates.map(item => <button className={candidate?.id === item.id ? "selected" : ""} key={item.id} onClick={() => { projectApi.candidate(selected.id, item.id).then(detail => { setCandidate(detail); setWeek(0); setQuality(null);setExplanation(null); }).catch(showError); }}>البديل {item.rank}<small>{item.total_penalty} جزاء · اختلاف {item.diversity_count}</small></button>)}</div>{candidate && <><div className="week-tabs" aria-label="أسابيع دورة المشروع">{weeks.map(item => <button className={week === item ? "selected" : ""} key={item} onClick={() => setWeek(item)}>أسبوع المشروع {item + 1}</button>)}</div><div className="schedule-preview">{visibleEntries.length ? visibleEntries.map(entry => <article className="lesson-card" key={entry.id}><time>{weekdays[entry.weekday_index]} · {minutes(entry.starts_at_minute)}–{minutes(entry.ends_at_minute)}</time><h4>{entry.subject.name_ar}</h4><p>{entry.teachers.map(item => item.name_ar).join(" + ")}</p><p>الشعبة: {entry.sections.map(item => item.name_ar).join(" + ")}</p>{entry.resources.length > 0 && <p>المورد: {entry.resources.map(item => item.name_ar).join(" + ")}</p>}{selected.schools.length > 1 && <span>{entry.school.name_ar}</span>}<button onClick={()=>void projectApi.candidateExplanation(selected.id,candidate.id,entry.occurrence_id).then(setExplanation).catch(showError)}>لماذا هنا؟</button></article>) : <p className="empty-state">لا توجد حصص في هذا الأسبوع.</p>}</div><button onClick={()=>void projectApi.candidateQuality(selected.id,candidate.id).then(setQuality).catch(showError)}>جودة الجدول</button>{quality&&<aside className="quality-panel"><h3>تقرير الجودة الحقيقي</h3><p>المخالفات الإلزامية: {quality.hard_violations.length}</p><p>مجموع الجزاء الموزون: {quality.total_weighted_penalty}</p><p>فجوات المعلمين: {quality.teacher_gap_total}</p><p>مخالفات التوزيع: {quality.distribution_violations.length}</p></aside>}{explanation&&<aside className="explanation-panel"><h3>لماذا وُضعت هذه الحصة هنا؟</h3><p>الوقت المختار: {weekdays[explanation.chosen_slot.weekday_index]} {minutes(explanation.chosen_slot.starts_at_minute)}</p><p>{explanation.mandatory_rule_facts.length} قواعد إلزامية و{explanation.preference_rule_facts.length} قواعد تفضيلية مؤثرة.</p>{explanation.alternatives.slice(0,4).map(x=><p key={x.slot.id}>{x.status==="blocked"?"بديل مرفوض":x.status==="valid_but_worse"?"بديل صالح لكنه أسوأ":"بديل صالح"}: {minutes(x.slot.starts_at_minute)} · فرق الجزاء {x.penalty_delta}</p>)}</aside>}{candidate.penalty_breakdown.length > 0 && <div className="penalty-panel"><h3>تفصيل الجزاءات</h3>{candidate.penalty_breakdown.map(item => <p key={item.rule_id}>{ruleLabels[item.rule_type] ?? item.rule_type}: {item.violation_count} × {item.weight} = {item.weighted_penalty}</p>)}</div>}</>}</section>}

        <h2>باني قواعد الجدولة</h2><div className="rule-categories" aria-label="فئات القواعد"><span>التوفر والأوقات</span><span>توزيع الحصص</span><span>الحصص المتتالية</span><span>العلاقات</span><span>الموارد</span><span>الراحة والتوازن</span></div><form className="rule-form" key={editingRule?.id ?? "new"} onSubmit={saveRule}><input name="label" aria-label="وصف القاعدة" placeholder="مثال: لا تزيد رياضيات عن حصتين يوميًا" defaultValue={editingRule?.label} required /><select name="rule_type" aria-label="نوع القاعدة" defaultValue={editingRule?.rule_type ?? "teacher_unavailable"}>{Object.entries(ruleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><select name="severity" aria-label="أثر القاعدة" defaultValue={editingRule?.severity??"hard"}><option value="hard">إلزامية</option><option value="soft">تفضيلية</option></select><select name="target_key" aria-label="نوع المستهدف" defaultValue={editingRule ? Object.keys(editingRule.selector)[0] : "teacher_id"}><option value="teacher_id">معلم</option><option value="section_id">شعبة</option><option value="resource_id">مورد</option><option value="subject_id">مادة</option><option value="assignment_id">إسناد</option></select><input name="target_id" aria-label="معرف المستهدف" defaultValue={editingRule ? String((editingRule.selector.assignment_ids as string[]|undefined)?.[0]??Object.values(editingRule.selector)[0] ?? "") : ""} required /><input name="second_target_id" aria-label="معرف الإسناد أو المورد الثاني" defaultValue={editingRule ? String((editingRule.selector.assignment_ids as string[]|undefined)?.[1]??editingRule.selector.resource_id??"") : ""}/><select name="weekday_index" aria-label="اليوم" defaultValue={String(editingRule?.parameters.weekday_index ?? 0)}>{weekdays.map((day, index) => <option key={day} value={index}>{day}</option>)}</select><input name="numeric_value" aria-label="قيمة القاعدة" type="number" min="1" max="720" defaultValue={Number(editingRule?.parameters.maximum??editingRule?.parameters.minimum_days??editingRule?.parameters.block_size??editingRule?.parameters.minimum_gap_minutes??2)} /><select name="resource_type" aria-label="نوع المورد"><option value="room">غرفة</option><option value="science_lab">مختبر علوم</option><option value="computer_lab">معمل حاسب</option><option value="gym">صالة رياضية</option></select><input name="weight" aria-label="وزن التفضيل" type="number" min="1" max="1000" defaultValue={editingRule?.weight ?? 50} /><p className="rule-preview">تُحفظ القاعدة كعقد typed، ويتحقق الخادم من المستهدف والمعاملات قبل ترجمتها إلى CP-SAT.</p><button className="primary">{editingRule ? "حفظ التعديل" : "حفظ القاعدة"}</button>{editingRule && <button type="button" onClick={() => setEditingRule(null)}>إلغاء</button>}</form>
        <div className="rule-list">{rules.map(rule => <article key={rule.id} className={!rule.enabled ? "disabled-rule" : ""}><div><strong>{rule.label}</strong><span>{rule.severity === "hard" ? "إلزامي" : `تفضيل · وزن ${rule.weight}`} · {rule.enabled ? "مفعلة" : "معطلة"}</span></div><div className="rule-actions"><button onClick={() => setEditingRule(rule)}>تعديل</button><button onClick={() => void refreshRules(() => projectApi.duplicateRule(selected.id, rule.id))}>نسخ</button><button onClick={() => void refreshRules(() => projectApi.updateRule(selected.id, rule.id, { label: rule.label, description: rule.description ?? null, rule_type: rule.rule_type, severity: rule.severity, weight: rule.weight, selector: rule.selector, parameters: rule.parameters, enabled: !rule.enabled }))}>{rule.enabled ? "تعطيل" : "تفعيل"}</button><button className="danger" onClick={() => setDeleteRule(rule)}>حذف</button></div></article>)}</div>
      </section>}
    </div>
    {selected && <SchedulingAssistant projectId={selected.id} onConfirmed={async()=>{setRules(await projectApi.rules(selected.id));setReport(null);setNotice("تمت إضافة القواعد المؤكدة وستدخل في فحص الجاهزية والتوليد.")}} />}
    {selected && candidate && <TimetableEditor projectId={selected.id} candidate={candidate} />}
    {deleteRule && selected && <div className="dialog-backdrop"><section className="edit-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-rule-title"><h2 id="delete-rule-title">حذف القاعدة؟</h2><p>سيتم حذف «{deleteRule.label}» من المشروع.</p><div className="dialog-actions"><button onClick={() => setDeleteRule(null)}>إلغاء</button><button className="danger" onClick={() => void refreshRules(() => projectApi.removeRule(selected.id, deleteRule.id)).then(() => setDeleteRule(null))}>تأكيد الحذف</button></div></section></div>}
  </div>;
}
