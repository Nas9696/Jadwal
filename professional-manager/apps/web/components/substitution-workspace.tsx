"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { masterApi, type TeacherSnapshot } from "@/lib/master-api";
import { projectApi, type Project, type WorkingTimetable } from "@/lib/project-api";
import {
  substitutionApi,
  type Absence,
  type Candidate,
  type CandidateList,
  type DailySummary,
  type SubstitutionNeed,
  type WaitingPolicy,
  type Workload,
} from "@/lib/substitution-api";

type Tab = "daily" | "workload" | "policy";
type PendingAssignment = { need: SubstitutionNeed; candidate: Candidate };

const today = () => new Date().toISOString().slice(0, 10);
const timeLabel = (minute: number) => `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
const toMinute = (value: string) => { const [hour, minute] = value.split(":").map(Number); return hour * 60 + minute; };
const nullableNumber = (data: FormData, key: string) => { const value = String(data.get(key) ?? "").trim(); return value === "" ? null : Number(value); };
const reasonLabels: Record<string, string> = {
  teacher_inactive: "هوية المعلم غير نشطة", no_active_project_membership: "لا يعمل في مدارس المشروع",
  same_as_absent_teacher: "هو المعلم الغائب نفسه", waiting_exempt: "مستثنى من الانتظار",
  teacher_absent: "مسجل غائبًا في هذا الوقت", teaching_time_collision: "لديه حصة متداخلة زمنيًا",
  substitution_time_collision: "مكلّف ببديل متداخل", hard_unavailable_rule: "قاعدة عدم توفر إلزامية",
  combined_workload_cap: "تجاوز حد الحمولة المجمعة", daily_waiting_cap: "تجاوز الحد اليومي للانتظار",
  weekly_waiting_cap: "تجاوز الحد الأسبوعي للانتظار",
};

export function SubstitutionWorkspace() {
  const [tab, setTab] = useState<Tab>("daily");
  const [schoolId, setSchoolId] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [working, setWorking] = useState<WorkingTimetable | null>(null);
  const [teachers, setTeachers] = useState<TeacherSnapshot | null>(null);
  const [date, setDate] = useState(today());
  const [week, setWeek] = useState(0);
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [workloads, setWorkloads] = useState<Workload[]>([]);
  const [policy, setPolicy] = useState<WaitingPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [absenceOpen, setAbsenceOpen] = useState(false);
  const [candidates, setCandidates] = useState<CandidateList | null>(null);
  const [pending, setPending] = useState<PendingAssignment | null>(null);
  const [pendingCancellation, setPendingCancellation] = useState<Absence | null>(null);

  const availableProjects = useMemo(() => projects.filter(project => project.schools.some(school => school.school_id === schoolId)), [projects, schoolId]);
  const activeTeachers = useMemo(() => teachers?.teachers.filter(card => card.teacher.is_active && card.membership.is_active) ?? [], [teachers]);

  const loadScope = useCallback(async (id?: string) => {
    const school = id ?? localStorage.getItem("pm-school") ?? "";
    if (!school) { setLoading(false); return; }
    setSchoolId(school); setLoading(true); setError("");
    try {
      const [allProjects, teacherData] = await Promise.all([projectApi.list(), masterApi.teachers(school)]);
      setProjects(allProjects); setTeachers(teacherData);
      const selected = allProjects.find(p => p.id === projectId && p.schools.some(s => s.school_id === school)) ?? allProjects.find(p => p.schools.some(s => s.school_id === school));
      setProjectId(selected?.id ?? "");
    } catch (cause) { setError((cause as Error).message); }
    finally { setLoading(false); }
  }, [projectId]);

  const loadDay = useCallback(async () => {
    if (!projectId) { setSummary(null); setWorking(null); return; }
    setLoading(true); setError("");
    try {
      const [current, daySummary, rows, currentPolicy] = await Promise.all([
        projectApi.working(projectId), substitutionApi.summary(projectId, date),
        substitutionApi.workloads(projectId, date), substitutionApi.policy(projectId),
      ]);
      setWorking(current); setSummary(daySummary); setWorkloads(rows); setPolicy(currentPolicy);
    } catch (cause) { setWorking(null); setSummary(null); setError((cause as Error).message); }
    finally { setLoading(false); }
  }, [date, projectId]);

  useEffect(() => { const timer = setTimeout(() => void loadScope(), 0); const handler = (event: Event) => void loadScope((event as CustomEvent<string>).detail); window.addEventListener("pm-school-change", handler); return () => { clearTimeout(timer); window.removeEventListener("pm-school-change", handler); }; }, [loadScope]);
  useEffect(() => { const timer = setTimeout(() => void loadDay(), 0); return () => clearTimeout(timer); }, [loadDay]);

  async function createAbsence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!working) return;
    const data = new FormData(event.currentTarget); const partial = data.get("partial") === "on";
    setBusy(true); setError("");
    try {
      await substitutionApi.createAbsence(projectId, {
        school_id: schoolId, teacher_id: String(data.get("teacher_id")), absence_date: date,
        project_cycle_week_index: week, working_timetable_revision: working.revision,
        full_day: !partial, starts_at_minute: partial ? toMinute(String(data.get("starts_at"))) : null,
        ends_at_minute: partial ? toMinute(String(data.get("ends_at"))) : null,
        reason_code: String(data.get("reason_code") || "other"), reason_text: String(data.get("reason_text") || "") || null,
      });
      setAbsenceOpen(false); setMessage("تم تسجيل الغياب واستخراج الحصص المتأثرة من نسخة العمل"); await loadDay();
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }

  async function inspectNeed(need: SubstitutionNeed) {
    setBusy(true); setError("");
    try { setCandidates(await substitutionApi.candidates(projectId, need.id)); }
    catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }

  async function assign() {
    if (!pending || !working) return; setBusy(true); setError("");
    try {
      await substitutionApi.assign(projectId, pending.need.id, {
        substitute_teacher_id: pending.candidate.teacher_id, need_version: pending.need.version,
        working_timetable_revision: working.revision,
        mode: pending.candidate.rank === 1 ? "recommended" : "manual_override",
      });
      setPending(null); setCandidates(null); setMessage("تم إسناد البديل بعد إعادة فحص الأهلية والتعارضات"); await loadDay();
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }

  async function unassign(need: SubstitutionNeed) {
    if (!working) return; setBusy(true);
    try { await substitutionApi.unassign(projectId, need.id, { need_version: need.version, working_timetable_revision: working.revision }); setMessage("أُلغي تكليف البديل مع بقاء سجل العملية"); await loadDay(); }
    catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }

  async function refreshAbsence(id: string) {
    if (!working) return; setBusy(true);
    try { await substitutionApi.refreshAbsence(projectId, id, working.revision); setMessage("تم تحديث الحصص المتأثرة وفق نسخة الجدول الحالية"); await loadDay(); }
    catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }

  async function cancelAbsence() {
    if (!pendingCancellation) return; setBusy(true); setError("");
    try { await substitutionApi.cancelAbsence(projectId, pendingCancellation.id); setPendingCancellation(null); setMessage("أُلغي سجل الغياب وتكليفاته مع الاحتفاظ بالسجل التاريخي"); await loadDay(); }
    catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }

  async function savePolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); setBusy(true);
    try {
      await substitutionApi.savePolicy(projectId, {
        combined_workload_limit: nullableNumber(data, "combined"), daily_waiting_limit: nullableNumber(data, "daily"),
        weekly_waiting_limit: nullableNumber(data, "weekly"), fairness_weight: Number(data.get("fairness")),
        specialty_preference_enabled: data.get("specialty") === "on", specialty_preference_weight: Number(data.get("specialty_weight")),
        same_school_preference_weight: Number(data.get("school_weight")), exclude_exempt_teachers: data.get("exclude") === "on", enabled: true,
      });
      setMessage("تم حفظ سياسة الانتظار على الخادم"); await loadDay();
    } catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }

  async function toggleExemption(row: Workload) {
    setBusy(true);
    try { await substitutionApi.saveProfile(projectId, row.teacher_id, { exempt: !row.exempt, custom_combined_limit: row.custom_combined_limit, custom_daily_limit: row.custom_daily_limit, custom_weekly_limit: row.custom_weekly_limit, notes: row.notes }); setMessage(row.exempt ? "أُلغي استثناء المعلم" : "تم استثناء المعلم من الانتظار"); await loadDay(); }
    catch (cause) { setError((cause as Error).message); } finally { setBusy(false); }
  }

  if (loading && !teachers) return <section className="content"><div className="skeleton" aria-label="جار تحميل الغياب والبدلاء" /></section>;
  return <section className="content substitution-page">
    <div className="page-heading"><div><span className="eyebrow">تشغيل يومي موثوق</span><h1>الغياب والبدلاء والانتظار</h1><p>سجل الغياب، راجع الحصص المتأثرة، ثم اختر بديلًا مؤهلًا بتفسير واضح.</p></div><button className="primary" disabled={!working || !activeTeachers.length} onClick={() => setAbsenceOpen(true)}>تسجيل غياب</button></div>
    {message && <div className="success-banner" role="status">✓ {message}</div>}{error && <div className="error-banner" role="alert">{error}</div>}
    <div className="substitution-filters"><label>مشروع الجدول<select aria-label="مشروع الجدول" value={projectId} onChange={event => setProjectId(event.target.value)}><option value="">اختر مشروعًا</option>{availableProjects.map(project => <option key={project.id} value={project.id}>{project.name_ar}</option>)}</select></label><label>تاريخ التشغيل<input aria-label="تاريخ التشغيل" type="date" value={date} onChange={event => setDate(event.target.value)} /></label><label>أسبوع دورة المشروع<input aria-label="أسبوع دورة المشروع" type="number" min="0" value={week} onChange={event => setWeek(Number(event.target.value))} /></label><span className={`revision-pill ${working ? "ready" : ""}`}>{working ? `نسخة العمل ${working.revision}` : "لا توجد نسخة عمل"}</span></div>
    <div className="workspace-tabs" role="tablist"><button className={tab === "daily" ? "active" : ""} onClick={() => setTab("daily")}>لوحة اليوم</button><button className={tab === "workload" ? "active" : ""} onClick={() => setTab("workload")}>النصاب والانتظار</button><button className={tab === "policy" ? "active" : ""} onClick={() => setTab("policy")}>سياسة الانتظار</button></div>
    {tab === "daily" && <DailyPanel summary={summary} busy={busy} inspect={inspectNeed} unassign={unassign} refresh={refreshAbsence} cancel={setPendingCancellation} />}
    {tab === "workload" && <WorkloadPanel rows={workloads} busy={busy} toggle={toggleExemption} />}
    {tab === "policy" && policy && <PolicyPanel policy={policy} busy={busy} save={savePolicy} />}
    {absenceOpen && <AbsenceDialog teachers={activeTeachers} busy={busy} submit={createAbsence} close={() => setAbsenceOpen(false)} />}
    {candidates && <CandidateDrawer data={candidates} choose={(candidate) => { const need = summary?.absences.flatMap(a => a.needs).find(n => n.id === candidates.need_id); if (need) setPending({ need, candidate }); }} close={() => setCandidates(null)} />}
    {pending && <div className="dialog-backdrop"><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-substitute"><h2 id="confirm-substitute">تأكيد تكليف البديل</h2><p>سيُكلّف <strong>{pending.candidate.teacher_name}</strong> بهذه الحصة. سيعيد الخادم فحص الوقت الحقيقي والنصاب والنسخة قبل الحفظ.</p>{pending.candidate.rank !== 1 && <p className="notice">هذا اختيار يدوي لبديل مؤهل ترتيبه {pending.candidate.rank}. لن يتم تجاوز أي مانع إلزامي.</p>}<div className="dialog-actions"><button className="secondary" onClick={() => setPending(null)}>إلغاء</button><button className="primary" disabled={busy} onClick={() => void assign()}>تأكيد التكليف</button></div></section></div>}
    {pendingCancellation && <div className="dialog-backdrop"><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="cancel-absence"><h2 id="cancel-absence">إلغاء سجل الغياب</h2><p>سيُلغى غياب <strong>{pendingCancellation.teacher_name}</strong> وكل تكليف بديل نشط تابع له. سيبقى سجل العمليات محفوظًا للمراجعة.</p><div className="dialog-actions"><button className="secondary" onClick={() => setPendingCancellation(null)}>رجوع</button><button className="danger-button" disabled={busy} onClick={() => void cancelAbsence()}>تأكيد إلغاء الغياب</button></div></section></div>}
  </section>;
}

function DailyPanel({ summary, busy, inspect, unassign, refresh, cancel }: { summary: DailySummary | null; busy: boolean; inspect: (need: SubstitutionNeed) => Promise<void>; unassign: (need: SubstitutionNeed) => Promise<void>; refresh: (id: string) => Promise<void>; cancel: (absence: Absence) => void }) {
  if (!summary) return <div className="empty-state"><h2>اختر مشروعًا له نسخة عمل</h2><p>عمليات الغياب تعتمد على الجدول الحالي المعتمد للمشروع.</p></div>;
  return <><div className="daily-metrics"><Metric label="المعلمون الغائبون" value={summary.absent_teachers} /><Metric label="الحصص المتأثرة" value={summary.needs} /><Metric label="تمت تغطيتها" value={summary.covered} tone="good" /><Metric label="بانتظار بديل" value={summary.uncovered} tone="warn" /></div>{summary.absences.length === 0 ? <div className="empty-state"><h2>لا يوجد غياب مسجل لهذا اليوم</h2><p>ابدأ بتسجيل غياب كامل أو جزئي، وستظهر الحصص المتأثرة هنا.</p></div> : <div className="absence-list">{summary.absences.map(absence => <article className="absence-card" key={absence.id}><header><div><span className="absence-avatar">{absence.teacher_name.slice(0, 2)}</span><div><h2>{absence.teacher_name}</h2><p>{absence.school_name} · {absence.full_day ? "غياب كامل" : `${timeLabel(absence.starts_at_minute!)}–${timeLabel(absence.ends_at_minute!)}`}</p></div></div><div className="absence-header-actions"><b className={`coverage ${absence.status}`}>{absence.status === "covered" ? "مغطى" : absence.status === "partially_covered" ? "مغطى جزئيًا" : "مفتوح"}</b><button className="danger-link" disabled={busy} onClick={() => cancel(absence)}>إلغاء الغياب</button></div></header>{absence.stale && <div className="stale-banner">تغيرت نسخة الجدول بعد تسجيل الغياب. <button disabled={busy} onClick={() => void refresh(absence.id)}>تحديث الحصص المتأثرة</button></div>}<div className="need-list">{absence.needs.length === 0 ? <p className="inline-empty">لا توجد حصة متأثرة ضمن وقت الغياب.</p> : absence.needs.filter(need => need.status !== "cancelled").map(need => <div className="need-row" key={need.id}><time>{timeLabel(need.starts_at_minute)}<span>{timeLabel(need.ends_at_minute)}</span></time><div><strong>{need.subject_name}</strong><small>{need.section_names.join("، ") || "دون شعبة"}</small></div>{need.assignment ? <div className="assigned-substitute"><span>البديل</span><b>{need.assignment.teacher_name}</b><small>الترتيب {need.assignment.rank} · {need.assignment.score} نقطة</small></div> : <span className="uncovered-dot">تحتاج بديلًا</span>}<button className={need.assignment ? "secondary" : "primary"} disabled={busy || need.stale} onClick={() => void (need.assignment ? unassign(need) : inspect(need))}>{need.assignment ? "إلغاء التكليف" : "عرض البدلاء"}</button></div>)}</div></article>)}</div>}</>;
}

function WorkloadPanel({ rows, busy, toggle }: { rows: Workload[]; busy: boolean; toggle: (row: Workload) => Promise<void> }) { return <div className="workload-table-wrap"><table className="workload-table"><thead><tr><th>المعلم</th><th>النصاب الأساسي</th><th>تدريس فعلي</th><th>انتظار هذا الأسبوع</th><th>المجموع / الحد</th><th>السعة المتبقية</th><th>السياسة</th></tr></thead><tbody>{rows.map(row => <tr key={row.teacher_id} className={row.exempt ? "exempt" : ""}><td><strong>{row.teacher_name}</strong>{row.exempt && <small>مستثنى</small>}</td><td>{row.base_target}</td><td>{row.teaching_load}</td><td>{row.assigned_this_week}</td><td>{row.teaching_load + row.assigned_this_week} / {row.combined_limit}</td><td><b>{row.remaining_capacity}</b></td><td><button className="secondary" disabled={busy} onClick={() => void toggle(row)}>{row.exempt ? "إلغاء الاستثناء" : "استثناء"}</button></td></tr>)}</tbody></table>{rows.length === 0 && <div className="empty-state"><h2>لا يوجد معلمون في نطاق المشروع</h2></div>}</div>; }

function PolicyPanel({ policy, busy, save }: { policy: WaitingPolicy; busy: boolean; save: (event: FormEvent<HTMLFormElement>) => Promise<void> }) { return <form className="policy-card" onSubmit={save}><div><h2>حدود الحمولة</h2><p>القيمة الفارغة للحد المجمع تستخدم النصاب الأساسي لكل معلم. القيمة صفر حد صالح.</p></div><div className="three-fields"><label>الحد المجمع<input name="combined" type="number" min="0" defaultValue={policy.combined_workload_limit ?? ""} /></label><label>حد الانتظار اليومي<input name="daily" type="number" min="0" defaultValue={policy.daily_waiting_limit ?? ""} /></label><label>حد الانتظار الأسبوعي<input name="weekly" type="number" min="0" defaultValue={policy.weekly_waiting_limit ?? ""} /></label></div><div className="three-fields"><label>وزن العدالة<input name="fairness" type="number" min="0" defaultValue={policy.fairness_weight} /></label><label>وزن التخصص<input name="specialty_weight" type="number" min="0" defaultValue={policy.specialty_preference_weight} /></label><label>وزن المدرسة نفسها<input name="school_weight" type="number" min="0" defaultValue={policy.same_school_preference_weight} /></label></div><label className="check-field"><input name="specialty" type="checkbox" defaultChecked={policy.specialty_preference_enabled} />استخدم التخصص كتفضيل soft في الترتيب، وليس شرط أهلية</label><label className="check-field"><input name="exclude" type="checkbox" defaultChecked={policy.exclude_exempt_teachers} />استبعد المعلمين المعفيين</label><button className="primary" disabled={busy}>حفظ السياسة</button></form>; }

function AbsenceDialog({ teachers, busy, submit, close }: { teachers: TeacherSnapshot["teachers"]; busy: boolean; submit: (event: FormEvent<HTMLFormElement>) => Promise<void>; close: () => void }) { const [partial, setPartial] = useState(false); return <div className="dialog-backdrop"><section className="edit-dialog" role="dialog" aria-modal="true" aria-labelledby="absence-dialog"><div className="dialog-heading"><div><span>سجل اليوم</span><h2 id="absence-dialog">تسجيل غياب معلم</h2></div><button aria-label="إغلاق" onClick={close}>×</button></div><form onSubmit={submit}><label>المعلم<select name="teacher_id" required>{teachers.map(card => <option key={card.teacher.id} value={String(card.teacher.id)}>{String(card.teacher.name_ar)}</option>)}</select></label><label className="check-field"><input type="checkbox" name="partial" checked={partial} onChange={event => setPartial(event.target.checked)} />غياب جزئي خلال وقت محدد</label>{partial && <div className="two-fields"><label>من<input name="starts_at" type="time" required defaultValue="08:00" /></label><label>إلى<input name="ends_at" type="time" required defaultValue="09:00" /></label></div>}<label>سبب الغياب<select name="reason_code"><option value="sick">مرضي</option><option value="official">مهمة رسمية</option><option value="emergency">طارئ</option><option value="other">آخر</option></select></label><label>ملاحظة<input name="reason_text" maxLength={300} /></label><div className="dialog-actions"><button type="button" className="secondary" onClick={close}>إلغاء</button><button className="primary" disabled={busy}>{busy ? "جار التسجيل…" : "تسجيل واستخراج الحصص"}</button></div></form></section></div>; }

function CandidateDrawer({ data, choose, close }: { data: CandidateList; choose: (candidate: Candidate) => void; close: () => void }) { return <div className="dialog-backdrop"><section className="candidate-drawer" role="dialog" aria-modal="true" aria-labelledby="candidate-title"><div className="dialog-heading"><div><span>ترتيب واقعي قابل للتفسير</span><h2 id="candidate-title">البدلاء المؤهلون</h2></div><button aria-label="إغلاق" onClick={close}>×</button></div><div className="candidate-list">{data.candidates.map(candidate => <article key={candidate.teacher_id}><b className="rank">{candidate.rank}</b><div><h3>{candidate.teacher_name}</h3><p>تدريس {candidate.teaching_load} · انتظار اليوم {candidate.assigned_today} · بعد التكليف {candidate.combined_after_assignment}/{candidate.combined_limit}</p><small>{candidate.specialty_considered ? candidate.specialty_match ? "تطابق تخصص مرجعي (+تفضيل)" : "لا تطابق تخصص، لكنه مؤهل" : "التخصص غير مستخدم في السياسة"}</small></div><strong className="score">{candidate.total_score}</strong><button className="primary" onClick={() => choose(candidate)}>{candidate.rank === 1 ? "اختيار الموصى به" : "اختيار يدوي"}</button></article>)}</div>{data.candidates.length === 0 && <div className="inline-empty">لا يوجد بديل مؤهل حاليًا. راجع الموانع أدناه.</div>}{data.excluded.length > 0 && <details className="excluded-list"><summary>معلمون غير مؤهلين ({data.excluded.length})</summary>{data.excluded.map(candidate => <p key={candidate.teacher_id}><strong>{candidate.teacher_name}</strong> — {candidate.blocking_reasons.map(reason => reasonLabels[reason] ?? reason).join("، ")}</p>)}</details>}</section></div>; }

function Metric({ label, value, tone = "" }: { label: string; value: number; tone?: string }) { return <div className={`daily-metric ${tone}`}><span>{label}</span><strong>{value}</strong></div>; }
