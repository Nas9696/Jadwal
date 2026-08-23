import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setupApi } from "@/lib/setup-api";
import { projectApi } from "@/lib/project-api";
import { TimetableWorkspace } from "./timetable-workspace";

vi.mock("@/lib/setup-api", () => ({ setupApi: { schools: vi.fn(), snapshot: vi.fn() } }));
vi.mock("@/lib/project-api", () => ({ projectApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), rules: vi.fn(), saveRule: vi.fn(), updateRule: vi.fn(), duplicateRule: vi.fn(), removeRule: vi.fn(), preflight: vi.fn(), solve: vi.fn(), solveRun: vi.fn(), candidate: vi.fn() } }));

const school = { id: "s1", name_ar: "مدرسة النور", code: "S1" };
const setup = { school, years: [], terms: [{ id: "t1", name_ar: "الأول" }], shifts: [], patterns: [{ id: "w1", name_ar: "A" }, { id: "w2", name_ar: "B" }], days: [], blocks: [], stages: [], grades: [], sections: [] };
const project = { id: "p1", name_ar: "مشروع الفصل", status: "draft", scope_type: "school", schools: [{ school_id: "s1", term_id: "t1", cycle_phase_offset: 0 }] };
const completed = { id: "run1", project_id: "p1", status: "completed" as const, input_fingerprint: "abcdef123456789", solver_status: "optimal", diagnostics: [], candidates: [{ id: "c1", rank: 1, solver_status: "optimal", total_penalty: 0, penalty_breakdown: [], solve_time_ms: 20, diversity_count: 0 }, { id: "c2", rank: 2, solver_status: "optimal", total_penalty: 10, penalty_breakdown: [], solve_time_ms: 25, diversity_count: 1 }] };
const detail = (id: string, rank: number, subject: string) => ({ id, rank, solver_status: "optimal", total_penalty: rank - 1, penalty_breakdown: [], solve_time_ms: 20, diversity_count: rank - 1, entries: [{ id: `e${rank}`, occurrence_id: `o${rank}`, slot_id: "slot", project_cycle_week_index: 0, weekday_index: 0, starts_at_minute: 480, ends_at_minute: 525, school: { id: "s1", name_ar: "مدرسة النور" }, subject: { id: "sub", name_ar: subject }, teachers: [{ id: "t", name_ar: "أحمد" }], sections: [{ id: "sec", name_ar: "أ" }], resources: [] }] });

describe("timetable workspace", () => {
  beforeEach(() => {
    vi.mocked(setupApi.schools).mockResolvedValue([school]);
    vi.mocked(setupApi.snapshot).mockResolvedValue(setup);
    vi.mocked(projectApi.list).mockResolvedValue([project]);
    vi.mocked(projectApi.create).mockResolvedValue(project);
    vi.mocked(projectApi.update).mockResolvedValue(project);
    vi.mocked(projectApi.rules).mockResolvedValue([]);
    vi.mocked(projectApi.preflight).mockResolvedValue({ readiness: "توجد أخطاء تمنع التوليد", errors: 1, warnings: 0, diagnostics: [{ code: "no_lesson_slots", message: "لا توجد حصص قابلة للجدولة" }] });
    vi.mocked(projectApi.solve).mockResolvedValue(completed);
    vi.mocked(projectApi.candidate).mockImplementation(async (_projectId, id) => id === "c2" ? detail("c2", 2, "العلوم") : detail("c1", 1, "الرياضيات"));
  });
  afterEach(() => { cleanup(); vi.clearAllMocks(); });

  it("creates a real scoped project", async () => {
    render(<TimetableWorkspace />);
    await screen.findByText("مشروع الفصل");
    fireEvent.change(screen.getByLabelText("اسم المشروع"), { target: { value: "مشروع جديد" } });
    fireEvent.click(screen.getByRole("button", { name: "إنشاء مشروع" }));
    await waitFor(() => expect(projectApi.create).toHaveBeenCalledWith(expect.objectContaining({ name_ar: "مشروع جديد", schools: [expect.objectContaining({ term_id: "t1", cycle_phase_offset: 0 })] })));
  });

  it("shows factual preflight and keeps generation blocked", async () => {
    render(<TimetableWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: /مشروع الفصل/ }));
    fireEvent.click(await screen.findByRole("button", { name: "تشغيل فحص الجاهزية" }));
    expect(await screen.findByText("توجد أخطاء تمنع التوليد")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "توليد الجدول" })).toBeDisabled();
  });

  it("edits the visual school term and cycle phase scope", async () => {
    render(<TimetableWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: /مشروع الفصل/ }));
    fireEvent.change(screen.getByLabelText("محاذاة مدرسة النور"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "حفظ النطاق" }));
    await waitFor(() => expect(projectApi.update).toHaveBeenCalledWith("p1", expect.objectContaining({ schools: [expect.objectContaining({ cycle_phase_offset: 1 })] })));
  });

  it("runs generation and switches between persisted candidates", async () => {
    vi.mocked(projectApi.preflight).mockResolvedValue({ readiness: "جاهز للتوليد", errors: 0, warnings: 0, diagnostics: [] });
    render(<TimetableWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: /مشروع الفصل/ }));
    fireEvent.click(screen.getByRole("button", { name: "تشغيل فحص الجاهزية" }));
    await screen.findByText("جاهز للتوليد");
    fireEvent.click(screen.getByRole("button", { name: "توليد الجدول" }));
    expect(await screen.findByText("الرياضيات")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /البديل 2/ }));
    expect(await screen.findByText("العلوم")).toBeInTheDocument();
    expect(projectApi.candidate).toHaveBeenCalledWith("p1", "c2");
  });

  it("exposes rule edit copy toggle and delete actions", async () => {
    vi.mocked(projectApi.rules).mockResolvedValue([{ id: "r1", label: "عدم توفر أحمد", rule_type: "teacher_unavailable", severity: "hard", weight: null, selector: { teacher_id: "t1" }, parameters: { weekday_index: 0 }, enabled: true }]);
    render(<TimetableWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: /مشروع الفصل/ }));
    expect(await screen.findByRole("button", { name: "تعديل" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "نسخ" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "تعطيل" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "حذف" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "نسخ" }));
    await waitFor(() => expect(projectApi.duplicateRule).toHaveBeenCalledWith("p1", "r1"));
    fireEvent.click(screen.getByRole("button", { name: "تعطيل" }));
    await waitFor(() => expect(projectApi.updateRule).toHaveBeenCalledWith("p1", "r1", expect.objectContaining({ enabled: false })));
  });
});
