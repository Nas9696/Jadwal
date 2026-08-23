import { afterEach, describe, expect, it, vi } from "vitest";
import { masterApi } from "./master-api";

afterEach(() => vi.restoreAllMocks());

describe("master data dependency messages", () => {
  it("explains why a referenced resource cannot be deactivated", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: { code: "resource_has_assignments" } }), {
        status: 409,
      }),
    );
    await expect(
      masterApi.updateCatalog("school-1", "resources", "resource-1", {
        is_active: false,
      }),
    ).rejects.toThrow("مستخدم في إسناد");
  });
});
