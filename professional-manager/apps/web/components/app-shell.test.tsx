import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./app-shell";

vi.mock("next/navigation", () => ({ usePathname: () => "/setup", useRouter: () => ({ refresh: vi.fn() }) }));
vi.mock("@/lib/setup-api", () => ({ setupApi: { schools: vi.fn().mockResolvedValue([{ id: "s1", name_ar: "مدرسة الآفاق", code: "A" }]) } }));

describe("Arabic app shell", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    Object.defineProperty(window, "localStorage", { configurable: true, value: { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => values.set(key, value), clear: () => values.clear() } });
    document.documentElement.dir = "rtl";
  });
  it("shows setup navigation and a real school selector", async () => {
    render(<AppShell><div>المحتوى</div></AppShell>);
    expect(screen.getByRole("navigation", { name: "التنقل الرئيسي" })).toHaveTextContent("إعداد المدرسة");
    expect(screen.getByRole("navigation", { name: "التنقل الرئيسي" })).toHaveTextContent("التقارير والطباعة");
    expect(document.documentElement.dir).toBe("rtl");
    await waitFor(() => expect(screen.getByRole("combobox", { name: "اختيار المدرسة" })).toHaveValue("s1"));
    expect(screen.getByRole("link", { name: "إعداد المدرسة" })).toHaveClass("active");
  });
});
