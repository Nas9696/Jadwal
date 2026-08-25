import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { coreApi } from "@/lib/core-api";
import { projectApi } from "@/lib/project-api";
import { CoreWorkflow } from "./core-workflow";

const snapshot = {
  school: { name_ar: "مدرسة النور" }, selected_stages: ["primary" as const], term_id: "term-internal", project_id: "project-internal", weekdays: [0,1,2,3,4],
  blocks: [{ id:"block-internal", label_ar:"الطابور", block_order:0, block_type:"assembly", period_number:null, starts_at:"06:45:00", ends_at:"07:00:00" }, { id:"lesson-internal", label_ar:"الحصة 1", block_order:1, block_type:"lesson", period_number:1, starts_at:"07:00:00", ends_at:"07:45:00" }],
  stages:[], grades:[{id:"grade-internal",name_ar:"الأول",stage_id:"stage-internal"}], sections:[{id:"section-internal",name_ar:"الأول أ",grade_id:"grade-internal"}],
  teachers:[{id:"teacher-internal",name_ar:"أحمد",workload_limit:24,assigned:18,remaining:6,shared:false,availability:[]}],
  subjects:[{id:"subject-internal",name_ar:"رياضيات"}], assignments:[], assignments_count:0, rules_count:0,
  readiness:{basic_data:true,assignments:false,constraints:true,preflight:false},
};

vi.mock("@/lib/core-api", () => ({ coreApi: { snapshot:vi.fn(), saveDay:vi.fn(), editPeriod:vi.fn(), saveStructure:vi.fn(), updateSection:vi.fn(), deleteSection:vi.fn(), orderSections:vi.fn(), createTeacher:vi.fn(), createTeachers:vi.fn(), uploadTeachers:vi.fn(), updateTeacher:vi.fn(), deleteTeacher:vi.fn(), mergeTeachers:vi.fn(), orderTeachers:vi.fn(), saveAvailability:vi.fn(), copyAvailability:vi.fn(), createSubject:vi.fn(), updateSubject:vi.fn(), deleteSubject:vi.fn(), orderSubjects:vi.fn(), saveCurriculum:vi.fn(), createAssignment:vi.fn(), updateAssignment:vi.fn(), deleteAssignment:vi.fn(), deduplicateAssignments:vi.fn(), transferAssignments:vi.fn(), createRule:vi.fn(), generate:vi.fn() } }));
vi.mock("@/lib/project-api", () => ({ projectApi: { latestSolve:vi.fn(),solveRun:vi.fn(),candidate:vi.fn(),candidateQuality:vi.fn(),candidateExplanation:vi.fn() } }));

describe("simplified core timetable workflow", () => {
  let storage: Record<string,string>;
  afterEach(cleanup);
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(coreApi.snapshot).mockResolvedValue(snapshot);
    vi.mocked(projectApi.latestSolve).mockResolvedValue(null);
    storage={"pm-school":"school-1"};
    Object.defineProperty(window,"localStorage",{configurable:true,value:{getItem:(key:string)=>storage[key]??null,setItem:(key:string,next:string)=>{storage[key]=next}}});
  });
  it("shows six human steps and hides technical vocabulary", async () => {
    render(<CoreWorkflow step={1}/>);
    expect(await screen.findByRole("heading",{name:"المدرسة واليوم الدراسي"})).toBeInTheDocument();
    const navigation=screen.getByRole("navigation",{name:"خطوات إنشاء الجدول"});
    expect(navigation.querySelectorAll("a")).toHaveLength(6);
    expect(document.body).not.toHaveTextContent(/UUID|Week Pattern|Shift|solver|Code/);
    expect(document.body).not.toHaveTextContent("teacher-internal");
    expect(document.querySelector("time")).toHaveTextContent("06:45");
    expect(document.querySelector("time")).toHaveTextContent("07:00");
  });
  it("submits the automatic school day with realistic defaults", async () => {
    vi.mocked(coreApi.saveDay).mockResolvedValue({});
    render(<CoreWorkflow step={1}/>);
    await screen.findByDisplayValue("مدرسة النور");
    fireEvent.click(screen.getByRole("button",{name:"إنشاء التوقيت تلقائيًا"}));
    await waitFor(()=>expect(coreApi.saveDay).toHaveBeenCalledWith("school-1",expect.objectContaining({assembly_start:"06:45",assembly_minutes:15,period_minutes:45,weekdays:[0,1,2,3,4]})));
  });
  it("edits the selected section from the compact details panel", async () => {
    vi.mocked(coreApi.updateSection).mockResolvedValue({});
    render(<CoreWorkflow step={2}/>);
    await screen.findByRole("heading",{name:"الصفوف والفصول",level:1});
    fireEvent.click(screen.getByRole("tab",{name:"إدارة الموجود"}));
    const input=screen.getByRole("textbox",{name:"اسم الفصل أو الشعبة"});
    expect(input).toHaveValue("الأول أ");
    fireEvent.change(input,{target:{value:"فصل الموهوبين"}});
    fireEvent.click(screen.getByRole("button",{name:"حفظ الاسم"}));
    await waitFor(()=>expect(coreApi.updateSection).toHaveBeenCalledWith("school-1","section-internal",{name_ar:"فصل الموهوبين"}));
  });
  it("builds sections with the selected naming pattern", async () => {
    vi.mocked(coreApi.saveStructure).mockResolvedValue({});
    render(<CoreWorkflow step={2}/>);
    await screen.findByRole("heading",{name:"الصفوف والفصول",level:1});
    fireEvent.click(screen.getByText("1 / أ"));
    fireEvent.click(screen.getByRole("button",{name:"إنشاء الصفوف والفصول"}));
    await waitFor(()=>expect(coreApi.saveStructure).toHaveBeenCalledWith("school-1",expect.objectContaining({naming_pattern:"number_slash_letter",reset_names:true})));
  });
  it("adds pasted teacher names in one action", async () => {
    vi.mocked(coreApi.createTeachers).mockResolvedValue({ created: 2, skipped: 0, names: ["أحمد علي", "سارة محمد"] });
    render(<CoreWorkflow step={3}/>);
    const input = await screen.findByRole("textbox", { name: "أسماء المعلمين" });
    fireEvent.change(input, { target: { value: "أحمد علي\nسارة محمد" } });
    expect(screen.getByText("2 اسم")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "إضافة جميع الأسماء" }));
    await waitFor(() => expect(coreApi.createTeachers).toHaveBeenCalledWith("school-1", ["أحمد علي", "سارة محمد"], 24, false));
  });
  it("starts assignment work from the selected teacher", async () => {
    vi.mocked(coreApi.createAssignment).mockResolvedValue({});
    render(<CoreWorkflow step={4}/>);
    expect(await screen.findByRole("heading",{name:"أحمد"})).toBeInTheDocument();
    expect(screen.getByText("18",{selector:".workload-meter strong"})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:/إضافة إسناد/}));
    fireEvent.click(screen.getByText("الأول أ",{selector:".section-groups label span"}));
    fireEvent.click(screen.getByRole("button",{name:/حفظ 1 إسناد/}));
    await waitFor(()=>expect(coreApi.createAssignment).toHaveBeenCalledWith("school-1",expect.objectContaining({teacher_id:"teacher-internal",subject_id:"subject-internal",section_ids:["section-internal"],weekly_occurrences:5})));
  });
  it("requires explicit approval before exceeding a teacher workload", async () => {
    vi.mocked(coreApi.snapshot).mockResolvedValue({...snapshot,teachers:[{...snapshot.teachers[0],assigned:23,remaining:1}]});
    vi.mocked(coreApi.createAssignment).mockResolvedValue({});
    render(<CoreWorkflow step={4}/>);
    await screen.findByRole("heading",{name:"أحمد"});
    fireEvent.click(screen.getByRole("button",{name:/إضافة إسناد/}));
    fireEvent.click(screen.getByText("الأول أ",{selector:".section-groups label span"}));
    fireEvent.click(screen.getByRole("button",{name:/حفظ 1 إسناد/}));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("سيصبح نصاب أحمد 28 حصة بدلًا من 24");
    fireEvent.click(screen.getByRole("button",{name:"اعتماد الزيادة وحفظ الإسناد"}));
    await waitFor(()=>expect(coreApi.createAssignment).toHaveBeenCalledWith("school-1",expect.objectContaining({allow_overload:true})));
  });
  it("offers moving assignments without an unsafe copy action", async () => {
    const assignment={id:"assignment-1",subject_id:"subject-internal",subject_name:"رياضيات",teacher_ids:["teacher-internal"],teacher_names:["أحمد"],section_ids:["section-internal"],section_names:["الأول أ"],weekly_occurrences:5};
    vi.mocked(coreApi.snapshot).mockResolvedValue({...snapshot,assignments:[assignment],assignments_count:1,teachers:[...snapshot.teachers,{id:"teacher-second",name_ar:"سارة",workload_limit:22,assigned:4,remaining:18,shared:false,availability:[]}]});
    render(<CoreWorkflow step={4}/>);
    await screen.findByRole("heading",{name:"أحمد"});
    fireEvent.click(screen.getByRole("checkbox",{name:""}));
    fireEvent.click(screen.getByRole("button",{name:/نقل المحدد/}));
    expect(screen.getByRole("button",{name:"تنفيذ النقل"})).toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"نسخ"})).not.toBeInTheDocument();
  });
  it("keeps the selected teacher when the assignment screen opens", async () => {
    storage["pm-selected-teacher"]="teacher-second";
    vi.mocked(coreApi.snapshot).mockResolvedValue({...snapshot,teachers:[...snapshot.teachers,{id:"teacher-second",name_ar:"سارة",workload_limit:22,assigned:4,remaining:18,shared:false,availability:[]}]});
    render(<CoreWorkflow step={4}/>);
    expect(await screen.findByRole("heading",{name:"سارة"})).toBeInTheDocument();
    expect(screen.getByText("4",{selector:".workload-meter strong"})).toBeInTheDocument();
  });
  it("deletes a teacher and their assignments after explicit confirmation", async () => {
    vi.mocked(coreApi.deleteTeacher).mockResolvedValue(undefined);
    render(<CoreWorkflow step={3}/>);
    await screen.findByRole("heading",{name:"أحمد"});
    fireEvent.click(screen.getByRole("button",{name:"حذف المعلم"}));
    expect(screen.getByRole("alertdialog")).toHaveTextContent("ستبقى المواد والفصول");
    fireEvent.click(screen.getByRole("button",{name:"حذف المعلم وإسناداته"}));
    await waitFor(()=>expect(coreApi.deleteTeacher).toHaveBeenCalledWith("school-1","teacher-internal",true));
  });
  it("saves the visible teacher order from the dedicated controls", async () => {
    const orderedSnapshot={...snapshot,teachers:[...snapshot.teachers,{id:"teacher-second",name_ar:"سارة",workload_limit:22,assigned:4,remaining:18,shared:false,availability:[]}]};
    vi.mocked(coreApi.snapshot).mockResolvedValue(orderedSnapshot);
    vi.mocked(coreApi.orderTeachers).mockResolvedValue({});
    render(<CoreWorkflow step={3}/>);
    await screen.findByRole("heading",{name:"أحمد"});
    fireEvent.click(screen.getByRole("button",{name:"خفض المعلم المحدد"}));
    await waitFor(()=>expect(coreApi.orderTeachers).toHaveBeenCalledWith("school-1",["teacher-second","teacher-internal"]));
  });
  it("separates the curriculum plan from teacher assignments", async () => {
    render(<CoreWorkflow step={4}/>);
    await screen.findByRole("heading",{name:"أحمد"});
    expect(screen.queryByRole("heading",{name:"الخطة الدراسية واحتياج المدرسة"})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab",{name:"الخطة الدراسية والاحتياج"}));
    expect(screen.getByRole("heading",{name:"الخطة الدراسية واحتياج المدرسة"})).toBeInTheDocument();
    expect(screen.getByRole("columnheader",{name:"الإجراءات"})).toBeInTheDocument();
  });
  it("does not flag the same subject in different numeric sections as duplicate", async () => {
    vi.mocked(coreApi.snapshot).mockResolvedValue({...snapshot,sections:[{id:"section-1",name_ar:"1 / 1",grade_id:"grade-internal"},{id:"section-2",name_ar:"1 / 2",grade_id:"grade-internal"}],assignments:[{id:"assignment-1",subject_id:"subject-internal",subject_name:"لغتي",teacher_ids:["teacher-internal"],teacher_names:["أحمد"],section_ids:["section-1"],section_names:["1 / 1"],weekly_occurrences:4},{id:"assignment-2",subject_id:"subject-internal",subject_name:"لغتي",teacher_ids:["teacher-internal"],teacher_names:["أحمد"],section_ids:["section-2"],section_names:["1 / 2"],weekly_occurrences:4}],assignments_count:2});
    render(<CoreWorkflow step={4}/>);
    await screen.findByText("الأول 1 / 1");
    expect(screen.queryByText(/إسنادًا مكررًا/)).not.toBeInTheDocument();
  });
  it("shows the latest generated alternative as a professional weekly grid", async () => {
    const run={id:"run-1",project_id:"project-internal",status:"completed" as const,input_fingerprint:"fingerprint",solver_status:"optimal",diagnostics:[],candidates:[{id:"candidate-1",rank:1,solver_status:"optimal",total_penalty:0,penalty_breakdown:[],solve_time_ms:80,diversity_count:0}]};
    const candidate={...run.candidates[0],entries:[{id:"entry-1",occurrence_id:"occurrence-1",slot_id:"slot-1",project_cycle_week_index:0,weekday_index:0,starts_at_minute:420,ends_at_minute:465,school:{id:"school-1",name_ar:"مدرسة النور"},subject:{id:"subject-internal",name_ar:"رياضيات"},teachers:[{id:"teacher-internal",name_ar:"أحمد"}],sections:[{id:"section-internal",name_ar:"الأول أ"}],resources:[]}]};
    vi.mocked(projectApi.latestSolve).mockResolvedValue(run);
    vi.mocked(projectApi.candidate).mockResolvedValue(candidate);
    render(<CoreWorkflow step={6}/>);
    expect(await screen.findByRole("table")).toHaveClass("weekly-grid");
    expect(screen.getByRole("columnheader",{name:"الأحد"})).toBeInTheDocument();
    expect(screen.getByRole("button",{name:/رياضيات أحمد/})).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("candidate-1");
  });
});
