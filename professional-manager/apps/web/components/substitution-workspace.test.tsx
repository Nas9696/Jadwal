import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { masterApi } from "@/lib/master-api";
import { projectApi } from "@/lib/project-api";
import { substitutionApi, type DailySummary } from "@/lib/substitution-api";
import { SubstitutionWorkspace } from "./substitution-workspace";

vi.mock("@/lib/master-api", () => ({ masterApi: { teachers: vi.fn() } }));
vi.mock("@/lib/project-api", () => ({ projectApi: { list: vi.fn(), working: vi.fn() } }));
vi.mock("@/lib/substitution-api", () => ({ substitutionApi: { policy: vi.fn(), savePolicy: vi.fn(), saveProfile: vi.fn(), workloads: vi.fn(), summary: vi.fn(), createAbsence: vi.fn(), refreshAbsence: vi.fn(), cancelAbsence: vi.fn(), candidates: vi.fn(), assign: vi.fn(), unassign: vi.fn() } }));

const project = { id: "p1", name_ar: "جدول المدرسة", status: "ready", scope_type: "school", schools: [{ school_id: "s1", term_id: "term1", cycle_phase_offset: 0 }] };
const teacherSnapshot = { school: { id: "s1", name_ar: "مدرسة النور", code: "S1" }, teachers: [{ teacher: { id: "t1", name_ar: "أحمد", is_active: true }, membership: { id: "m1", is_active: true }, schools: [], is_shared: false, assigned_workload: 14 }], available_teachers: [] };
const working = { id: "w1", project_id: "p1", source_candidate_id: "c1", name: "نسخة العمل", version_number: 1, revision: 4, history_cursor: 0, status: "working", can_undo: false, can_redo: false, entries: [], locks: [] };
const need = { id: "n1", absence_id: "a1", version: 1, occurrence_id: "o1", school_id: "s1", school_name: "مدرسة النور", subject_id: "sub1", subject_name: "رياضيات", section_names: ["أول متوسط أ"], project_cycle_week_index: 0, weekday_index: 0, starts_at_minute: 480, ends_at_minute: 525, status: "unassigned", source_working_revision: 4, stale: false, assignment: null };
const summary: DailySummary = { date: "2026-08-24", absent_teachers: 1, needs: 1, covered: 0, uncovered: 1, teachers_carrying_substitutions: 0, absences: [{ id: "a1", project_id: "p1", school_id: "s1", school_name: "مدرسة النور", teacher_id: "t1", teacher_name: "أحمد", absence_date: "2026-08-24", project_cycle_week_index: 0, weekday_index: 1, full_day: true, starts_at_minute: null, ends_at_minute: null, reason_code: "sick", reason_text: null, status: "open", working_timetable_revision: 4, stale: false, needs: [need] }] };
const policy = { id: "pol1", project_id: "p1", combined_workload_limit: 24, daily_waiting_limit: 2, weekly_waiting_limit: 5, fairness_weight: 5, specialty_preference_enabled: true, specialty_preference_weight: 2, same_school_preference_weight: 1, exclude_exempt_teachers: true, enabled: true };
const workloads = [{ teacher_id: "t1", teacher_name: "أحمد", base_target: 24, teaching_load: 14, assigned_today: 0, assigned_this_week: 0, combined_limit: 24, daily_limit: 2, weekly_limit: 5, remaining_capacity: 10, exempt: false, custom_combined_limit: null, custom_daily_limit: null, custom_weekly_limit: null, notes: null }];
const candidate = { teacher_id: "t2", teacher_name: "خالد", canonical_code: "T2", eligible: true, blocking_reasons: [], free_at_time: true, teaching_load: 12, assigned_today: 0, assigned_this_week: 1, combined_after_assignment: 14, combined_limit: 24, daily_limit: 2, weekly_limit: 5, exempt: false, specialty_considered: true, specialty_match: false, same_school_membership: true, score_breakdown: { remaining_capacity: 50, daily_fairness: 5 }, total_score: 55, rank: 2 };

describe("daily absence and substitution workspace", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", { configurable: true, value: { getItem: () => "s1" } });
    vi.mocked(projectApi.list).mockResolvedValue([project]); vi.mocked(projectApi.working).mockResolvedValue(working);
    vi.mocked(masterApi.teachers).mockResolvedValue(teacherSnapshot); vi.mocked(substitutionApi.summary).mockResolvedValue(summary);
    vi.mocked(substitutionApi.workloads).mockResolvedValue(workloads); vi.mocked(substitutionApi.policy).mockResolvedValue(policy);
    vi.mocked(substitutionApi.createAbsence).mockResolvedValue(summary.absences[0]);
    vi.mocked(substitutionApi.candidates).mockResolvedValue({ need_id: "n1", need_version: 1, working_timetable_revision: 4, candidates: [candidate], excluded: [] });
    vi.mocked(substitutionApi.assign).mockResolvedValue({ ...need, status: "assigned", version: 2, assignment: { id: "sa1", teacher_id: "t2", teacher_name: "خالد", score: 55, rank: 2, manual_override: true, score_breakdown: candidate.score_breakdown, eligibility_facts: {} } });
    vi.mocked(substitutionApi.cancelAbsence).mockResolvedValue({ ...summary.absences[0], status: "cancelled" });
  });
  afterEach(() => { cleanup(); vi.clearAllMocks(); });

  it("shows the Arabic daily workflow and extracts affected lessons", async () => {
    render(<SubstitutionWorkspace />);
    expect(await screen.findByText("الغياب والبدلاء والانتظار")).toBeInTheDocument();
    expect(await screen.findByText("رياضيات")).toBeInTheDocument();
    expect(screen.getByText("أول متوسط أ")).toBeInTheDocument();
    expect(screen.getByText("نسخة العمل 4")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "تسجيل غياب" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "غياب جزئي خلال وقت محدد" }));
    fireEvent.change(screen.getByLabelText("من"), { target: { value: "08:00" } });
    fireEvent.change(screen.getByLabelText("إلى"), { target: { value: "09:00" } });
    fireEvent.click(screen.getByRole("button", { name: "تسجيل واستخراج الحصص" }));
    await waitFor(() => expect(substitutionApi.createAbsence).toHaveBeenCalledWith("p1", expect.objectContaining({ full_day: false, starts_at_minute: 480, ends_at_minute: 540, working_timetable_revision: 4 })));
  });

  it("shows factual ranking and requires in-app confirmation for a lower-ranked eligible teacher", async () => {
    render(<SubstitutionWorkspace />); await screen.findByText("رياضيات");
    fireEvent.click(screen.getByRole("button", { name: "عرض البدلاء" }));
    expect(await screen.findByText("لا تطابق تخصص، لكنه مؤهل")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "اختيار يدوي" }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("لن يتم تجاوز أي مانع إلزامي");
    fireEvent.click(screen.getByRole("button", { name: "تأكيد التكليف" }));
    await waitFor(() => expect(substitutionApi.assign).toHaveBeenCalledWith("p1", "n1", { substitute_teacher_id: "t2", need_version: 1, working_timetable_revision: 4, mode: "manual_override" }));
  });

  it("shows 24/14 capacity facts and saves exemptions server-side", async () => {
    render(<SubstitutionWorkspace />); await screen.findByText("رياضيات");
    fireEvent.click(screen.getByRole("button", { name: "النصاب والانتظار" }));
    expect(screen.getByRole("cell", { name: "14" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "10" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "استثناء" }));
    await waitFor(() => expect(substitutionApi.saveProfile).toHaveBeenCalledWith("p1", "t1", expect.objectContaining({ exempt: true })));
  });

  it("uses an in-app confirmation before cancelling an absence", async () => {
    render(<SubstitutionWorkspace />); await screen.findByText("رياضيات");
    fireEvent.click(screen.getByRole("button", { name: "إلغاء الغياب" }));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("سيبقى سجل العمليات محفوظًا");
    fireEvent.click(screen.getByRole("button", { name: "تأكيد إلغاء الغياب" }));
    await waitFor(() => expect(substitutionApi.cancelAbsence).toHaveBeenCalledWith("p1", "a1"));
  });
});
