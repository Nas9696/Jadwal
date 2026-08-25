import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setupApi } from "@/lib/setup-api";
import { projectApi } from "@/lib/project-api";
import { TimetableWorkspace } from "./timetable-workspace";

vi.mock("@/lib/setup-api", () => ({ setupApi: { schools: vi.fn(), snapshot: vi.fn() } }));
vi.mock("@/lib/project-api", () => ({ projectApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), rules: vi.fn(), saveRule: vi.fn(), updateRule: vi.fn(), duplicateRule: vi.fn(), removeRule: vi.fn(), assistantParse:vi.fn(), assistantConfirm:vi.fn(), preflight: vi.fn(), solve: vi.fn(), latestSolve: vi.fn(), solveRun: vi.fn(), candidate: vi.fn(), candidateQuality:vi.fn(), candidateExplanation:vi.fn() } }));

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
    vi.mocked(projectApi.latestSolve).mockResolvedValue(null);
    vi.mocked(projectApi.assistantParse).mockResolvedValue({source_text:"لا تضع",status:"ready",parser_type:"deterministic_ar_v1",preview_token:"secure-preview-token-123456789",expires_at:"2026-08-23T12:00:00Z",clarifications:[],warnings:[],proposals:[{id:"proposal-1",rule_type:"teacher_unavailable",severity:"hard",weight:null,selector:{teacher_id:"t1"},parameters:{weekday_index:0,period_numbers:[1]},resolved_labels:{teacher:"أحمد"},arabic_summary:"لا توضع حصص أحمد في الحصة 1 يوم الأحد.",evidence:["hard:no-placement"]}]});
    vi.mocked(projectApi.assistantConfirm).mockResolvedValue({created_rules:[],consumed:true});
    vi.mocked(projectApi.preflight).mockResolvedValue({ readiness: "توجد أخطاء تمنع التوليد", errors: 1, warnings: 0, diagnostics: [{ code: "no_lesson_slots", message: "لا توجد حصص قابلة للجدولة" }] });
    vi.mocked(projectApi.solve).mockResolvedValue(completed);
    vi.mocked(projectApi.candidate).mockImplementation(async (_projectId, id) => id === "c2" ? detail("c2", 2, "العلوم") : detail("c1", 1, "الرياضيات"));
    vi.mocked(projectApi.candidateQuality).mockResolvedValue({hard_violations:[],total_weighted_penalty:12,penalty_breakdown:[],teacher_gaps:{t:1},teacher_gap_total:1,first_period_distribution:{t:2},last_period_distribution:{t:1},consecutive_streaks:[],distribution_violations:[],source:{type:"candidate"}});
    vi.mocked(projectApi.candidateExplanation).mockResolvedValue({occurrence_id:"o1",chosen_slot:{id:"slot",school_id:"s1",project_cycle_week_index:0,weekday_index:0,starts_at_minute:480,ends_at_minute:525,attendance_mode:"onsite"},mandatory_rule_facts:[],preference_rule_facts:[{rule_type:"subject_preferred_time"}],entity_facts:{teacher_ids:["t"]},alternatives:[{slot:{id:"late",school_id:"s1",project_cycle_week_index:0,weekday_index:0,starts_at_minute:525,ends_at_minute:570,attendance_mode:"onsite"},status:"valid_but_worse",blocking_facts:[],penalty_delta:25}]});
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

  it("allows partial generation only for capacity shortages", async () => {
    vi.mocked(projectApi.preflight).mockResolvedValue({
      readiness: "السعة لا تكفي للجدول الكامل",
      errors: 1,
      warnings: 0,
      diagnostics: [{
        severity: "error",
        code: "section_capacity_shortage",
        message: "الشعبة الرابع — 4 / 2: مطلوب 33 حصة، والمتاح 30 فقط (عجز 3).",
        suggested_remediation: "زد الأوقات الأسبوعية بمقدار 3 أو خفّض إسنادات الشعبة بالمقدار نفسه.",
      }],
    });
    render(<TimetableWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: /مشروع الفصل/ }));
    fireEvent.click(screen.getByRole("button", { name: "تشغيل فحص الجاهزية" }));
    expect(await screen.findByText(/الرابع — 4 \/ 2/)).toBeInTheDocument();
    const button = screen.getByRole("button", { name: "توليد جدول جزئي" });
    expect(button).toBeEnabled();
    fireEvent.click(button);
    await waitFor(() => expect(projectApi.solve).toHaveBeenCalledWith("p1", expect.objectContaining({ allow_partial: true })));
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

  it("loads the latest persisted result when reopening a project", async () => {
    vi.mocked(projectApi.latestSolve).mockResolvedValue(completed);
    render(<TimetableWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: /مشروع الفصل/ }));
    expect(await screen.findByText("الجداول المولّدة")).toBeInTheDocument();
    expect(await screen.findByText("الرياضيات")).toBeInTheDocument();
    expect(screen.getByText("تم تحميل آخر جدول مولّد ومحفوظ لهذا المشروع.")).toBeInTheDocument();
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

  it("shows advanced RTL rule categories and sends the server optimization profile",async()=>{
    vi.mocked(projectApi.preflight).mockResolvedValue({readiness:"جاهز للتوليد",errors:0,warnings:0,diagnostics:[]});
    render(<TimetableWorkspace/>);fireEvent.click(await screen.findByRole("button",{name:/مشروع الفصل/}));
    expect(screen.getByText("توزيع الحصص")).toBeInTheDocument();expect(screen.getByText("الحصص المتتالية")).toBeInTheDocument();expect(screen.getByText("الراحة والتوازن")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("ملف التحسين"),{target:{value:"teacher_comfort"}});fireEvent.click(screen.getByRole("button",{name:"تشغيل فحص الجاهزية"}));await screen.findByText("جاهز للتوليد");fireEvent.click(screen.getByRole("button",{name:"توليد الجدول"}));
    await waitFor(()=>expect(projectApi.solve).toHaveBeenCalledWith("p1",expect.objectContaining({optimization_profile:"teacher_comfort"})));
  });

  it("renders factual quality and placement explanation panels",async()=>{
    vi.mocked(projectApi.preflight).mockResolvedValue({readiness:"جاهز للتوليد",errors:0,warnings:0,diagnostics:[]});render(<TimetableWorkspace/>);fireEvent.click(await screen.findByRole("button",{name:/مشروع الفصل/}));fireEvent.click(screen.getByRole("button",{name:"تشغيل فحص الجاهزية"}));await screen.findByText("جاهز للتوليد");fireEvent.click(screen.getByRole("button",{name:"توليد الجدول"}));await screen.findByText("الرياضيات");fireEvent.click(screen.getByRole("button",{name:"جودة الجدول"}));expect(await screen.findByText("مجموع الجزاء الموزون: 12")).toBeInTheDocument();fireEvent.click(screen.getByRole("button",{name:"لماذا هنا؟"}));expect(await screen.findByText(/بديل صالح لكنه أسوأ/)).toHaveTextContent("فرق الجزاء 25");
  });

  it("previews Arabic proposals without auto-saving and confirms explicitly",async()=>{
    render(<TimetableWorkspace/>);fireEvent.click(await screen.findByRole("button",{name:/مشروع الفصل/}));
    fireEvent.change(screen.getByLabelText("طلب قاعدة الجدولة"),{target:{value:"لا تضع للأستاذ أحمد الحصة الأولى يوم الأحد"}});
    fireEvent.click(screen.getByRole("button",{name:"معاينة القاعدة"}));
    expect(await screen.findByText(/لا توضع حصص أحمد/)).toBeInTheDocument();expect(projectApi.saveRule).not.toHaveBeenCalled();expect(projectApi.assistantConfirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"اعتماد القواعد المحددة"}));
    await waitFor(()=>expect(projectApi.assistantConfirm).toHaveBeenCalledWith("p1",{preview_token:"secure-preview-token-123456789",proposal_ids:["proposal-1"]}));
  });
});
