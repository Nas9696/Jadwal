import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { projectApi } from "@/lib/project-api";
import { TimetableEditor } from "./timetable-editor";

vi.mock("@/lib/project-api", () => ({ projectApi: { deriveWorking: vi.fn(), problem: vi.fn(), analyzeMove: vi.fn(), applyMove: vi.fn(), applySwap: vi.fn(), undo: vi.fn(), redo: vi.fn(), lockOccurrence: vi.fn(), unlock: vi.fn(), working: vi.fn(), repairPreview: vi.fn(), repairApply: vi.fn(), snapshots: vi.fn(), createSnapshot: vi.fn(), restoreSnapshot: vi.fn() } }));
const entry = { id: "e1", occurrence_id: "o1", slot_id: "s1", project_cycle_week_index: 0, weekday_index: 0, starts_at_minute: 480, ends_at_minute: 525, school: { id: "school", name_ar: "النور" }, subject: { id: "sub", name_ar: "رياضيات" }, teachers: [{ id: "t1", name_ar: "أحمد" }], sections: [{ id: "sec", name_ar: "أ" }], resources: [] };
const candidate = { id: "c1", rank: 1, solver_status: "optimal", total_penalty: 0, penalty_breakdown: [], solve_time_ms: 10, diversity_count: 0, entries: [entry] };
const table = { id: "w1", project_id: "p1", source_candidate_id: "c1", name: "نسخة العمل", version_number: 1, revision: 1, history_cursor: 0, status: "working", can_undo: false, can_redo: false, entries: [entry], locks: [] };
const slots = [{ id: "s1", school_id: "school", project_cycle_week_index: 0, weekday_index: 0, starts_at_minute: 480, ends_at_minute: 525, attendance_mode: "onsite" }, { id: "s2", school_id: "school", project_cycle_week_index: 0, weekday_index: 1, starts_at_minute: 480, ends_at_minute: 525, attendance_mode: "onsite" }];

describe("professional timetable editor", () => {
  beforeEach(() => { vi.mocked(projectApi.deriveWorking).mockResolvedValue(table); vi.mocked(projectApi.problem).mockResolvedValue({ slots }); vi.mocked(projectApi.working).mockResolvedValue(table); });
  afterEach(() => { cleanup(); vi.clearAllMocks(); });

  it("derives immutable candidate and exposes all authoritative views and locks", async () => {
    render(<TimetableEditor projectId="p1" candidate={candidate} />);
    fireEvent.click(screen.getByRole("button", { name: "فتح محرر الجدول" }));
    expect(await screen.findByText("محرر الجدول الاحترافي")).toBeInTheDocument();
    expect(projectApi.deriveWorking).toHaveBeenCalledWith("p1", "c1");
    for (const label of ["الجدول العام", "الشعبة", "المعلم", "المادة", "الغرفة / المورد"]) expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "قفل رياضيات" }));
    await waitFor(() => expect(projectApi.lockOccurrence).toHaveBeenCalledWith("p1", "o1", 1));
  });

  it("shows server conflict panel and explicit minimal repair preview", async () => {
    vi.mocked(projectApi.analyzeMove).mockResolvedValue({ revision: 1, occurrence_id: "o1", source_slot_id: "s1", valid: false, target_slot: slots[1], violations: [{ code: "teacher_conflict" }], teacher_conflicts: [{ occurrence_id: "o2" }], section_conflicts: [], resource_conflicts: [], hard_rule_violations: [], lock_violations: [], affected_entries: [{ occurrence_id: "o2" }], soft_penalty_delta: 0, swap_candidates: [], alternative_slots: [] });
    vi.mocked(projectApi.repairPreview).mockResolvedValue({ revision: 1, occurrence_id: "o1", target_slot_id: "s2", fingerprint: "a".repeat(64), total_moved_occurrences: 2, penalty_before: 0, penalty_after: 0, changes: [{ occurrence_id: "o1", from: { slot_id: "s1" }, to: { slot_id: "s2" }, reason: "حل التعارض" }] });
    render(<TimetableEditor projectId="p1" candidate={candidate} />); fireEvent.click(screen.getByRole("button", { name: "فتح محرر الجدول" })); await screen.findByText("رياضيات");
    const card = screen.getByText("رياضيات").closest("article"); const empty = screen.getByText("وقت متاح").closest("div");
    fireEvent.dragStart(card!); fireEvent.drop(empty!);
    expect(await screen.findByText(/المعلم مرتبط بحصة أخرى متداخلة/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "إصلاح تلقائي بأقل تغييرات" }));
    expect(await screen.findByText("معاينة فقط — لا توجد أي كتابة في قاعدة البيانات")).toBeInTheDocument();
    expect(screen.getByText("2 تغييرات مقترحة")).toBeInTheDocument();
  });
});
