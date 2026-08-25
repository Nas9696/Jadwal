import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { blocksForDay, nextBlockOrder, SetupWorkspace } from "./setup-workspace";
import { setupApi } from "@/lib/setup-api";

const snapshot = {
  school: { id: "school-1", name_ar: "مدرسة الاختبار", code: "T" },
  years: [{ id: "year-1", name: "1448", starts_on: "2026-08-01", ends_on: "2027-06-01", is_current: true }],
  terms: [{ id: "term-1", academic_year_id: "year-1", name_ar: "الفصل الأول", order: 1, starts_on: "2026-08-01", ends_on: "2026-12-01" }], shifts: [{ id: "shift-1", name_ar: "صباحي", code: "AM", order: 0, is_active: true }],
  patterns: [{ id: "pattern-1", name_ar: "الأسبوع A", code: "A", cycle_week_index: 0 }],
  days: [
    { id: "day-sun", shift_id: "shift-1", week_pattern_id: "pattern-1", weekday_index: 0, enabled: true, label_ar: "الأحد" },
    { id: "day-mon", shift_id: "shift-1", week_pattern_id: "pattern-1", weekday_index: 1, enabled: true, label_ar: "الاثنين" },
  ],
  blocks: [
    { id: "sun-1", school_day_id: "day-sun", block_order: 0, block_type: "lesson", label_ar: "رياضيات الأحد", starts_at: "08:00:00", ends_at: "08:45:00", period_number: 1, attendance_mode: "onsite" },
    { id: "mon-1", school_day_id: "day-mon", block_order: 0, block_type: "lesson", label_ar: "علوم الاثنين", starts_at: "08:00:00", ends_at: "08:45:00", period_number: 1, attendance_mode: "onsite" },
  ],
  stages: [{ id: "stage-1", name_ar: "ابتدائي", code: "P", order: 0 }], grades: [{ id: "grade-1", stage_id: "stage-1", name_ar: "الأول", order: 0 }], sections: [{ id: "section-1", grade_id: "grade-1", name_ar: "أ", capacity: 25 }],
};

vi.mock("@/lib/setup-api", () => ({ setupApi: { snapshot: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() } }));

describe("selected school-day timeline", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.mocked(setupApi.snapshot).mockResolvedValue(snapshot);
    Object.defineProperty(window, "localStorage", { configurable: true, value: { getItem: () => "school-1", setItem: vi.fn() } });
  });

  it("filters blocks and computes order inside one day", () => {
    expect(blocksForDay(snapshot.blocks, "day-sun").map((x) => x.id)).toEqual(["sun-1"]);
    expect(nextBlockOrder([...snapshot.blocks, { ...snapshot.blocks[0], id: "sun-2", block_order: 4 }], "day-sun")).toBe(5);
    expect(nextBlockOrder(snapshot.blocks, "missing-day")).toBe(0);
  });

  it("switches the visible timeline without mixing days", async () => {
    render(<SetupWorkspace initialTab="day" />);
    expect(await screen.findByText("رياضيات الأحد")).toBeInTheDocument();
    expect(screen.queryByText("علوم الاثنين")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "اليوم المعروض في المخطط" }), { target: { value: "day-mon" } });
    await waitFor(() => expect(screen.getByText("علوم الاثنين")).toBeInTheDocument());
    expect(screen.queryByText("رياضيات الأحد")).not.toBeInTheDocument();
  });

  it("exposes edit actions for every populated PM-002A resource", async () => {
    render(<SetupWorkspace initialTab="calendar" />);
    await screen.findByRole("heading", { name: "عام دراسي جديد" });
    expect(screen.getAllByRole("button", { name: "تعديل" })).toHaveLength(4);
    fireEvent.click(screen.getByRole("button", { name: "اليوم الدراسي" }));
    expect(screen.getAllByRole("button", { name: "تعديل" })).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: "المراحل والصفوف" }));
    expect(screen.getAllByRole("button", { name: "تعديل" })).toHaveLength(3);
  });
});
