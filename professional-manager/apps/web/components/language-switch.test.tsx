import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LanguageSwitch } from "./language-switch";

describe("LanguageSwitch", () => {
  it("starts Arabic-first and switches document direction", () => {
    render(<LanguageSwitch />);
    expect(document.documentElement.dir).toBe("rtl");
    fireEvent.click(screen.getByRole("button"));
    expect(document.documentElement.dir).toBe("ltr");
    expect(document.documentElement.lang).toBe("en");
  });
});

