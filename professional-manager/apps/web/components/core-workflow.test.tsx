import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { coreApi } from "@/lib/core-api";
import { CoreWorkflow } from "./core-workflow";

const snapshot = {
  school: { name_ar: "مدرسة النور" }, selected_stages: ["primary" as const], term_id: "term-internal", project_id: "project-internal", weekdays: [0,1,2,3,4],
  blocks: [{ id:"block-internal", label_ar:"الطابور", block_order:0, block_type:"assembly", period_number:null, starts_at:"06:45:00", ends_at:"07:00:00" }, { id:"lesson-internal", label_ar:"الحصة 1", block_order:1, block_type:"lesson", period_number:1, starts_at:"07:00:00", ends_at:"07:45:00" }],
  stages:[], grades:[], sections:[{id:"section-internal",name_ar:"الأول أ",grade_id:"grade-internal"}],
  teachers:[{id:"teacher-internal",name_ar:"أحمد",workload_limit:24,assigned:18,remaining:6,shared:false,availability:[]}],
  subjects:[{id:"subject-internal",name_ar:"رياضيات"}], assignments:[], assignments_count:0, rules_count:0,
  readiness:{basic_data:true,assignments:false,constraints:true,preflight:false},
};

vi.mock("@/lib/core-api", () => ({ coreApi: { snapshot:vi.fn(), saveDay:vi.fn(), editPeriod:vi.fn(), saveStructure:vi.fn(), createTeacher:vi.fn(), saveAvailability:vi.fn(), copyAvailability:vi.fn(), createSubject:vi.fn(), createAssignment:vi.fn(), createRule:vi.fn(), generate:vi.fn() } }));

describe("simplified core timetable workflow", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.mocked(coreApi.snapshot).mockResolvedValue(snapshot);
    Object.defineProperty(window,"localStorage",{configurable:true,value:{getItem:()=>"school-1",setItem:vi.fn()}});
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
});
