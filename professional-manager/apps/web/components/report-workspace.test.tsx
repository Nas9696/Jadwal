import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { projectApi } from "@/lib/project-api";
import { reportApi } from "@/lib/report-api";
import { ReportWorkspace } from "./report-workspace";

vi.mock("@/lib/project-api",()=>({projectApi:{list:vi.fn()}}));
vi.mock("@/lib/report-api",()=>({reportApi:{options:vi.fn(),preview:vi.fn(),export:vi.fn()}}));

const project={id:"p1",name_ar:"مشروع المدرسة",status:"active",scope_type:"school",schools:[]};
const options={schools:[{id:"s1",label:"مدرسة النور",school_id:"s1",school_ids:["s1"]}],teachers:[{id:"t1",label:"أحمد",school_id:null,school_ids:["s1"]}],sections:[{id:"sec1",label:"الأول أ",school_id:"s1",school_ids:["s1"]}],subjects:[],resources:[]};
const dataset={report_type:"teacher_timetable" as const,title:"جدول المعلم",subtitle:"مشروع المدرسة",source:{kind:"working" as const,revision:7,version_number:2,project_name:"مشروع المدرسة"},columns:["اليوم","المعلمون"],rows:[{row_id:"r1",weekday_label:"الأحد",teacher_names:["أحمد"],section_names:[],resource_names:[]}],row_count:1,stale:false,warnings:[]};

describe("report workspace",()=>{
  beforeEach(()=>{vi.mocked(projectApi.list).mockResolvedValue([project]);vi.mocked(reportApi.options).mockResolvedValue(options);vi.mocked(reportApi.preview).mockResolvedValue(dataset);vi.mocked(reportApi.export).mockResolvedValue({blob:new Blob(["%PDF"]),filename:"report.pdf",pages:1,multiPage:false});vi.stubGlobal("URL",{createObjectURL:vi.fn(()=>"blob:test"),revokeObjectURL:vi.fn()});vi.spyOn(HTMLAnchorElement.prototype,"click").mockImplementation(()=>undefined);});
  afterEach(()=>{cleanup();vi.clearAllMocks();vi.unstubAllGlobals();});

  it("provides an RTL accessible filter-preview-export workflow",async()=>{
    render(<ReportWorkspace/>);
    expect(await screen.findByText("مشروع المدرسة")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button",{name:"جدول المعلم"}));
    fireEvent.change(await screen.findByLabelText("اختيار المعلم"),{target:{value:"t1"}});
    fireEvent.click(screen.getByRole("button",{name:"معاينة التقرير"}));
    expect(await screen.findByText("نسخة الجدول 7")).toBeInTheDocument();
    expect(reportApi.preview).toHaveBeenCalledWith("p1",expect.objectContaining({report_type:"teacher_timetable",filters:expect.objectContaining({teacher_id:"t1"})}));
    fireEvent.click(screen.getByRole("button",{name:"تصدير PDF"}));
    await waitFor(()=>expect(reportApi.export).toHaveBeenCalledWith("p1",expect.objectContaining({source:expect.objectContaining({expected_revision:7})}),"pdf"));
  });

  it("shows empty and stale-warning states",async()=>{
    vi.mocked(reportApi.preview).mockResolvedValue({...dataset,report_type:"general_timetable",rows:[],row_count:0,stale:true,warnings:["نسخة قديمة"]});
    render(<ReportWorkspace/>);
    expect(screen.getByText(/اختر التقرير والفلاتر/)).toBeInTheDocument();
    await screen.findByText("مشروع المدرسة");
    fireEvent.click(screen.getByRole("button",{name:"معاينة التقرير"}));
    expect(await screen.findByText("نسخة قديمة")).toBeInTheDocument();
    expect(screen.getByText("لا توجد بيانات مطابقة.")).toBeInTheDocument();
    expect(screen.getByRole("button",{name:"تصدير PDF"})).toBeDisabled();
  });

  it("validates branding files in-app before server verification",async()=>{
    render(<ReportWorkspace/>);await screen.findByText("مشروع المدرسة");
    const file=new File([new Uint8Array(1_000_001)],"unsafe.svg",{type:"image/svg+xml"});
    fireEvent.change(screen.getByLabelText("رفع الشعار"),{target:{files:[file]}});
    expect(await screen.findByRole("alert")).toHaveTextContent("PNG أو JPEG");
  });
});
