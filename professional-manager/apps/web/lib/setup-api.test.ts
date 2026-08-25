import { afterEach, describe, expect, it, vi } from "vitest";
import { setupApi, TENANT_ID } from "./setup-api";

afterEach(() => vi.restoreAllMocks());

describe("school setup API", () => {
  it("scopes reads to the tenant and selected school", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ school: { id: "school-1" }, years: [] }), { status: 200 }));
    await setupApi.snapshot("school-1");
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/schools/school-1/setup"), expect.objectContaining({ headers: expect.objectContaining({ "X-Tenant-ID": TENANT_ID }) }));
  });

  it("sends persisted changes to the API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "year-1" }), { status: 201 }));
    await setupApi.create("school-1", "years", { name: "1448 هـ" });
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/setup/years"), expect.objectContaining({ method: "POST" }));
  });

  it("edits setup records through PUT", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ id: "pattern-1" }), { status: 200 }));
    await setupApi.update("school-1", "patterns", "pattern-1", { name_ar: "الأسبوع الأساسي" });
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/patterns/pattern-1"), expect.objectContaining({ method: "PUT" }));
  });

  it("translates overlap validation into an actionable Arabic error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: { code: "day_block_overlap" } }), { status: 422 }));
    await expect(setupApi.create("school-1", "blocks", {})).rejects.toThrow("يتداخل هذا الوقت");
  });
});
